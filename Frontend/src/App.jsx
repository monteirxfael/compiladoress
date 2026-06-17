import React, { useState, useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { io } from 'socket.io-client';
import Editor from '@monaco-editor/react';

import 'xterm/css/xterm.css';

export default function App() {
  const [session, setSession] = useState({
    access_token: "mock-token-temporario-para-testes",
    user: { email: "rafael@estudante.if" }
  });
  
  const [code, setCode] = useState('programa\n  inteiro x;\ninicio\n  leia(x);\n  escreva(x);\nfim');
  const [asmCode, setAsmCode] = useState('; O código Assembly compilado aparecerá aqui...');
  const [isAsmExpanded, setIsAsmExpanded] = useState(true);
  const [isCompiling, setIsCompiling] = useState(false);
  
  const terminalRef = useRef(null);
  const xtermRef = useRef(null);
  const fitAddonRef = useRef(null);
  const socketRef = useRef(null);

  useEffect(() => {
    if (!session) return;

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Fira Code, monospace',
      theme: { background: '#0a0a0a', foreground: '#f8f8f2', cursor: '#50fa7b' }
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    term.writeln('\x1b[1;34m[*] SIMPLES Web IDE Terminal pronto.\x1b[0m');
    term.writeln('[*] Conectando ao cluster de execução...\r\n');

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    socketRef.current = io('http://localhost:5000/pty', {
      auth: { token: session.access_token }
    });

    socketRef.current.on('connect', () => {
      term.writeln('\x1b[1;32m[+] Canal de comunicação síncrona PTY Ativo!\x1b[0m\r\n');
    });

    socketRef.current.on('pty_data', (data) => {
      term.write(data);
    });

    term.onData((data) => {
      if (socketRef.current?.connected) {
        socketRef.current.emit('pty_input', { input: data });
      }
    });

    const handleResize = () => fitAddon.fit();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      term.dispose();
      if (socketRef.current) socketRef.current.disconnect();
    };
  }, [session]);

  const handleCompile = async () => {
    setIsCompiling(true);
    xtermRef.current.writeln('\r\n\x1b[1;33m[*] Enviando código ao compilador...\x1b[0m');
    
    try {
      const response = await fetch('http://localhost:5000/api/compile', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code: code })
      });

      const data = await response.json();

      if (response.ok) {
        setAsmCode(data.asm);
        xtermRef.current.writeln('\x1b[1;32m[+] Compilação Concluída com Sucesso!\x1b[0m');
      } else {
        xtermRef.current.writeln(`\x1b[1;31m[-] Erro:\x1b[0m\r\n${data.error}`);
      }
    } catch (err) {
      xtermRef.current.writeln('\x1b[1;31m[-] Falha na requisição. Backend offline.\x1b[0m');
    } finally {
      setIsCompiling(false);
    }
  };

  const handleRun = () => {
    if (socketRef.current?.connected) {
      xtermRef.current.writeln('\r\n\x1b[1;32m[*] Instanciando sandbox Docker e executando binário...\x1b[0m\r');
      socketRef.current.emit('run_binary');
    } else {
      xtermRef.current.writeln('\x1b[1;31m[-] Erro: Sem conexão WebSocket ativa.\x1b[0m');
    }
  };

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', backgroundColor: '#111827', color: '#f3f4f6', overflow: 'hidden', fontFamily: 'sans-serif' }}>
      
      <header style={{ backgroundColor: '#1f2937', borderBottom: '1px solid #374151', padding: '12px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '20px', fontWeight: '900', letterSpacing: '0.05em', color: '#818cf8' }}>
            SIMPLES<span style={{ color: '#34d399' }}>.IDE</span>
          </span>
          <span style={{ fontSize: '12px', backgroundColor: '#374151', color: '#9ca3af', padding: '2px 8px', borderRadius: '9999px', fontFamily: 'monospace', border: '1px solid #4b5563' }}>
            v1.0
          </span>
        </div>
        
        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={handleCompile} disabled={isCompiling} style={{ backgroundColor: '#4f46e5', color: 'white', fontWeight: '600', padding: '6px 16px', borderRadius: '4px', border: 'none', cursor: 'pointer', fontSize: '14px' }}>
            {isCompiling ? '⚙️ Compilando...' : '⚙️ Compilar'}
          </button>
          <button onClick={handleRun} style={{ backgroundColor: '#059669', color: 'white', fontWeight: '600', padding: '6px 16px', borderRadius: '4px', border: 'none', cursor: 'pointer', fontSize: '14px' }}>
            ▶ Executar
          </button>
          <button onClick={() => xtermRef.current?.clear()} style={{ backgroundColor: '#4b5563', color: '#e5e7eb', fontWeight: '600', padding: '6px 12px', borderRadius: '4px', border: 'none', cursor: 'pointer', fontSize: '14px' }}>
            Limpar Console
          </button>
        </div>
      </header>

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden', borderBottom: '1px solid #1f2937' }}>
          
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: '30%', backgroundColor: '#030712' }}>
            <div style={{ backgroundColor: '#111827', padding: '4px 16px', height: '32px', display: 'flex', alignItems: 'center', fontSize: '12px', fontFamily: 'monospace', color: '#9ca3af', borderBottom: '1px solid #1f2937' }}>
              main.simples
            </div>
            <div style={{ flex: 1, paddingTop: '8px' }}>
              <Editor
                height="100%"
                language="javascript"
                theme="vs-dark"
                value={code}
                onChange={(val) => setCode(val || '')}
                options={{ fontSize: 14, minimap: { enabled: false }, automaticLayout: true }}
              />
            </div>
          </div>

          <div style={{ width: '4px', backgroundColor: '#1f2937' }} />
          
          <div style={{ display: 'flex', flexDirection: 'column', backgroundColor: '#030712', borderLeft: '1px solid #1f2937', width: isAsmExpanded ? '45%' : '45px', transition: 'all 0.3s' }}>
            <div style={{ backgroundColor: '#111827', padding: '4px 16px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', fontFamily: 'monospace', color: '#9ca3af', borderBottom: '1px solid #1f2937', overflow: 'hidden' }}>
              {isAsmExpanded && <span>código_gerado.asm</span>}
              <button onClick={() => setIsAsmExpanded(!isAsmExpanded)} style={{ color: '#9ca3af', background: 'none', border: 'none', cursor: 'pointer', fontWeight: '600', marginLeft: 'auto' }}>
                {isAsmExpanded ? '◂ Ocultar' : '👁️ ASM'}
              </button>
            </div>
            {isAsmExpanded && (
              <pre style={{ flex: 1, padding: '16px', fontFamily: 'monospace', fontSize: '14px', overflow: 'auto', color: '#fcd34d', margin: 0, lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                {asmCode}
              </pre>
            )}
          </div>

        </div>

        <div style={{ height: '240px', backgroundColor: '#0a0a0a', display: 'flex', flexDirection: 'column', borderTop: '1px solid #1f2937' }}>
          <div style={{ backgroundColor: '#111827', padding: '4px 16px', height: '32px', display: 'flex', alignItems: 'center', fontSize: '12px', fontFamily: 'monospace', color: '#9ca3af', borderBottom: '1px solid #1f2937' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }}></span>
              <span>Terminal Interativo (Console WebSocket PTY)</span>
            </span>
          </div>
          <div ref={terminalRef} style={{ flex: 1, padding: '8px', overflow: 'hidden' }} />
        </div>

      </main>
    </div>
  );
}