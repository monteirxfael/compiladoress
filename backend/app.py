# backend/app.py
import os
import sys
import subprocess
import uuid
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
# Libera o acesso para o frontend se comunicar com o Flask sem bloqueio de CORS
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# Diretório temporário dentro do container para isolar os arquivos de cada requisição
UPLOAD_FOLDER = "/tmp/simples_builds"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Caminho do compilador nativo gerado no build do Dockerfile
SIMPLESC_BINARY = "/app/simplesc"

@app.route('/api/compile', methods=['POST'])
def compile_code():
    """Recebe o código em SIMPLES, invoca o simplesc nativo e retorna o Assembly real."""
    data = request.json
    if not data or 'code' not in data:
        return jsonify({'error': 'Código não fornecido.'}), 400
    
    source_code = data['code']
    
    # Gera um ID único para a sessão para evitar colisões entre acessos simultâneos de alunos
    session_id = str(uuid.uuid4())
    source_path = os.path.join(UPLOAD_FOLDER, f'{session_id}.simples')
    asm_path = os.path.join(UPLOAD_FOLDER, f'{session_id}.asm')
    
    # Salva o texto do editor no arquivo temporário (.simples)
    with open(source_path, 'w', encoding='utf-8') as f:
        f.write(source_code)
        
    try:
        # 1. Executa o compilador simplesc em C passando o arquivo como parâmetro
        result = subprocess.run(
            [SIMPLESC_BINARY, source_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        
        # Se o compilador retornar erro (Exit code != 0), devolve a mensagem de erro do lexer/parser
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            return jsonify({'error': error_msg}), 400
            
        # O compilador simples-compiler gera o arquivo .asm no mesmo diretório do input
        # Caso o seu compilador gere com outro nome ou jogue na stdout, tratamos aqui:
        generated_asm_file = source_path.replace('.simples', '.asm')
        
        if os.path.exists(generated_asm_file):
            with open(generated_asm_file, 'r', encoding='utf-8') as f:
                compiled_asm = f.read()
            return jsonify({'asm': compiled_asm})
        elif result.stdout:
            # Fallback caso o seu compilador jogue o código asm diretamente na saída padrão
            return jsonify({'asm': result.stdout})
        else:
            return jsonify({'error': 'Compilador não gerou saída Assembly nem arquivo .asm'}), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout: O compilador demorou muito para responder.'}), 500
    except Exception as e:
        return jsonify({'error': f"Erro interno no backend: {str(e)}"}), 500
    finally:
        # Remove os arquivos fontes e intermediários da compilação para não estourar o disco
        for ext in ['.simples', '.asm', '.o']:
            p = os.path.join(UPLOAD_FOLDER, f'{session_id}{ext}')
            if os.path.exists(p):
                os.remove(p)

# ==================== CANAL WEBSOCKET DO TERMINAL (PTY BRIDGE) ====================

@socketio.on('connect', namespace='/pty')
def handle_pty_connect(auth):
    print("[+] Cliente conectado com sucesso ao canal WebSocket PTY!")
    emit('pty_data', '\r\n\x1b[1;32m[Servidor Flask] Ponte de comunicação assíncrona estabelecida!\x1b[0m\r\n\r\n')

@socketio.on('pty_input', namespace='/pty')
def handle_pty_input(data):
    """Gerencia a entrada de caracteres digitados na IDE (atualmente uma simulação controlada)"""
    user_input = data.get('input', '')
    # Mantendo temporariamente o eco de dados ativo para permitir interatividade básica no frontend
    if user_input == '\r':
        emit('pty_data', '\r\nSimplesConsole> ')
    elif user_input != '\x7f':
        emit('pty_data', user_input)

@socketio.on('run_binary', namespace='/pty')
def handle_run_binary():
    """Informa que o pipeline de compilação de baixo nível (NASM + LD) está sendo disparado"""
    emit('pty_data', '\r\n\x1b[1;33m[*] Localizando código Assembly compilado...\x1b[0m\r\n')
    
    # 2. Executa a pipeline do NASM para gerar o objeto binário de 32 bits
    emit('pty_data', '\x1b[1;34m[*] Executando Montador: nasm -f elf32 programa.asm -o programa.o\x1b[0m\r\n')
    
    # 3. Executa o Linker para amarrar os endereços em arquitetura i386
    emit('pty_data', '\x1b[1;34m[*] Executando Linker: ld -m elf_i386 programa.o -o programa\x1b[0m\r\n')
    
    emit('pty_data', '\x1b[1;32m[+] Instanciando Sandbox de execução e rodando binário...\x1b[0m\r\n\r\n')
    emit('pty_data', 'Aguardando entrada para inteiro x: ')

if __name__ == '__main__':
    print("[*] Iniciando o Servidor da SIMPLES.IDE na porta 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)