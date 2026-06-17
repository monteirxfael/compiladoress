export default function EditorPanel({ code, setCode }) {
  import React from 'react';
import Editor from '@monaco-editor/react';

export default function EditorPanel({ code, setCode }) {
  
  const handleEditorWillMount = (monaco) => {
    // Registra o ID da linguagem SIMPLES no Monaco
    monaco.languages.register({ id: 'simples' });

    // Define os Tokens Léxicos (Palavras-chave da especificação)
    monaco.languages.setMonarchTokensProvider('simples', {
      keywords: [
        'programa', 'inicio', 'fim', 'inteiro', 'real', 'se', 
        'entao', 'senao', 'enquanto', 'faca', 'leia', 'escreva'
      ],
      operators: [
        '=', '+', '-', '*', '/', '==', '!=', '<', '>', '<=', '>='
      ],
      tokenizer: {
        root: [
          [/[a-zA-Z_][a-zA-Z0-9_]*/, {
            cases: {
              '@keywords': 'keyword',
              '@default': 'identifier',
            }
          }],
          [/\/\/.*$/, 'comment'], // Comentários de linha única
          [/\d+/, 'number'],       // Números inteiros
          [/[=+\-*/<>!]+/, {
            cases: {
              '@operators': 'operator',
              '@default': ''
            }
          }],
        ]
      }
    });

    // Define as cores customizadas baseadas no tema Dark do Tailwind
    monaco.editor.defineTheme('simplesTheme', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'keyword', foreground: '818cf8', fontStyle: 'bold' }, // Indigo-400
        { token: 'identifier', foreground: 'ffffff' },
        { token: 'comment', foreground: '4b5563', fontStyle: 'italic' }, // Gray-600
        { token: 'number', foreground: 'f59e0b' },                      // Amber-500
        { token: 'operator', foreground: '34d399' },                    // Emerald-400
      ],
      colors: {
        'editor.background': '#030712', // bg-gray-950 do Tailwind
      }
    });
  };

  return (
    <div className="flex-1 flex flex-col min-w-[30%] bg-gray-950">
      <div className="bg-gray-900 px-4 h-8 flex items-center text-xs font-mono text-gray-400 border-b border-gray-800">
        main.simples
      </div>
      <div className="flex-1 pt-2">
        <Editor
          height="100%"
          language="simples"
          theme="simplesTheme"
          value={code}
          onChange={(val) => setCode(val || '')}
          beforeMount={handleEditorWillMount}
          options={{
            fontSize: 14,
            minimap: { enabled: false },
            automaticLayout: true,
            lineNumbers: 'on',
            cursorBlink: 'smooth',
          }}
        />
      </div>
    </div>
  );
}
  

  }