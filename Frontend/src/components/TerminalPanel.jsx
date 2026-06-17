export default function TerminalPanel({ terminalRef }) {
  import React from 'react';

export default function TerminalPanel({ terminalRef }) {
  return (
    <div className="h-60 bg-[#0a0a0a] flex flex-col border-t border-gray-800">
      <div className="bg-gray-900 px-4 h-8 flex items-center text-xs font-mono text-gray-400 border-b border-gray-800">
        <span className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Terminal Interativo (Console WebSocket PTY)</span>
        </span>
      </div>
      {/* O Xterm.js vai se acoplar estritamente dentro desta div via ref */}
      <div ref={terminalRef} className="flex-1 p-2 overflow-hidden" />
    </div>
  );
}

  }