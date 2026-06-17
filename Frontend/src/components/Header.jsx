import React from 'react';

export default function Header({ onCompile, onRun, onClearTerminal, isCompiling, onLogout }) {
  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-3 flex items-center justify-between shadow-md z-10">
      <div className="flex items-center space-x-3">
        <span className="text-xl font-black tracking-wider text-indigo-400">
          SIMPLES<span className="text-emerald-400">.IDE</span>
        </span>
        <span className="text-xs bg-gray-700 text-gray-400 px-2 py-0.5 rounded-full border border-gray-600 font-mono">
          v1.0
        </span>
      </div>
      
      <div className="flex items-center space-x-3">
        <button 
          onClick={onCompile}
          disabled={isCompiling}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 text-white font-semibold px-4 py-1.5 rounded transition text-sm cursor-pointer shadow-sm"
        >
          {isCompiling ? '⚙️ Compilando...' : '⚙️ Compilar'}
        </button>
        
        <button 
          onClick={onRun}
          className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-4 py-1.5 rounded transition text-sm cursor-pointer shadow-sm"
        >
          ▶ Executar
        </button>
        
        <button 
          onClick={onClearTerminal}
          className="bg-gray-700 hover:bg-gray-600 text-gray-300 font-semibold px-3 py-1.5 rounded transition text-sm cursor-pointer"
        >
          Limpar Console
        </button>

        <button 
          onClick={onLogout}
          className="bg-red-900/40 hover:bg-red-900 text-red-300 font-semibold px-3 py-1.5 rounded transition text-sm cursor-pointer border border-red-800/60"
        >
          Sair
        </button>
      </div>
    </header>
  );
}