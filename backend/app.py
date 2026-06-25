import os
import select
import subprocess
import uuid
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = "/tmp/simples_builds"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SIMPLESC_BINARY = os.environ.get("SIMPLESC_PATH", "backend/compiler/build/simplesc")

# socket_id → {'proc': Popen, 'session_id': str, 'input_buffer': str}
active_processes = {}


def _cleanup_session(session_id):
    """Remove todos os artefatos de build de uma sessão."""
    for suffix in ['.asm', '.o', '']:
        path = os.path.join(UPLOAD_FOLDER, f'{session_id}{suffix}')
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def _stream_output(proc, sid, session_id):
    """
    Lê stdout do subprocesso e emite ao cliente via WebSocket.
    Executa como background task para não bloquear o servidor.
    """
    try:
        while True:
            ready, _, _ = select.select([proc.stdout], [], [], 0.1)
            if ready:
                chunk = os.read(proc.stdout.fileno(), 1024)
                if not chunk:
                    break
                socketio.emit(
                    'stdout',
                    {'data': chunk.decode('utf-8', errors='replace')},
                    room=sid,
                    namespace='/pty',
                )
            elif proc.poll() is not None:
                # Processo terminou — drena saída restante
                while True:
                    r, _, _ = select.select([proc.stdout], [], [], 0)
                    if not r:
                        break
                    chunk = os.read(proc.stdout.fileno(), 1024)
                    if not chunk:
                        break
                    socketio.emit(
                        'stdout',
                        {'data': chunk.decode('utf-8', errors='replace')},
                        room=sid,
                        namespace='/pty',
                    )
                break
    except Exception as e:
        print(f'[!] _stream_output erro ({sid}): {e}')
    finally:
        proc.wait()
        rc = proc.returncode
        socketio.emit('exit', {'code': rc}, room=sid, namespace='/pty')
        _cleanup_session(session_id)
        active_processes.pop(sid, None)


# ==================== COMPILAÇÃO (HTTP) ====================

@app.route('/api/compile', methods=['POST'])
def compile_code():
    """Recebe código SIMPLES, invoca simplesc e retorna o ASM limpo + session_id."""
    data = request.json
    if not data or 'code' not in data:
        return jsonify({'error': 'Código não fornecido.'}), 400

    source_code = data['code']
    session_id = str(uuid.uuid4())
    source_path = os.path.join(UPLOAD_FOLDER, f'{session_id}.simples')
    asm_path = os.path.join(UPLOAD_FOLDER, f'{session_id}.asm')

    with open(source_path, 'w', encoding='utf-8') as f:
        f.write(source_code)

    try:
        result = subprocess.run(
            [SIMPLESC_BINARY, source_path, '-o', asm_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            return jsonify({'error': error_msg}), 400

        if not os.path.exists(asm_path):
            return jsonify({'error': 'Compilador não gerou o arquivo .asm'}), 500

        with open(asm_path, 'r', encoding='utf-8') as f:
            linhas_asm = f.readlines()

        # Remove linhas inválidas antes da primeira diretiva ASM real
        linhas_limpas = []
        encontrou_diretiva_valida = False
        for linha in linhas_asm:
            if not encontrou_diretiva_valida:
                lower = linha.lower().strip()
                if lower.startswith('section') or lower.startswith('global'):
                    encontrou_diretiva_valida = True
            if encontrou_diretiva_valida:
                linhas_limpas.append(linha)

        compiled_asm = ''.join(linhas_limpas) if linhas_limpas else ''.join(linhas_asm)

        with open(asm_path, 'w', encoding='utf-8') as f:
            f.write(compiled_asm)

        # Retorna session_id para o frontend usar em run_binary
        return jsonify({'asm': compiled_asm, 'session_id': session_id})

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout: O compilador demorou muito.'}), 500
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
    finally:
        # Remove apenas o fonte; mantém o .asm para a etapa de execução
        if os.path.exists(source_path):
            os.remove(source_path)


# ==================== CANAL WEBSOCKET DO TERMINAL (PTY BRIDGE) ====================

@socketio.on('connect', namespace='/pty')
def handle_pty_connect(auth):
    print(f'[+] Cliente {request.sid} conectado ao canal WebSocket PTY!')
    emit('pty_data', '\r\n\x1b[1;32m[Servidor Flask] Ponte de comunicação assíncrona estabelecida!\x1b[0m\r\n\r\n')


@socketio.on('disconnect', namespace='/pty')
def handle_pty_disconnect():
    sid = request.sid
    state = active_processes.pop(sid, None)
    if state:
        try:
            state['proc'].kill()
        except Exception:
            pass
        _cleanup_session(state['session_id'])


@socketio.on('pty_input', namespace='/pty')
def handle_pty_input(data):
    sid = request.sid
    user_input = data.get('input', '')
    state = active_processes.get(sid)

    if not state:
        # Nenhum processo rodando — só ecoa
        if user_input == '\r':
            emit('pty_data', '\r\nSimplesConsole> ')
        elif user_input != '\x7f':
            emit('pty_data', user_input)
        return

    proc = state['proc']

    if user_input == '\x7f':  # Backspace
        if state['input_buffer']:
            state['input_buffer'] = state['input_buffer'][:-1]
            emit('pty_data', '\b \b')
    elif user_input == '\r':  # Enter — envia linha completa ao stdin
        line = state['input_buffer'] + '\n'
        state['input_buffer'] = ''
        emit('pty_data', '\r\n')
        try:
            proc.stdin.write(line.encode('utf-8'))
            proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
    elif user_input == '\x03':  # Ctrl+C
        try:
            proc.kill()
        except Exception:
            pass
    else:
        state['input_buffer'] += user_input
        emit('pty_data', user_input)  # Ecoa o caractere ao terminal


@socketio.on('run_binary', namespace='/pty')
def handle_run_binary(data):
    sid = request.sid
    session_id = data.get('session_id', '') if isinstance(data, dict) else ''

    if not session_id:
        emit('pty_data', '\r\n\x1b[1;31m[-] Erro: compile o código antes de executar.\x1b[0m\r\n')
        return

    asm_path = os.path.join(UPLOAD_FOLDER, f'{session_id}.asm')
    obj_path = os.path.join(UPLOAD_FOLDER, f'{session_id}.o')
    bin_path = os.path.join(UPLOAD_FOLDER, session_id)

    if not os.path.exists(asm_path):
        emit('pty_data', '\r\n\x1b[1;31m[-] Arquivo .asm não encontrado. Recompile o código.\x1b[0m\r\n')
        return

    # Mata processo anterior deste socket, se houver
    existing = active_processes.pop(sid, None)
    if existing:
        try:
            existing['proc'].kill()
        except Exception:
            pass

    emit('compile_started', {'message': 'Montando e linkando o binário...'})
    emit('pty_data', '\r\n\x1b[1;33m[*] nasm -f elf32 ...\x1b[0m\r\n')

    nasm = subprocess.run(
        ['nasm', '-f', 'elf32', asm_path, '-o', obj_path],
        capture_output=True, text=True, timeout=15,
    )
    if nasm.returncode != 0:
        err = nasm.stderr or nasm.stdout
        emit('pty_data', f'\r\n\x1b[1;31m[-] Erro NASM:\x1b[0m\r\n{err}\r\n')
        return

    emit('pty_data', '\x1b[1;33m[*] ld -m elf_i386 ...\x1b[0m\r\n')

    ld = subprocess.run(
        ['ld', '-m', 'elf_i386', obj_path, '-o', bin_path],
        capture_output=True, text=True, timeout=15,
    )
    if ld.returncode != 0:
        err = ld.stderr or ld.stdout
        emit('pty_data', f'\r\n\x1b[1;31m[-] Erro ld:\x1b[0m\r\n{err}\r\n')
        return

    os.chmod(bin_path, 0o755)
    emit('pty_data', '\x1b[1;32m[+] Executando binário...\x1b[0m\r\n\r\n')

    try:
        proc = subprocess.Popen(
            [bin_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            cwd=UPLOAD_FOLDER,
        )
    except Exception as e:
        emit('pty_data', f'\r\n\x1b[1;31m[-] Falha ao iniciar o binário: {e}\x1b[0m\r\n')
        return

    active_processes[sid] = {'proc': proc, 'session_id': session_id, 'input_buffer': ''}
    socketio.start_background_task(_stream_output, proc, sid, session_id)


if __name__ == '__main__':
    print('[*] Iniciando o Servidor da SIMPLES.IDE na porta 5000...')
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
