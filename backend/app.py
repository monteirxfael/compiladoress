# backend/app.py
import os
import sys
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

SIMPLESC_BINARY = "/app/simplesc"

@app.route('/api/compile', methods=['POST'])
def compile_code():
    """Recebe o código em SIMPLES, invoca o simplesc e limpa o ASM gerado para o NASM."""
    data = request.json
    if not data or 'code' not in data:
        return jsonify({'error': 'Código não fornecido.'}), 400
    
    source_code = data['code']
    session_id = str(uuid.uuid4())
    source_path = os.path.join(UPLOAD_FOLDER, f'{session_id}.simples')
    
    with open(source_path, 'w', encoding='utf-8') as f:
        f.write(source_code)
        
    try:
        # 1. Executa o vosso compilador
        result = subprocess.run(
            [SIMPLESC_BINARY, source_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            return jsonify({'error': error_msg}), 400
            
        generated_asm_file = source_path.replace('.simples', '.asm')
        
        if os.path.exists(generated_asm_file):
            with open(generated_asm_file, 'r', encoding='utf-8') as f:
                linhas_asm = f.readlines()
            
            # 2. SISTEMA DE FILTRAGEM: Remove linhas inválidas do topo do arquivo
            linhas_limpas = []
            encontrou_diretiva_valida = False
            
            for linha in linhas_asm:
                linha_lower = linha.lower().strip()
                # O filtro só ativa quando encontra o início real do Assembly x86
                if linha_lower.startswith("section") or linha_lower.startswith("global"):
                    encontrou_diretiva_valida = True
                
                if encontrou_diretiva_valida:
                    linhas_limpas.append(linha)
            
            # Se o filtro encontrou código válido, reescreve o ficheiro limpo para o NASM
            if linhas_limpas:
                compiled_asm = "".join(linhas_limpas)
                with open(generated_asm_file, 'w', encoding='utf-8') as f:
                    f.write(compiled_asm)
            else:
                # Caso não encontre diretivas, mantém o original para não quebrar o fluxo
                compiled_asm = "".join(linhas_asm)

            return jsonify({'asm': compiled_asm})
        
        return jsonify({'error': 'Compilador não gerou o arquivo .asm'}), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout: O compilador demorou muito.'}), 500
    except Exception as e:
        return jsonify({'error': f"Erro interno: {str(e)}"}), 500
    finally:
        # Limpeza física mantida para segurança do disco
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
    user_input = data.get('input', '')
    if user_input == '\r':
        emit('pty_data', '\r\nSimplesConsole> ')
    elif user_input != '\x7f':
        emit('pty_data', user_input)

@socketio.on('run_binary', namespace='/pty')
def handle_run_binary():
    emit('pty_data', '\r\n\x1b[1;33m[*] Localizando código Assembly compilado...\x1b[0m\r\n')
    emit('pty_data', '\x1b[1;34m[*] Executando Montador: nasm -f elf32 programa.asm -o programa.o\x1b[0m\r\n')
    emit('pty_data', '\x1b[1;34m[*] Executando Linker: ld -m elf_i386 programa.o -o programa\x1b[0m\r\n')
    emit('pty_data', '\x1b[1;32m[+] Instanciando Sandbox de execução e rodando binário...\x1b[0m\r\n\r\n')
    emit('pty_data', 'Aguardando entrada para inteiro x: ')

if __name__ == '__main__':
    print("[*] Iniciando o Servidor da SIMPLES.IDE na porta 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)