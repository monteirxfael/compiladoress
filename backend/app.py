# backend/app.py
import os
import sys
import subprocess
import shlex
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
# Libera o acesso para o frontend (Vite) se comunicar com o Flask sem bloqueio de CORS
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# Cria uma pasta temporária para armazenar os códigos enviados
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'temp_build')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/api/compile', methods=['POST'])
def compile_code():
    """Recebe o código em SIMPLES, gera o arquivo .asm e devolve para a tela."""
    data = request.json
    if not data or 'code' not in data:
        return jsonify({'error': 'Código não fornecido.'}), 400
    
    source_code = data['code']
    source_path = os.path.join(UPLOAD_FOLDER, 'programa.simples')
    asm_path = os.path.join(UPLOAD_FOLDER, 'programa.asm')
    
    # Salva o texto do editor no arquivo local
    with open(source_path, 'w', encoding='utf-8') as f:
        f.write(source_code)
        
    try:
        # Comportamento temporário (Mock): gera um esqueleto estruturado em NASM
        # Quando seu compilador em C ('simplesc') estiver pronto, usaremos subprocess para chamá-lo
        mock_asm = (
            "; ---------------------------------------------------------\n"
            ";   Código Assembly NASM gerado pelo Compilador SIMPLES\n"
            "; ---------------------------------------------------------\n"
            "global _start\n\n"
            "section .text\n"
            "_start:\n"
            "    ; Seu compilador adicionará as instruções geradas aqui\n"
            "    mov eax, 1       ; Syscall exit\n"
            "    mov ebx, 0       ; Código de retorno 0\n"
            "    int 0x80\n"
        )
        with open(asm_path, 'w', encoding='utf-8') as f:
            f.write(mock_asm)
            
        with open(asm_path, 'r', encoding='utf-8') as f:
            compiled_asm = f.read()
            
        return jsonify({'asm': compiled_asm})
        
    except Exception as e:
        return jsonify({'error': f"Erro interno no backend: {str(e)}"}), 500

# ==================== CANAL WEBSOCKET DO TERMINAL (PTY BRIDGE) ====================

@socketio.on('connect', namespace='/pty')
def handle_pty_connect(auth):
    print("[+] Cliente conectado com sucesso ao canal WebSocket PTY!")
    emit('pty_data', '\r\n\x1b[1;32m[Servidor Flask] Ponte de comunicação assíncrona estabelecida!\x1b[0m\r\n\r\n')

@socketio.on('pty_input', namespace='/pty')
def handle_pty_input(data):
    """Recebe cada caractere que o aluno digita no xterm e devolve na tela (Echo)"""
    user_input = data.get('input', '')
    # Tratamento básico de Enter para pular linha no console local por enquanto
    if user_input == '\r':
        emit('pty_data', '\r\n')
    else:
        emit('pty_data', user_input)

@socketio.on('run_binary', namespace='/pty')
def handle_run_binary():
    """Simula a execução do binário final dentro do container isolado"""
    emit('pty_data', '\r\n\x1b[1;33m[*] Instanciando container efêmero Docker (Sandbox)...\x1b[0m\r\n')
    emit('pty_data', '\x1b[1;32m[+] Execução terminada com sucesso.\x1b[0m\r\n\r\nSimplesConsole> ')

if __name__ == '__main__':
    print("[*] Iniciando o Servidor da SIMPLES.IDE na porta 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)