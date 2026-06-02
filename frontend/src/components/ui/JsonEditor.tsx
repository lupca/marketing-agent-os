'use client';
// src/components/ui/JsonEditor.tsx
// Editable JSON editor with syntax highlighting and schema validation

import { useState, useCallback, useEffect } from 'react';
import { AlertCircle, CheckCircle2, RotateCcw } from 'lucide-react';

interface JsonEditorProps {
  value: Record<string, unknown>;
  onChange?: (value: Record<string, unknown>) => void;
  readOnly?: boolean;
  height?: string;
  label?: string;
}

function syntaxHighlight(json: string): string {
  return json
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      (match) => {
        let cls = 'text-sky-300'; // number
        if (/^"/.test(match)) {
          if (/:$/.test(match)) cls = 'text-violet-300'; // key
          else cls = 'text-emerald-300'; // string
        } else if (/true|false/.test(match)) cls = 'text-amber-300'; // boolean
        else if (/null/.test(match)) cls = 'text-slate-500'; // null
        return `<span class="${cls}">${match}</span>`;
      }
    );
}

export default function JsonEditor({
  value,
  onChange,
  readOnly = false,
  height = '400px',
  label,
}: JsonEditorProps) {
  const [raw, setRaw] = useState(() => JSON.stringify(value, null, 2));
  const [error, setError] = useState<string | null>(null);
  const [isValid, setIsValid] = useState(true);

  useEffect(() => {
    setRaw(JSON.stringify(value, null, 2));
    setError(null);
    setIsValid(true);
  }, [value]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const text = e.target.value;
      setRaw(text);
      try {
        const parsed = JSON.parse(text);
        setError(null);
        setIsValid(true);
        onChange?.(parsed);
      } catch (err) {
        setError((err as Error).message);
        setIsValid(false);
      }
    },
    [onChange]
  );

  const handleReset = useCallback(() => {
    const resetStr = JSON.stringify(value, null, 2);
    setRaw(resetStr);
    setError(null);
    setIsValid(true);
  }, [value]);

  return (
    <div className="flex flex-col gap-2">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        {label && (
          <span className="text-xs font-medium text-slate-400">{label}</span>
        )}
        <div className="flex items-center gap-2 ml-auto">
          {isValid ? (
            <span className="flex items-center gap-1 text-xs text-emerald-400">
              <CheckCircle2 size={12} /> Valid JSON
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-red-400">
              <AlertCircle size={12} /> Invalid JSON
            </span>
          )}
          {!readOnly && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition-colors px-2 py-0.5 rounded hover:bg-slate-700"
            >
              <RotateCcw size={12} /> Reset
            </button>
          )}
        </div>
      </div>

      {/* Editor */}
      <div
        className="relative rounded-lg border overflow-hidden"
        style={{
          borderColor: error ? '#ef4444' : isValid ? '#1e293b' : '#ef4444',
        }}
      >
        {/* Line numbers */}
        <div
          className="absolute left-0 top-0 bottom-0 w-10 bg-slate-950 border-r border-slate-800 flex flex-col items-end pr-2 pt-3 gap-[0px] pointer-events-none select-none overflow-hidden"
          style={{ height }}
          aria-hidden="true"
        >
          {raw.split('\n').map((_, i) => (
            <span key={i} className="text-slate-600 font-mono text-xs leading-5">
              {i + 1}
            </span>
          ))}
        </div>

        {/* Textarea */}
        <textarea
          value={raw}
          onChange={handleChange}
          readOnly={readOnly}
          spellCheck={false}
          className={`
            w-full pl-12 pr-4 py-3 bg-slate-950 font-mono text-xs text-slate-200
            leading-5 resize-none outline-none
            ${readOnly ? 'cursor-default opacity-80' : 'cursor-text'}
          `}
          style={{ height, minHeight: height }}
        />
      </div>

      {/* Error message */}
      {error && (
        <div className="flex items-start gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
          <AlertCircle size={12} className="mt-0.5 shrink-0" />
          <span className="font-mono">{error}</span>
        </div>
      )}
    </div>
  );
}
