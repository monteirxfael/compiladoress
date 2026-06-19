# SIMPLES.IDE — Web IDE para a linguagem SIMPLES

Uma IDE web completa para escrever, compilar e executar programas na linguagem **SIMPLES**, desenvolvida como projeto da disciplina de Compiladores.

## Acesso

Deploy em produção: [https://simples-ide.onrender.com](https://simples-ide.onrender.com)

---

## Funcionalidades

- Editor de código com syntax highlighting customizado para a linguagem SIMPLES (Monaco Editor)
- Compilação real via `simplesc` (compilador C99 desenvolvido pelo professor)
- Visualização do Assembly NASM gerado
- Terminal interativo via WebSocket (xterm.js) com execução real do binário
- Pipeline completo: `.simples` → `.asm` → `.o` → binário ELF32

---

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | React + Vite |
| Editor | Monaco Editor (`@monaco-editor/react`) |
| Terminal | xterm.js + Flask-SocketIO |
| Backend | Python 3 + Flask + Flask-SocketIO |
| Compilador | simplesc (C99) — [pm-avila/simples-compiler](https://github.com/pm-avila/simples-compiler) |
| Montagem | NASM + ld (ELF32) |
| Container | Docker + Docker Compose |

---

## Como rodar localmente

### Pré-requisitos

- Python 3.10+
- Node.js 20+
- GCC, Make, NASM, binutils (`apt install gcc make nasm binutils`)

### Backend

```bash
cd backend

# Compile o simplesc (apenas na primeira vez)
cd compiler && make all && cd ..

# Instale as dependências Python
pip install -r requirements.txt

# Suba o servidor
python3 app.py
```

O backend estará disponível em `http://localhost:5000`.

### Frontend

```bash
cd Frontend
npm install
npm run dev
```

O frontend estará disponível em `http://localhost:5173`.

---

## Como rodar com Docker Compose

```bash
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:5000`

---

## Integrantes

- **Rafael** — [@monteirxfael](https://github.com/monteirxfael)
- **Nattan** — [@nattan](https://github.com/nattan)
- **Felipe** — [@felipehcheleno-maker](https://github.com/felipehcheleno-maker)
