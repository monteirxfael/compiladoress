# backend/app.py
import os
import subprocess
import threading
import shutil
import docker as docker_sdk
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# No Linux/WSL usa /tmp para garantir que binários gerados tenham permissão
# de execução — arquivos em /mnt/c/ (NTFS) não herdam o bit +x no WSL.
_local_build = os.path.join(os.path.dirname(__file__), 'temp_build')
UPLOAD_FOLDER = '/tmp/simples_build' if os.name == 'posix' else _local_build
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Mapeia sid -> Popen para permitir envio de stdin ao processo em execução
running_processes = {}

# Estado legado do terminal (mantido para compatibilidade)
STATUS_SISTEMA = {"executando_programa": False, "valor_x": ""}

# =============================================================================
# PADRÃO FAÇADE — CompilerService esconde a orquestração
# simplesc → arquivo .asm atrás de uma interface simples.
# O cliente (rota /api/compile) chama apenas compile(),
# sem conhecer os detalhes de cada etapa.
# =============================================================================
class CompilerService:
    def __init__(self, compiler_dir: str, build_dir: str):
        self.simplesc_path = os.path.join(compiler_dir, 'build', 'simplesc')
        self.build_dir = build_dir
        self._compiler_dir = compiler_dir

    def _ensure_binary(self):
        """Compila o simplesc com make all se o binário ainda não existir."""
        if not os.path.isfile(self.simplesc_path):
            result = subprocess.run(
                ['make', 'all'],
                cwd=self._compiler_dir,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"Erro ao compilar simplesc:\n{result.stderr}")

    def compile(self, code: str) -> dict:
        """Recebe código-fonte SIMPLES e retorna {'asm': ...} ou {'error': ...}."""
        source_path = os.path.join(self.build_dir, 'programa.simples')
        asm_path = os.path.join(self.build_dir, 'programa.asm')

        # Etapa 1: salvar o código-fonte no disco
        with open(source_path, 'w', encoding='utf-8') as f:
            f.write(code)

        # Etapa 2: garantir que o simplesc está compilado
        self._ensure_binary()

        # Etapa 3: invocar o simplesc para gerar o .asm
        result = subprocess.run(
            [self.simplesc_path, source_path, asm_path],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return {'error': result.stderr or result.stdout}

        # Etapa 4: ler e retornar o assembly gerado
        with open(asm_path, 'r', encoding='utf-8') as f:
            return {'asm': f.read()}


# =============================================================================
# PADRÃO STRATEGY — ExecutionStrategy define o contrato de
# "como executar um binário". SubprocessStrategy é a implementação
# atual. No futuro, PtyStrategy substituiria sem mudar o código
# que usa a estratégia.
# =============================================================================
class ExecutionStrategy:
    def execute(self, binary_path: str, sid: str):
        raise NotImplementedError


class SubprocessStrategy(ExecutionStrategy):
    def execute(self, binary_path: str, sid: str):
        """Monta o binário com NASM + ld e executa em sandbox Docker (qemu) com fallback para Popen."""
        build_dir = os.path.dirname(binary_path)
        asm_path = os.path.join(build_dir, 'programa.asm')
        obj_path = os.path.join(build_dir, 'programa.o')

        if not os.path.isfile(asm_path):
            socketio.emit('pty_data', '\r\n\x1b[1;31m[-] Nenhum .asm encontrado. Compile primeiro.\x1b[0m\r\n', room=sid, namespace='/pty')
            return

        # Resolve caminhos absolutos dos binários para evitar PermissionError no WSL
        nasm_bin = shutil.which('nasm') or '/usr/bin/nasm'
        ld_bin = shutil.which('ld') or '/usr/bin/ld'

        if not os.path.isfile(nasm_bin):
            socketio.emit('pty_data', f'\r\n\x1b[1;31m[-] nasm não encontrado em {nasm_bin}. Instale com: apt install nasm\x1b[0m\r\n', room=sid, namespace='/pty')
            socketio.emit('exit', {'code': 1}, room=sid, namespace='/pty')
            return

        # PADRÃO OBSERVER: evento 'compile_started' notifica a UI que a montagem começou.
        socketio.emit('compile_started', {'message': 'Montando com NASM...'}, room=sid, namespace='/pty')
        socketio.emit('pty_data', '\r\n\x1b[1;33m[*] Montando com NASM...\x1b[0m\r\n', room=sid, namespace='/pty')

        nasm = subprocess.run(
            [nasm_bin, '-f', 'elf32', asm_path, '-o', obj_path],
            capture_output=True, text=True
        )
        if nasm.returncode != 0:
            err = nasm.stderr.replace('\n', '\r\n')
            socketio.emit('pty_data', f'\x1b[1;31m[-] Erro NASM:\x1b[0m\r\n{err}\r\n', room=sid, namespace='/pty')
            socketio.emit('exit', {'code': nasm.returncode}, room=sid, namespace='/pty')
            return

        socketio.emit('pty_data', '\x1b[1;33m[*] Linkando com ld...\x1b[0m\r\n', room=sid, namespace='/pty')

        ld = subprocess.run(
            [ld_bin, '-m', 'elf_i386', obj_path, '-o', binary_path],
            capture_output=True, text=True
        )
        if ld.returncode != 0:
            err = ld.stderr.replace('\n', '\r\n')
            socketio.emit('pty_data', f'\x1b[1;31m[-] Erro ld:\x1b[0m\r\n{err}\r\n', room=sid, namespace='/pty')
            socketio.emit('exit', {'code': ld.returncode}, room=sid, namespace='/pty')
            return

        os.chmod(binary_path, 0o755)

        socketio.emit('stdout', {'data': '\r\n$ Executando...\r\n'}, room=sid, namespace='/pty')
        socketio.emit('compile_started', {'message': 'Iniciando execução...'}, room=sid, namespace='/pty')
        socketio.emit('pty_data', '\x1b[1;32m[+] Executando binário: ./programa\x1b[0m\r\n\r\n', room=sid, namespace='/pty')

        try:
            # PADRÃO STRATEGY: tenta executar no container runner sandbox (qemu isolado).
            # Se o Docker não estiver disponível, cai no fallback Popen direto.
            client = docker_sdk.from_env()
            binary_name = os.path.basename(binary_path)

            container = client.containers.run(
                image='simples-runner',
                command=['/usr/bin/qemu-i386-static', f'/sandbox/{binary_name}'],
                volumes={build_dir: {'bind': '/sandbox', 'mode': 'ro'}},
                network_mode='none',
                cap_drop=['ALL'],
                read_only=True,
                tmpfs={'/tmp': ''},
                stdin_open=True,
                tty=False,
                detach=True,
                remove=False,
            )
            running_processes[sid] = container

            def read_output():
                try:
                    for chunk in container.logs(stream=True, follow=True):
                        text = chunk.decode('utf-8', errors='replace').replace('\n', '\r\n')
                        # PADRÃO OBSERVER: 'stdout' notifica a UI com o output do processo.
                        socketio.emit('stdout', {'data': text}, room=sid, namespace='/pty')
                finally:
                    result = container.wait()
                    container.remove(force=True)
                    running_processes.pop(sid, None)
                    # PADRÃO OBSERVER: 'exit' sinaliza término com código de saída.
                    socketio.emit('exit', {'code': result.get('StatusCode', 0)}, room=sid, namespace='/pty')

            threading.Thread(target=read_output, daemon=True).start()

        except Exception:
            # Fallback: Popen direto se Docker não disponível
            socketio.emit('pty_data', '\x1b[1;33m[~] Docker indisponível — executando via subprocess.\x1b[0m\r\n', room=sid, namespace='/pty')
            try:
                # Popen com pipes abertos: stdin permanece disponível para leia()
                process = subprocess.Popen(
                    [binary_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=0,  # sem buffer — crítico para leia funcionar em tempo real
                )
                running_processes[sid] = process

                def read_output_fallback():
                    try:
                        for chunk in iter(lambda: process.stdout.read(1), b''):
                            text = chunk.decode('utf-8', errors='replace').replace('\n', '\r\n')
                            socketio.emit('stdout', {'data': text}, room=sid, namespace='/pty')
                    finally:
                        process.wait()
                        running_processes.pop(sid, None)
                        socketio.emit('exit', {'code': process.returncode}, room=sid, namespace='/pty')

                threading.Thread(target=read_output_fallback, daemon=True).start()

            except Exception as e:
                socketio.emit('pty_data', f'\r\n\x1b[1;31mErro ao executar: {e}\x1b[0m\r\n', room=sid, namespace='/pty')
                socketio.emit('exit', {'code': 1}, room=sid, namespace='/pty')


# =============================================================================
# PADRÃO FACTORY — cria a estratégia de execução adequada.
# Centraliza a decisão em um único ponto: para adicionar
# PtyStrategy ou DockerStrategy, basta estender este factory.
# =============================================================================
def execution_strategy_factory(mode: str = "subprocess") -> ExecutionStrategy:
    if mode == "subprocess":
        return SubprocessStrategy()
    raise ValueError(f"Estratégia desconhecida: {mode}")


# Instâncias dos serviços
_compiler_service = CompilerService(
    compiler_dir=os.path.join(os.path.dirname(__file__), 'compiler'),
    build_dir=UPLOAD_FOLDER
)

# =============================================================================
# ROTAS REST
# =============================================================================

@app.route('/api/compile', methods=['POST'])
def compile_code():
    """Recebe o código em SIMPLES, gera o arquivo .asm e devolve para a tela."""
    data = request.json
    if not data or 'code' not in data:
        return jsonify({'error': 'Código não fornecido.'}), 400

    try:
        result = _compiler_service.compile(data['code'])
        if 'error' in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f"Erro interno no backend: {str(e)}"}), 500


# =============================================================================
# CANAL WEBSOCKET DO TERMINAL (PTY BRIDGE)
# =============================================================================

@socketio.on('connect', namespace='/pty')
def handle_pty_connect(auth):
    print("[+] Cliente conectado com sucesso ao canal WebSocket PTY!")
    emit('pty_data', '\r\n\x1b[1;32m[Servidor Flask] Ponte de comunicação assíncrona estabelecida!\x1b[0m\r\n\r\n')

@socketio.on('pty_input', namespace='/pty')
def handle_pty_input(data):
    """Encaminha input do xterm.js para o processo em execução (leia interativo)
    ou trata como entrada do console padrão se nenhum processo estiver rodando."""
    sid = request.sid
    user_input = data.get('input', '')

    process = running_processes.get(sid)
    if process and process.poll() is None:
        # Processo real em execução: envia o caractere diretamente ao stdin do binário.
        # '\r' vira '\n' porque o processo espera newline Unix para leia().
        try:
            char = '\n' if user_input == '\r' else user_input
            process.stdin.write(char.encode('utf-8'))
            process.stdin.flush()
            # Ecoa o caractere no terminal para feedback visual
            echo = '\r\n' if user_input == '\r' else user_input
            emit('pty_data', echo)
        except Exception:
            pass
    else:
        # Nenhum processo rodando: comportamento padrão do console
        if user_input == '\r':
            emit('pty_data', '\r\nSimplesConsole> ')
        elif user_input == '\x7f':
            pass
        else:
            emit('pty_data', user_input)


@socketio.on('stop_execution', namespace='/pty')
def handle_stop_execution(data=None):
    """Encerra o processo em execução para o cliente atual."""
    sid = request.sid
    process = running_processes.pop(sid, None)
    if process:
        process.terminate()
        emit('pty_data', '\r\n\x1b[1;31m[!] Execução interrompida pelo usuário.\x1b[0m\r\nSimplesConsole> ')

@socketio.on('run_binary', namespace='/pty')
def handle_run_binary():
    """Delega a execução para a estratégia escolhida pelo factory."""
    sid = request.sid
    binary_path = os.path.join(UPLOAD_FOLDER, 'programa')

    # Factory decide qual estratégia usar; Strategy executa sem o handler saber os detalhes.
    strategy = execution_strategy_factory(mode="subprocess")
    strategy.execute(binary_path=binary_path, sid=sid)


if __name__ == '__main__':
    print("[*] Iniciando o Servidor da SIMPLES.IDE na porta 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
