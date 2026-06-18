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

# Variável global temporária para gerenciar o estado da simulação do terminal
STATUS_SISTEMA = {"executando_programa": False, "valor_x": ""}

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
    """Recebe e gerencia cada caractere que você digita no terminal xterm"""
    user_input = data.get('input', '')
    global STATUS_SISTEMA

    # Se o botão Executar foi clicado e o programa está simulando o 'leia(x)'
    if STATUS_SISTEMA["executando_programa"]:
        if user_input == '\r' or user_input == '\n': # Se o usuário apertou ENTER
            emit('pty_data', '\r\n')
            
            # Pega o valor digitado ou define um padrão caso tenha apertado Enter direto
            valor_final = STATUS_SISTEMA["valor_x"] if STATUS_SISTEMA["valor_x"] else "10"
            
            # Simula a execução das instruções seguintes do compilador
            emit('pty_data', f'\x1b[1;36m[Sandbox] Armazenando valor {valor_final} no endereço de memória de X.\x1b[0m\r\n')
            emit('pty_data', f'SimplesOut> {valor_final}\r\n') # Simulação do escreva(x)
            
            # Encerra o ciclo da Sandbox Docker
            emit('pty_data', '\r\n\x1b[1;32m[+] Processo finalizado com código de saída 0.\x1b[0m\r\nSimplesConsole> ')
            
            # Reseta o estado do terminal para o modo padrão
            STATUS_SISTEMA["executando_programa"] = False
            STATUS_SISTEMA["valor_x"] = ""
        
        elif user_input == '\x7f': # Trata o Backspace (Apagar) no terminal
            if len(STATUS_SISTEMA["valor_x"]) > 0:
                STATUS_SISTEMA["valor_x"] = STATUS_SISTEMA["valor_x"][:-1]
                emit('pty_data', '\b \b') # Apaga o caractere visualmente no xterm
        
        else:
            # Filtra para aceitar apenas números (já que a variável 'x' é inteiro)
            if user_input.isdigit():
                STATUS_SISTEMA["valor_x"] += user_input
                emit('pty_data', user_input) # Ecoa o número digitado na tela do usuário
            
    else:
        # Comportamento padrão do terminal (Fora da execução do binário)
        if user_input == '\r':
            emit('pty_data', '\r\nSimplesConsole> ')
        elif user_input == '\x7f':
            pass
        else:
            emit('pty_data', user_input)

@socketio.on('run_binary', namespace='/pty')
def handle_run_binary():
    """Simula o disparo do binário correspondente ao código 'main.simples'"""
    global STATUS_SISTEMA
    STATUS_SISTEMA["executando_programa"] = True
    STATUS_SISTEMA["valor_x"] = "" # Limpa qualquer resíduo anterior
    
    emit('pty_data', '\r\n\x1b[1;33m[*] Instanciando container efêmero Docker (Sandbox Container)...\x1b[0m\r\n')
    emit('pty_data', '\x1b[1;34m[*] Carregando imagem base do cluster local...\x1b[0m\r\n')
    emit('pty_data', '\x1b[1;32m[+] Executando binário: ./programa_compilado\x1b[0m\r\n\r\n')
    
    # Simula a execução do comando 'leia(x)' pausando o terminal para input do aluno
    emit('pty_data', 'Aguardando entrada para inteiro x: ')

if __name__ == '__main__':
    print("[*] Iniciando o Servidor da SIMPLES.IDE na porta 5000...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)