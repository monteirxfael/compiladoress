# PROGRESS.md — Registro de Progresso

## Status Geral: ✅ Entregável

---

## Funcionalidades Implementadas

### ✅ Editor com Syntax Highlighting
- Monaco Editor integrado com linguagem customizada `simples`
- 27 palavras-reservadas destacadas (keywords, comentários, strings, números, operadores)
- Tema `simples-dark` com paleta de cores dedicada

### ✅ Pipeline de Compilação
- Código SIMPLES → `simplesc` (C99) → `.asm` NASM
- Assembly gerado exibido em tempo real no painel direito
- Erros do compilador exibidos no terminal

### ✅ Terminal Interativo (xterm.js + WebSocket)
- xterm.js conectado via Flask-SocketIO no namespace `/pty`
- Execução real do binário via NASM + ld + subprocess
- `leia` interativo: stdin aberto via `Popen` + thread daemon
- Eventos nomeados: `compile_started`, `stdout`, `exit`, `pty_data`

### ✅ Sandbox de Execução (Docker + QEMU)
- Container `simples-runner` com `qemu-user-static` para execução isolada
- `network_mode: none`, `cap_drop: ALL`, `read_only: true`
- Fallback automático para subprocess direto se Docker indisponível

---

## Design Patterns Implementados

| Pattern | Implementação | Arquivo |
|---|---|---|
| **Façade** | `CompilerService.compile()` encapsula pipeline simplesc→asm | `backend/app.py:32` |
| **Strategy** | `ExecutionStrategy` + `SubprocessStrategy` | `backend/app.py:82` |
| **Observer** | Eventos WebSocket nomeados consumidos pelo frontend | `backend/app.py:107` |
| **Factory** | `execution_strategy_factory(mode)` | `backend/app.py:179` |

---

## Infraestrutura

| Componente | Status |
|---|---|
| `Dockerfile` (backend) | ✅ Ubuntu 22.04 + nasm + binutils + simplesc |
| `docker-compose.yml` | ✅ backend + frontend + nginx + runner |
| `nginx/nginx.conf` | ✅ reverse proxy porta 80 → backend:5000 |
| `render.yaml` | ✅ runtime: docker para deploy no Render |
| `runner/Dockerfile` | ✅ qemu-user-static sandbox |

---

## Git

| Item | Status |
|---|---|
| Branches de feature | ✅ `feat/syntax-highlighting-e-compilador`, `feat/felipe-execucao-pty-readme` |
| Pull Request mergeado | ✅ PR #1 mergeado via GitHub |
| Conventional Commits | ✅ `feat:`, `fix:`, `docs:`, `chore:`, `refactor:` |
| Autores | ✅ Rafael Monteiro, Nattan, felipehcheleno-maker |

---

## Equipe

- **Rafael Monteiro** — UI + estrutura Flask inicial
- **Nattan** — integração compilador + WebSocket + Docker
- **Felipe** — execução PTY + README + design patterns

---

## Deploy

- Local: `docker compose up --build`
- Produção: [https://simples-ide.onrender.com](https://simples-ide.onrender.com)
