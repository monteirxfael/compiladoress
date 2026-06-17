export default function AsmPanel({ asmCode, isAsmExpanded, setIsAsmExpanded }) {
  import React from 'react';

export default function AsmPanel({ asmCode, isAsmExpanded, setIsAsmExpanded }) {
  return (
    <div 
      className="flex flex-col bg-gray-950 transition-all duration-300 border-l border-gray-800"
      style={{ width: isAsmExpanded ? '45%' : '45px' }}
    >
      <div className="bg-gray-900 px-4 h-8 flex items-center justify-between text-xs font-mono text-gray-400 border-b border-gray-800 whitespace-nowrap overflow-hidden">
        {isAsmExpanded && <span>código_gerado.asm</span>}
        <button 
          onClick={() => setIsAsmExpanded(!isAsmExpanded)}
          className="text-gray-400 hover:text-white transition cursor-pointer ml-auto font-semibold"
        >
          {isAsmExpanded ? '◂ Ocultar' : '👁️ ASM'}
        </button>
      </div>
      {isAsmExpanded && (
        <pre className="flex-1 p-4 font-mono text-sm overflow-auto text-orange-300 leading-relaxed bg-gray-900/20 select-text">
          {asmCode}
        </pre>
      )}
    </div>
  );
}
  

  }