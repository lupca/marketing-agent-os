'use client';
// src/components/ui/JsonDiffViewer.tsx
// Side-by-side JSON diff viewer for node I/O inspection

import { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';

interface JsonDiffViewerProps {
  left: Record<string, unknown>;
  right: Record<string, unknown>;
  leftLabel?: string;
  rightLabel?: string;
}

type DiffStatus = 'added' | 'removed' | 'changed' | 'unchanged';

interface DiffEntry {
  key: string;
  leftValue: unknown;
  rightValue: unknown;
  status: DiffStatus;
}

function computeDiff(
  left: Record<string, unknown>,
  right: Record<string, unknown>
): DiffEntry[] {
  const allKeys = new Set([...Object.keys(left), ...Object.keys(right)]);
  return Array.from(allKeys).map((key) => {
    const lv = left[key];
    const rv = right[key];
    let status: DiffStatus = 'unchanged';
    if (!(key in left)) status = 'added';
    else if (!(key in right)) status = 'removed';
    else if (JSON.stringify(lv) !== JSON.stringify(rv)) status = 'changed';
    return { key, leftValue: lv, rightValue: rv, status };
  });
}

function formatValue(val: unknown): string {
  if (val === undefined) return '—';
  if (typeof val === 'string') return val.length > 200 ? val.slice(0, 200) + '…' : val;
  return JSON.stringify(val, null, 2);
}

function ValueCell({
  value,
  highlight,
}: {
  value: unknown;
  highlight: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const isComplex = typeof value === 'object' && value !== null;
  const formatted = formatValue(value);
  const isLong = formatted.length > 120;

  return (
    <div
      className={`rounded px-2 py-1 font-mono text-xs break-all transition-colors ${
        highlight
          ? 'bg-amber-500/10 border border-amber-500/30 text-amber-200'
          : 'text-slate-300'
      }`}
    >
      {isComplex ? (
        <button
          className="flex items-center gap-1 text-blue-400 hover:text-blue-300 transition-colors mb-1"
          onClick={() => setExpanded((e) => !e)}
        >
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          {Array.isArray(value)
            ? `Array[${(value as unknown[]).length}]`
            : `Object{${Object.keys(value as object).length}}`}
        </button>
      ) : null}
      {(expanded || !isComplex) && (
        <pre className={`whitespace-pre-wrap ${isLong && !expanded ? 'line-clamp-3' : ''}`}>
          {formatted}
        </pre>
      )}
      {!expanded && isLong && !isComplex && (
        <button
          className="text-blue-400 text-xs hover:underline mt-1"
          onClick={() => setExpanded(true)}
        >
          Show more…
        </button>
      )}
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="p-1 rounded hover:bg-slate-700 transition-colors"
      title="Copy JSON"
    >
      {copied ? (
        <Check size={14} className="text-emerald-400" />
      ) : (
        <Copy size={14} className="text-slate-400" />
      )}
    </button>
  );
}

const STATUS_STYLES: Record<DiffStatus, string> = {
  added: 'bg-emerald-500/5 border-l-2 border-l-emerald-500',
  removed: 'bg-red-500/5 border-l-2 border-l-red-500',
  changed: 'bg-amber-500/5 border-l-2 border-l-amber-500',
  unchanged: '',
};

const STATUS_BADGE: Record<DiffStatus, { label: string; cls: string }> = {
  added: { label: 'NEW', cls: 'bg-emerald-500/20 text-emerald-400' },
  removed: { label: 'DEL', cls: 'bg-red-500/20 text-red-400' },
  changed: { label: 'MOD', cls: 'bg-amber-500/20 text-amber-400' },
  unchanged: { label: '', cls: '' },
};

export default function JsonDiffViewer({
  left,
  right,
  leftLabel = 'Input State',
  rightLabel = 'Output State',
}: JsonDiffViewerProps) {
  const diffs = useMemo(() => computeDiff(left, right), [left, right]);
  const changedCount = diffs.filter((d) => d.status !== 'unchanged').length;

  return (
    <div className="flex flex-col gap-2 w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> Added
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" /> Removed
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" /> Modified
          </span>
        </div>
        {changedCount > 0 && (
          <span className="text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full">
            {changedCount} change{changedCount !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-[180px_1fr_1fr] gap-2 text-xs text-slate-500 font-medium px-2">
        <span>Field</span>
        <span className="flex items-center gap-2">
          {leftLabel}
          <CopyButton text={JSON.stringify(left, null, 2)} />
        </span>
        <span className="flex items-center gap-2">
          {rightLabel}
          <CopyButton text={JSON.stringify(right, null, 2)} />
        </span>
      </div>

      {/* Diff rows */}
      <div className="flex flex-col gap-1 max-h-96 overflow-y-auto">
        {diffs.map(({ key, leftValue, rightValue, status }) => (
          <div
            key={key}
            className={`grid grid-cols-[180px_1fr_1fr] gap-2 items-start px-2 py-1.5 rounded transition-colors ${STATUS_STYLES[status]}`}
          >
            {/* Key */}
            <div className="flex items-center gap-2 pt-1">
              <span className="font-mono text-xs text-slate-300 truncate">{key}</span>
              {STATUS_BADGE[status].label && (
                <span
                  className={`text-[10px] px-1 py-0.5 rounded font-bold ${STATUS_BADGE[status].cls}`}
                >
                  {STATUS_BADGE[status].label}
                </span>
              )}
            </div>
            {/* Left value */}
            <ValueCell
              value={leftValue}
              highlight={status === 'changed' || status === 'removed'}
            />
            {/* Right value */}
            <ValueCell
              value={rightValue}
              highlight={status === 'changed' || status === 'added'}
            />
          </div>
        ))}
        {diffs.length === 0 && (
          <div className="text-center text-slate-500 text-sm py-8">
            No fields to compare
          </div>
        )}
      </div>
    </div>
  );
}
