'use client';
// src/components/cockpit/DagRadar.tsx
// Glass-box DAG Monitor: Real-time pipeline visualization with node I/O diff

import { useState, useEffect, useCallback, useRef } from 'react';
import { X, RefreshCw, Wifi, WifiOff, Clock, AlertCircle, ChevronRight } from 'lucide-react';
import { cockpitApi } from '@/lib/api';
import { useCockpitWebSocket } from '@/hooks/useCockpitWebSocket';
import JsonDiffViewer from '@/components/ui/JsonDiffViewer';
import type {
  PipelineRun, PipelineNodeExecution, DagVisualization,
  DagNode, NodeStatus, NodeName, CockpitWebSocketEvent
} from '@/lib/types';

// ─── DAG Layout Constants ─────────────────────────────────────────────────────

const NODE_CONFIG: Record<NodeName, { label: string; emoji: string; desc: string }> = {
  scoring:            { label: 'Scoring',      emoji: '🎯', desc: 'MAB belief scoring' },
  selector:           { label: 'Selector',     emoji: '⚡', desc: '80/20 angle mix' },
  creative_generation:{ label: 'Creative Gen', emoji: '✍️', desc: 'LLM copywriting' },
  guardian_sandbox:   { label: 'Guardian',     emoji: '🛡️', desc: 'Brand safety check' },
  insight_generator:  { label: 'Insight Gen',  emoji: '💡', desc: 'CMO insights' },
  publisher:          { label: 'Publisher',    emoji: '📡', desc: 'Facebook Ads API' },
};

const NODE_ORDER: NodeName[] = [
  'scoring', 'selector', 'creative_generation',
  'guardian_sandbox', 'insight_generator', 'publisher'
];

// ─── Status Styling ────────────────────────────────────────────────────────────

const statusStyle = (status: NodeStatus, isSelected: boolean) => {
  const base = 'transition-all duration-300 cursor-pointer';
  const selected = isSelected ? 'ring-2 ring-blue-400 ring-offset-1 ring-offset-slate-900' : '';
  switch (status) {
    case 'running':
      return `${base} ${selected} bg-blue-500/20 border-2 border-blue-500 shadow-[0_0_20px_rgba(59,130,246,0.5)] animate-dag-pulse`;
    case 'completed':
      return `${base} ${selected} bg-emerald-500/15 border border-emerald-500/60 shadow-[0_0_10px_rgba(16,185,129,0.2)]`;
    case 'failed':
      return `${base} ${selected} bg-red-500/15 border-2 border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.4)] animate-dag-shake`;
    case 'skipped':
      return `${base} ${selected} bg-slate-800/50 border border-slate-700 opacity-40`;
    case 'pending':
    default:
      return `${base} ${selected} bg-slate-800/50 border border-slate-700 hover:border-slate-600`;
  }
};

const statusDot = (status: NodeStatus) => {
  switch (status) {
    case 'running':    return 'bg-blue-400 animate-ping';
    case 'completed':  return 'bg-emerald-400';
    case 'failed':     return 'bg-red-400';
    case 'pending':    return 'bg-slate-600';
    case 'skipped':    return 'bg-slate-700';
    default:           return 'bg-slate-600';
  }
};

// ─── DAG Node Component ────────────────────────────────────────────────────────

function DagNodeCard({
  node,
  isSelected,
  onClick,
}: {
  node: DagNode;
  isSelected: boolean;
  onClick: () => void;
}) {
  const cfg = NODE_CONFIG[node.name];

  return (
    <div
      onClick={onClick}
      className={`relative rounded-xl p-3 w-32 text-center select-none ${statusStyle(node.status, isSelected)}`}
    >
      {/* Status dot */}
      <div className="absolute top-2 right-2">
        <span className={`block w-2 h-2 rounded-full ${statusDot(node.status)}`} />
      </div>

      {/* Retry badge */}
      {node.retry_count > 0 && (
        <div className="absolute -top-2 -left-2 bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
          ×{node.retry_count}
        </div>
      )}

      <div className="text-2xl mb-1">{cfg.emoji}</div>
      <p className="text-xs font-semibold text-slate-200">{cfg.label}</p>
      <p className="text-[10px] text-slate-500 mt-0.5">{cfg.desc}</p>

      {node.duration_ms > 0 && (
        <div className="mt-2 flex items-center justify-center gap-1 text-[10px] text-slate-400">
          <Clock size={8} />
          {node.duration_ms < 1000
            ? `${node.duration_ms}ms`
            : `${(node.duration_ms / 1000).toFixed(1)}s`}
        </div>
      )}
    </div>
  );
}

// ─── Connector Arrow ───────────────────────────────────────────────────────────

function Arrow({ type }: { type: 'normal' | 'retry' }) {
  if (type === 'retry') {
    return (
      <div className="flex flex-col items-center justify-center w-8">
        <div className="text-amber-400 text-[10px] font-bold">↺</div>
      </div>
    );
  }
  return (
    <div className="flex items-center justify-center w-8">
      <ChevronRight size={16} className="text-slate-600" />
    </div>
  );
}

// ─── Node Detail Panel ─────────────────────────────────────────────────────────

function NodeDetailPanel({
  node,
  execution,
  onClose,
}: {
  node: DagNode;
  execution: PipelineNodeExecution | null;
  onClose: () => void;
}) {
  const cfg = NODE_CONFIG[node.name];
  const inputState = (execution?.input_state ?? {}) as Record<string, unknown>;
  const outputState = (execution?.output_state ?? {}) as Record<string, unknown>;

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-3xl z-40 flex flex-col bg-slate-950 border-l border-slate-800 shadow-2xl overflow-hidden animate-slide-in-right">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{cfg.emoji}</span>
          <div>
            <h3 className="font-bold text-slate-100">{cfg.label}</h3>
            <p className="text-xs text-slate-500">{cfg.desc}</p>
          </div>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            node.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' :
            node.status === 'running'   ? 'bg-blue-500/20 text-blue-400' :
            node.status === 'failed'    ? 'bg-red-500/20 text-red-400' :
            'bg-slate-700 text-slate-400'
          }`}>
            {node.status.toUpperCase()}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-2 rounded-lg hover:bg-slate-800 transition-colors"
        >
          <X size={18} className="text-slate-400" />
        </button>
      </div>

      {/* Meta info */}
      <div className="grid grid-cols-3 gap-3 px-6 py-3 border-b border-slate-800/50 bg-slate-900/40">
        <div>
          <p className="text-xs text-slate-500">Duration</p>
          <p className="text-sm font-mono text-slate-200">
            {node.duration_ms > 0 ? `${node.duration_ms}ms` : '—'}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Retries</p>
          <p className="text-sm font-mono text-slate-200">{node.retry_count}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Execution ID</p>
          <p className="text-sm font-mono text-slate-400 truncate">
            {node.execution_id ? node.execution_id.slice(0, 12) + '…' : '—'}
          </p>
        </div>
      </div>

      {/* Error message if any */}
      {node.error_message && (
        <div className="mx-6 mt-4 flex items-start gap-2 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-red-300 font-mono">{node.error_message}</p>
        </div>
      )}

      {/* JSON Diff */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <h4 className="text-xs font-semibold text-slate-400 mb-3 uppercase tracking-wider">
          State Diff — Input vs Output
        </h4>
        {execution ? (
          <JsonDiffViewer
            left={inputState}
            right={outputState}
            leftLabel="Input State"
            rightLabel="Output State"
          />
        ) : (
          <div className="text-center py-12 text-slate-500 text-sm">
            No execution data available for this node yet.
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Run Selector ─────────────────────────────────────────────────────────────

function RunSelector({
  runs,
  selectedId,
  onSelect,
}: {
  runs: PipelineRun[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <select
      value={selectedId ?? ''}
      onChange={(e) => onSelect(e.target.value)}
      className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500 min-w-[280px]"
    >
      <option value="">— Select a Pipeline Run —</option>
      {runs.map((r) => (
        <option key={r.id} value={r.id}>
          {r.id.slice(0, 8)}… · {r.execution_mode} · {r.status} ·{' '}
          {new Date(r.started_at).toLocaleString()}
        </option>
      ))}
    </select>
  );
}

// ─── Main DagRadar Component ───────────────────────────────────────────────────

export default function DagRadar() {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [dag, setDag] = useState<DagVisualization | null>(null);
  const [executions, setExecutions] = useState<PipelineNodeExecution[]>([]);
  const [selectedNode, setSelectedNode] = useState<DagNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [dagLoading, setDagLoading] = useState(false);
  const dagRef = useRef<DagVisualization | null>(null);

  // WebSocket for live updates
  const { connectionState } = useCockpitWebSocket(
    useCallback(
      (event: CockpitWebSocketEvent) => {
        if (
          ['node_start', 'node_complete', 'node_fail', 'run_complete', 'run_fail'].includes(event.type)
        ) {
          const runId = event.data.run_id as string;
          if (runId === selectedRunId) {
            // Refresh DAG for current run
            refreshDag(runId);
          }
          // If it's a new run, add to list
          if (event.type === 'run_start') {
            setRuns((prev) => {
              const exists = prev.some((r) => r.id === runId);
              if (!exists) {
                const newRun = {
                  id: runId,
                  execution_mode: event.data.execution_mode as 'shadow' | 'live',
                  status: 'running',
                  started_at: event.timestamp,
                  campaign_id: event.data.campaign_id as string ?? null,
                } as PipelineRun;
                return [newRun, ...prev.slice(0, 49)];
              }
              return prev;
            });
          }
        }
      },
      [selectedRunId]
    )
  );

  const refreshDag = async (runId: string) => {
    try {
      const dagData = await cockpitApi.getDag(runId);
      setDag(dagData);
      dagRef.current = dagData;
      const runData = await cockpitApi.getRun(runId);
      setExecutions(runData.nodes ?? []);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    const fetchRuns = async () => {
      try {
        const res = await cockpitApi.getRuns({ page_size: 50 });
        setRuns(res.runs ?? []);
        // Auto-select latest run
        if (res.runs?.length > 0 && !selectedRunId) {
          const latest = res.runs[0];
          setSelectedRunId(latest.id);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchRuns();
  }, []);

  useEffect(() => {
    if (!selectedRunId) return;
    setDagLoading(true);
    setSelectedNode(null);
    refreshDag(selectedRunId).finally(() => setDagLoading(false));
  }, [selectedRunId]);

  const getExecution = (node: DagNode) =>
    executions.find((e) => e.node_name === node.name) ?? null;

  const isConnected = connectionState === 'connected';

  // Build node list from dag or default pending nodes
  const nodes: DagNode[] = dag?.nodes?.length
    ? (dag.nodes as any[]).map((node) => {
        const name = node.node_name as NodeName;
        const execution = executions.find((e) => e.node_name === name) ?? null;
        return {
          name,
          label: NODE_CONFIG[name]?.label ?? name,
          order: node.node_order,
          status: node.status as NodeStatus,
          duration_ms: node.duration_ms,
          retry_count: execution?.retry_count ?? 0,
          has_error: !!node.error_message,
          error_message: node.error_message,
          execution_id: execution?.id ?? null,
        };
      }).sort((a, b) => a.order - b.order)
    : NODE_ORDER.map((name, i) => ({
        name,
        label: NODE_CONFIG[name].label,
        order: i + 1,
        status: 'pending' as NodeStatus,
        duration_ms: 0,
        retry_count: 0,
        has_error: false,
        error_message: null,
        execution_id: null,
      }));

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-slate-300">Pipeline Run:</span>
          <RunSelector
            runs={runs}
            selectedId={selectedRunId}
            onSelect={setSelectedRunId}
          />
          {dagLoading && (
            <RefreshCw size={14} className="text-slate-400 animate-spin" />
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* WS Status */}
          <div className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border ${
            isConnected
              ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
              : 'text-slate-500 bg-slate-800/50 border-slate-700'
          }`}>
            {isConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
            {isConnected ? 'Live' : 'Offline'}
          </div>

          {/* Run status */}
          {dag && (
            <span className={`text-xs px-2 py-1 rounded-lg font-medium ${
              dag.status === 'completed'   ? 'bg-emerald-500/20 text-emerald-400' :
              dag.status === 'running'     ? 'bg-blue-500/20 text-blue-400' :
              dag.status === 'failed'      ? 'bg-red-500/20 text-red-400' :
              dag.status === 'quarantined' ? 'bg-amber-500/20 text-amber-400' :
              'bg-slate-700 text-slate-400'
            }`}>
              {dag.status?.toUpperCase()}
            </span>
          )}
        </div>
      </div>

      {/* DAG Visualization */}
      <div className="relative rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm p-6 overflow-x-auto">
        {/* Background grid */}
        <div
          className="absolute inset-0 rounded-2xl opacity-[0.03] pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(circle, #94a3b8 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />

        {loading || dagLoading ? (
          <div className="flex items-center justify-center h-32 text-slate-500">
            <RefreshCw size={20} className="animate-spin mr-2" />
            Loading pipeline…
          </div>
        ) : (
          <div className="relative flex items-center gap-0 min-w-max mx-auto w-fit">
            {nodes.map((node, idx) => (
              <div key={`${node.name}-${idx}`} className="flex items-center">
                <DagNodeCard
                  node={node}
                  isSelected={selectedNode?.name === node.name}
                  onClick={() =>
                    setSelectedNode((prev) =>
                      prev?.name === node.name ? null : node
                    )
                  }
                />
                {idx < nodes.length - 1 && (
                  <div className="flex flex-col items-center">
                    {/* Show conditional retry arrow between creative_generation and guardian_sandbox */}
                    {node.name === 'guardian_sandbox' ? (
                      <div className="flex items-center w-10">
                        <ChevronRight size={16} className="text-slate-600" />
                      </div>
                    ) : (
                      <Arrow type="normal" />
                    )}
                  </div>
                )}
              </div>
            ))}

            {/* Retry loop arc for guardian_sandbox → creative_generation */}
            {(nodes.find((n) => n.name === 'guardian_sandbox')?.retry_count ?? 0) > 0 && (
              <div
                className="absolute text-amber-400 text-xs font-bold"
                style={{ top: '-24px', left: '50%', transform: 'translateX(-50%)' }}
              >
                ↺ Retry ({nodes.find((n) => n.name === 'guardian_sandbox')?.retry_count ?? 0})
              </div>
            )}
          </div>
        )}

        {/* Click hint */}
        {!selectedNode && !loading && !dagLoading && (
          <p className="text-center text-xs text-slate-600 mt-4">
            Click on a node to inspect its JSON input/output diff
          </p>
        )}
      </div>

      {/* Mode badge */}
      {dag && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>Mode:</span>
          <span className={`px-2 py-0.5 rounded font-medium ${
            dag.execution_mode === 'live'
              ? 'bg-emerald-500/15 text-emerald-400'
              : 'bg-violet-500/15 text-violet-400'
          }`}>
            {dag.execution_mode?.toUpperCase()}
          </span>
        </div>
      )}

      {/* Node detail side panel */}
      {selectedNode && (
        <>
          <div
            className="fixed inset-0 z-30 bg-black/30 backdrop-blur-[2px]"
            onClick={() => setSelectedNode(null)}
          />
          <NodeDetailPanel
            node={selectedNode}
            execution={getExecution(selectedNode)}
            onClose={() => setSelectedNode(null)}
          />
        </>
      )}
    </div>
  );
}
