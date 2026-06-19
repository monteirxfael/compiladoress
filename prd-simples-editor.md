# Simples Editor — PRD Técnico

## 1. Visão Geral

Web IDE para a linguagem SIMPLES. Permite escrever, compilar e executar programas SIMPLES no navegador, sem instalação local. Três painéis: editor com syntax highlighting, visualizador NASM, terminal interativo.

## 2. Arquitetura

### Componentes

- **Browser**: Monaco Editor (editor) + xterm.js (terminal) via React/Vite
- **Backend**: Flask + Flask-SocketIO (WebSocket bridge)
- **Compilador**: simplesc (C99) — git submodule em `backend/compiler/`
- **Pipeline**: código SIMPLES → simplesc → `.asm` → nasm → ld → binário → execução via PTY

### Fluxo

```
Browser (Monaco) → POST /api/compile → simplesc → NASM gerado → painel direito
Browser (xterm.js) ↕ WebSocket /pty ↕ Flask-SocketIO ↕ subprocess → binário
```

## 3. Stack Técnica

| Camada | Tecnologia | Versão |
|---|---|---|
| Frontend | React + Vite | React 18 |
| Editor | Monaco Editor (`@monaco-editor/react`) | latest |
| Terminal | xterm.js | latest |
| Backend | Python + Flask + Flask-SocketIO + Flask-CORS | Python 3.10+ |
| Compilador | simplesc (C99) + NASM + binutils | — |
| Containerização | Docker + Docker Compose | — |

## 4. Padrões de Projeto Aplicados

- **Strategy** — `ExecutionStrategy` abstrai "como executar" o binário compilado (via `subprocess` direto ou via PTY interativo), permitindo trocar a estratégia sem alterar o código do WebSocket handler.

- **Façade** — `CompilerService.compile()` encapsula o pipeline completo: recebe o código-fonte SIMPLES, chama `simplesc`, monta com `nasm` e linka com `ld`, expondo uma interface simples para o resto do backend.

- **Observer** — eventos WebSocket nomeados (`compile_started`, `asm_generated`, `stdout`, `exit`) emitidos pelo backend e consumidos pela UI (xterm.js / painel ASM), desacoplando produtor e consumidor do output.

- **Factory** — centralização da criação de estratégias de execução: um `ExecutionFactory` decide qual `ExecutionStrategy` instanciar com base no ambiente (PTY disponível, container Docker, fallback subprocess).

## 5. API

### REST

| Método | Rota | Body | Resposta |
|---|---|---|---|
| POST | `/api/compile` | `{"code": "..."}` | `{"asm": "..."}` ou `{"error": "..."}` |

### WebSocket (`/pty` namespace)

| Evento | Direção | Descrição |
|---|---|---|
| `run_binary` | Cliente → Servidor | Inicia execução do binário compilado |
| `pty_input` | Cliente → Servidor | Envia input do usuário para o processo em execução |
| `pty_data` | Servidor → Cliente | Recebe output do processo para o terminal xterm.js |

## 6. Estrutura do Repositório

```
simples-editor/
├── README.md
├── prd-simples-editor.md
├── docker-compose.yml
├── Dockerfile
├── Frontend/          # React + Vite
│   └── src/App.jsx    # Monaco + xterm.js
├── backend/
│   ├── app.py         # Flask + SocketIO
│   ├── compiler/      # git submodule: pm-avila/simples-compiler
│   └── temp_build/    # arquivos temporários de compilação
```

## 7. Deploy

- **Local**: `docker compose up --build`
- **Produção**: Render.com — [https://simples-ide.onrender.com](https://simples-ide.onrender.com)

## 8. Equipe

- **Rafael Monteiro** — UI + estrutura Flask inicial
- **Nattan** — integração compilador + WebSocket
- **Felipe** — execução PTY + README
