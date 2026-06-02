'use client';
// src/components/cockpit/QuarantineZone.tsx
// Quarantine Zone: isolate failed tasks, edit JSON state, force-resume pipeline

import { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert, Play, Trash2, X, AlertTriangle,
  Clock, RefreshCw, ChevronDown, ChevronUp, Check, Edit3
} from 'lucide-react';
import { cockpitApi } from '@/lib/api';
import JsonEditor from '@/components/ui/JsonEditor';
import JsonDiffViewer from '@/components/ui/JsonDiffViewer';
import type { QuarantinedTask, AgencyState, ResolutionStatus } from '@/lib/types';

// ─── Status config ──────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<ResolutionStatus, { label: string; cls: string }> = {
  pending:  { label: 'QUARANTINED', cls: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  resumed:  { label: 'RESUMED',     cls: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
  discarded:{ label: 'DISCARDED',   cls: 'bg-slate-700 text-slate-500 border-slate-600' },
};

const NODE_EMOJI: Record<string, string> = {
  scoring:             '🎯',
  selector:            '⚡',
  creative_generation: '✍️',
  guardian_sandbox:    '🛡️',
  insight_generator:   '💡',
  publisher:           '📡',
};

// ─── Task Editor Modal ───────────────────────────────────────────────────────

function TaskEditorModal({
  task,
  onClose,
  onResume,
  onDiscard,
}: {
  task: QuarantinedTask;
  onClose: () => void;
  onResume: (taskId: string) => Promise<void>;
  onDiscard: (taskId: string) => Promise<void>;
}) {
  const [editedState, setEditedState] = useState<AgencyState>(
    task.edited_state ?? task.frozen_state
  );
  const [saving, setSaving] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [discarding, setDiscarding] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<'editor' | 'diff'>('editor');
  const [confirmDiscard, setConfirmDiscard] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await cockpitApi.updateQuarantineState(task.id, editedState);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error('Failed to save state:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleResume = async () => {
    // Save first, then resume
    await handleSave();
    setResuming(true);
    try {
      await onResume(task.id);
      onClose();
    } finally {
      setResuming(false);
    }
  };

  const handleDiscard = async () => {
    setDiscarding(true);
    try {
      await onDiscard(task.id);
      onClose();
    } finally {
      setDiscarding(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-500/20 rounded-xl flex items-center justify-center">
              <ShieldAlert size={18} className="text-amber-400" />
            </div>
            <div>
              <h3 className="font-bold text-slate-100">
                State Editor — {NODE_EMOJI[task.node_name] ?? '⚙️'} {task.node_name}
              </h3>
              <p className="text-xs text-slate-500 font-mono">{task.id.slice(0, 12)}…</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800 transition-colors">
            <X size={18} className="text-slate-400" />
          </button>
        </div>

        {/* Quarantine reason */}
        <div className="mx-6 mt-4 flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-lg px-4 py-3">
          <AlertTriangle size={14} className="text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-semibold text-amber-300 mb-0.5">Quarantine Reason</p>
            <p className="text-xs text-amber-200/80">{task.quarantine_reason}</p>
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 px-6 mt-4">
          {(['editor', 'diff'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-xs rounded-lg font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {tab === 'editor' ? '✏️ State Editor' : '🔍 Diff View'}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {activeTab === 'editor' ? (
            <JsonEditor
              value={editedState as Record<string, unknown>}
              onChange={(v) => setEditedState(v as AgencyState)}
              height="380px"
              label="AgencyState — Edit and Save before resuming"
            />
          ) : (
            <JsonDiffViewer
              left={task.original_state as Record<string, unknown>}
              right={editedState as Record<string, unknown>}
              leftLabel="Original (Frozen)"
              rightLabel="Edited State"
            />
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-900/60">
          <div className="flex items-center gap-2">
            {/* Save button */}
            <button
              onClick={handleSave}
              disabled={saving || saved || task.resolution_status !== 'pending'}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-200 text-sm transition-colors"
            >
              {saving ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : saved ? (
                <Check size={14} className="text-emerald-400" />
              ) : (
                <Edit3 size={14} />
              )}
              {saved ? 'Saved!' : 'Save State'}
            </button>
          </div>

          <div className="flex items-center gap-2">
            {/* Discard */}
            {task.resolution_status === 'pending' && (
              <>
                {!confirmDiscard ? (
                  <button
                    onClick={() => setConfirmDiscard(true)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 text-sm transition-colors"
                  >
                    <Trash2 size={14} /> Discard
                  </button>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-red-400">Confirm discard?</span>
                    <button
                      onClick={handleDiscard}
                      disabled={discarding}
                      className="px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 text-xs border border-red-500/30 hover:bg-red-500/30 transition-colors"
                    >
                      {discarding ? '…' : 'Yes, discard'}
                    </button>
                    <button
                      onClick={() => setConfirmDiscard(false)}
                      className="px-3 py-1.5 rounded-lg bg-slate-700 text-slate-400 text-xs transition-colors hover:bg-slate-600"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </>
            )}

            {/* Force Resume */}
            {task.resolution_status === 'pending' && (
              <button
                onClick={handleResume}
                disabled={resuming}
                className="flex items-center gap-2 px-5 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 text-blue-300 text-sm font-semibold transition-all"
              >
                {resuming ? (
                  <RefreshCw size={14} className="animate-spin" />
                ) : (
                  <Play size={14} />
                )}
                Force Resume Node
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Task Card ───────────────────────────────────────────────────────────────

function TaskCard({
  task,
  onEdit,
}: {
  task: QuarantinedTask;
  onEdit: (task: QuarantinedTask) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const statusCfg = STATUS_CONFIG[task.resolution_status];

  return (
    <div className={`rounded-xl border overflow-hidden transition-all ${
      task.resolution_status === 'pending'
        ? 'border-amber-500/30 bg-amber-500/5'
        : 'border-slate-800 bg-slate-900/40'
    }`}>
      {/* Row */}
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="flex items-center gap-3">
          <div className="text-2xl">{NODE_EMOJI[task.node_name] ?? '⚙️'}</div>
          <div>
            <p className="text-sm font-medium text-slate-200 capitalize">
              {task.node_name.replace(/_/g, ' ')}
            </p>
            <p className="text-xs text-slate-500 font-mono">{task.id.slice(0, 10)}…</p>
          </div>
          <span className={`text-xs px-2 py-0.5 rounded-full font-bold border ${statusCfg.cls}`}>
            {statusCfg.label}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 text-xs text-slate-500">
            <Clock size={10} />
            {new Date(task.created_at).toLocaleString()}
          </div>
          {task.resolution_status === 'pending' && (
            <button
              onClick={(e) => { e.stopPropagation(); onEdit(task); }}
              className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 border border-blue-500/20 transition-colors font-medium"
            >
              <Edit3 size={11} /> Edit & Resume
            </button>
          )}
          {expanded ? <ChevronUp size={14} className="text-slate-500" /> : <ChevronDown size={14} className="text-slate-500" />}
        </div>
      </div>

      {/* Expanded reason */}
      {expanded && (
        <div className="border-t border-slate-800/50 px-5 py-3 bg-slate-900/30">
          <p className="text-xs text-slate-500 mb-1 font-medium">Quarantine Reason:</p>
          <p className="text-xs text-slate-300">{task.quarantine_reason}</p>
          {task.resolved_by && (
            <p className="text-xs text-slate-500 mt-2">
              Resolved by: <span className="text-slate-300">{task.resolved_by}</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main QuarantineZone ──────────────────────────────────────────────────────

export default function QuarantineZone() {
  const [tasks, setTasks] = useState<QuarantinedTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingTask, setEditingTask] = useState<QuarantinedTask | null>(null);
  const [filter, setFilter] = useState<'all' | ResolutionStatus>('all');

  const fetchTasks = useCallback(async () => {
    try {
      const data = await cockpitApi.getQuarantinedTasks();
      setTasks(data?.tasks ?? []);
    } catch (err) {
      console.error('Failed to load quarantine tasks:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 15000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const handleResume = async (taskId: string) => {
    await cockpitApi.forceResumeTask(taskId);
    await fetchTasks();
  };

  const handleDiscard = async (taskId: string) => {
    await cockpitApi.discardTask(taskId);
    await fetchTasks();
  };

  const filtered = filter === 'all'
    ? tasks
    : tasks.filter((t) => t.resolution_status === filter);

  const counts = {
    pending:   tasks.filter((t) => t.resolution_status === 'pending').length,
    resumed:   tasks.filter((t) => t.resolution_status === 'resumed').length,
    discarded: tasks.filter((t) => t.resolution_status === 'discarded').length,
  };

  return (
    <div className="space-y-5">
      {/* Header stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Pending', key: 'pending', color: 'amber', count: counts.pending },
          { label: 'Resumed', key: 'resumed', color: 'emerald', count: counts.resumed },
          { label: 'Discarded', key: 'discarded', color: 'slate', count: counts.discarded },
        ].map(({ label, key, color, count }) => (
          <button
            key={key}
            onClick={() => setFilter(filter === key ? 'all' : key as ResolutionStatus)}
            className={`rounded-xl p-4 text-left border transition-all ${
              filter === key
                ? `border-${color}-500/50 bg-${color}-500/10`
                : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
            }`}
          >
            <p className={`text-3xl font-bold ${
              color === 'amber'   ? 'text-amber-400' :
              color === 'emerald' ? 'text-emerald-400' : 'text-slate-400'
            }`}>
              {count}
            </p>
            <p className="text-xs text-slate-500 mt-1">{label}</p>
          </button>
        ))}
      </div>

      {/* Info box */}
      <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl px-5 py-4">
        <div className="flex items-start gap-3">
          <ShieldAlert size={16} className="text-blue-400 shrink-0 mt-0.5" />
          <div className="text-xs text-slate-300 space-y-1">
            <p className="font-semibold text-blue-300">Tính năng State Rehydration</p>
            <p>Khi pipeline bị kẹt, task không bị hủy hoàn toàn mà được đưa vào đây.</p>
            <p>Kỹ sư có thể sửa trực tiếp JSON state và bấm <strong className="text-blue-300">[Force Resume Node]</strong> để pipeline tiếp tục chính xác từ điểm bị ngắt — không cần chạy lại từ đầu.</p>
          </div>
        </div>
      </div>

      {/* Filter tabs + refresh */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {(['all', 'pending', 'resumed', 'discarded'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 text-xs rounded-lg transition-colors font-medium ${
                filter === f
                  ? 'bg-slate-700 text-slate-200'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {f === 'all' ? `All (${tasks.length})` : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <button
          onClick={fetchTasks}
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {/* Task list */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-16 rounded-xl bg-slate-800/50 animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-slate-500">
          <ShieldAlert size={36} className="mx-auto mb-3 opacity-20" />
          <p className="text-sm">
            {filter === 'pending'
              ? 'Không có task nào đang chờ xử lý. Hệ thống đang chạy suôn sẻ!'
              : 'Không có task nào.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((task) => (
            <TaskCard key={task.id} task={task} onEdit={setEditingTask} />
          ))}
        </div>
      )}

      {/* Editor Modal */}
      {editingTask && (
        <TaskEditorModal
          task={editingTask}
          onClose={() => { setEditingTask(null); fetchTasks(); }}
          onResume={handleResume}
          onDiscard={handleDiscard}
        />
      )}
    </div>
  );
}
