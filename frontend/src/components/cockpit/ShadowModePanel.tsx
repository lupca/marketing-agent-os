'use client';
// src/components/cockpit/ShadowModePanel.tsx
// Shadow Mode: AI runs but doesn't POST to external APIs

import { useState, useEffect, useCallback } from 'react';
import {
  Eye, EyeOff, Zap, AlertTriangle, TrendingUp, Brain,
  ChevronDown, ChevronUp, Clock, Target, DollarSign, CheckCircle
} from 'lucide-react';
import { cockpitApi } from '@/lib/api';
import type { ExecutionMode, PipelineRun, ShadowDecision } from '@/lib/types';

interface MABBar {
  angle: string;
  value: number;
  color: string;
}

const ANGLE_COLORS: Record<string, string> = {
  Fear: '#ef4444',
  Emotion: '#ec4899',
  Logic: '#3b82f6',
  'Social Proof': '#10b981',
  Urgency: '#f59e0b',
  Curiosity: '#8b5cf6',
};

function MabBeliefChart({ beliefs }: { beliefs: Record<string, number> }) {
  const bars: MABBar[] = Object.entries(beliefs)
    .map(([angle, value]) => ({ angle, value, color: ANGLE_COLORS[angle] ?? '#94a3b8' }))
    .sort((a, b) => b.value - a.value);
  const max = Math.max(...bars.map((b) => b.value), 0.001);

  return (
    <div className="flex flex-col gap-2">
      {bars.map(({ angle, value, color }) => (
        <div key={angle} className="flex items-center gap-3">
          <span className="text-xs text-slate-400 w-24 shrink-0">{angle}</span>
          <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{
                width: `${(value / max) * 100}%`,
                backgroundColor: color,
                boxShadow: `0 0 8px ${color}60`,
              }}
            />
          </div>
          <span className="text-xs font-mono text-slate-300 w-12 text-right">
            {(value * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}

function ShadowRunCard({ run }: { run: PipelineRun }) {
  const [expanded, setExpanded] = useState(false);
  const beliefs = run.initial_state?.current_beliefs ?? {};
  const variants = run.final_state?.generated_variants ?? [];
  const feedbacks = run.final_state?.sandbox_feedbacks ?? [];

  const topAngle = Object.entries(beliefs).sort((a, b) => b[1] - a[1])[0];
  const estSpend = (2000000 * variants.length).toLocaleString('vi-VN');

  const statusColor = {
    running: 'text-blue-400 bg-blue-500/10',
    completed: 'text-emerald-400 bg-emerald-500/10',
    failed: 'text-red-400 bg-red-500/10',
    quarantined: 'text-amber-400 bg-amber-500/10',
  }[run.status];

  const isLive = run.execution_mode === 'live';

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm overflow-hidden transition-all duration-200 hover:border-slate-700">
      {/* Card header */}
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="flex items-center gap-3">
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              isLive
                ? 'bg-emerald-500/10 border border-emerald-500/20'
                : 'bg-violet-500/10 border border-violet-500/20'
            }`}
          >
            {isLive ? (
              <Zap size={14} className="text-emerald-400" />
            ) : (
              <Eye size={14} className="text-violet-400" />
            )}
          </div>
          <div>
            <p className="text-sm font-medium text-slate-200">
              {isLive ? 'Live Run' : 'Shadow Run'}
            </p>
            <p className="text-xs text-slate-500 font-mono">
              {run.id.slice(0, 8)}…
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Status badge */}
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColor}`}>
            {run.status.toUpperCase()}
          </span>

          {/* Top angle */}
          {topAngle && (
            <div className="hidden sm:flex items-center gap-1.5 text-xs bg-slate-800 px-2 py-1 rounded-lg">
              <Brain size={10} className="text-violet-400" />
              <span className="text-slate-300">{topAngle[0]}</span>
              <span className="text-violet-400 font-mono">
                {(topAngle[1] * 100).toFixed(0)}%
              </span>
            </div>
          )}

          {/* Time */}
          <div className="flex items-center gap-1 text-xs text-slate-500">
            <Clock size={10} />
            {new Date(run.started_at).toLocaleTimeString()}
          </div>

          {expanded ? (
            <ChevronUp size={16} className="text-slate-500" />
          ) : (
            <ChevronDown size={16} className="text-slate-500" />
          )}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-slate-800 px-5 py-4 space-y-5">
          {/* Decision summary */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-slate-800/50 rounded-lg p-3">
              <p className="text-xs text-slate-500 mb-1 flex items-center gap-1">
                <Target size={10} /> Variants
              </p>
              <p className="text-2xl font-bold text-slate-200">{variants.length}</p>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3">
              <p className="text-xs text-slate-500 mb-1 flex items-center gap-1">
                <CheckCircle size={10} /> Passed Safety
              </p>
              <p className="text-2xl font-bold text-emerald-400">
                {variants.length - feedbacks.length}
              </p>
            </div>
            <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-3">
              <p className="text-xs text-amber-400 mb-1 flex items-center gap-1">
                <DollarSign size={10} /> Est. Spend (if live)
              </p>
              <p className="text-lg font-bold text-amber-300">{estSpend}₫</p>
            </div>
          </div>

          {/* MAB decision banner */}
          <div
            className={`rounded-lg px-4 py-3 border ${
              isLive
                ? 'bg-emerald-500/5 border-emerald-500/20'
                : 'bg-violet-500/5 border-violet-500/20'
            }`}
          >
            <p
              className={`text-sm font-medium ${
                isLive ? 'text-emerald-300' : 'text-violet-300'
              }`}
            >
              💭 AI quyết định:
            </p>
            <p className="text-xs text-slate-300 mt-1">
              Với dữ liệu hiện tại, MAB chọn góc tiếp cận&nbsp;
              <strong className={isLive ? 'text-emerald-300' : 'text-violet-300'}>
                {topAngle?.[0] ?? 'N/A'}
              </strong>
              &nbsp;cho {variants.length > 0 ? variants.length : 5} variants,
              dự kiến chi&nbsp;
              <strong className="text-amber-300">{estSpend}₫</strong>.
              {isLive ? (
                <span className="text-emerald-400 ml-2 font-semibold">
                  [Đang ở Live Mode — QUẢNG CÁO ĐÃ ĐƯỢC ĐĂNG THẬT]
                </span>
              ) : (
                <span className="text-slate-500 ml-2">
                  [Đang ở Shadow Mode — KHÔNG có tiền thật nào được tiêu]
                </span>
              )}
            </p>
          </div>

          {/* MAB Beliefs chart */}
          {Object.keys(beliefs).length > 0 && (
            <div>
              <p className="text-xs text-slate-400 font-medium mb-3 flex items-center gap-2">
                <TrendingUp size={12} /> MAB Belief Weights
              </p>
              <MabBeliefChart beliefs={beliefs} />
            </div>
          )}

          {/* Generated Variants */}
          {variants.length > 0 && (
            <div>
              <p className="text-xs text-slate-400 font-medium mb-2">
                Generated Variants ({variants.length})
              </p>
              <div className="space-y-2">
                {variants.slice(0, 3).map((v, i) => (
                  <div
                    key={v.variant_id ?? i}
                    className="text-xs bg-slate-800/50 rounded-lg p-3 border border-slate-700/50"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="px-1.5 py-0.5 rounded text-[10px] font-bold"
                        style={{
                          backgroundColor: `${ANGLE_COLORS[v.angle_name]}20`,
                          color: ANGLE_COLORS[v.angle_name],
                        }}
                      >
                        {v.angle_name}
                      </span>
                      <span className="text-slate-500">{v.platform}</span>
                    </div>
                    <p className="text-slate-300 line-clamp-2">{v.adapted_copy}</p>
                  </div>
                ))}
                {variants.length > 3 && (
                  <p className="text-xs text-slate-500 text-center">
                    +{variants.length - 3} more variants
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ShadowModePanel() {
  const [mode, setMode] = useState<ExecutionMode>('shadow');
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [listTab, setListTab] = useState<'shadow' | 'live'>('shadow');

  const fetchData = useCallback(async () => {
    try {
      const [modeRes, runsRes] = await Promise.all([
        cockpitApi.getExecutionMode(),
        cockpitApi.getRuns({ page_size: 100 }),
      ]);
      setMode(modeRes.mode);
      setRuns(runsRes.runs ?? []);
    } catch (err) {
      console.error('Failed to load shadow mode data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Sync listTab with active mode
  useEffect(() => {
    setListTab(mode);
  }, [mode]);

  const handleToggle = async () => {
    if (mode === 'shadow') {
      setShowConfirm(true);
    } else {
      // Switching back to shadow — no confirm needed
      await doToggle('shadow');
    }
  };

  const doToggle = async (newMode: ExecutionMode) => {
    setToggling(true);
    setShowConfirm(false);
    try {
      const res = await cockpitApi.setExecutionMode(newMode);
      setMode(res.mode);
    } catch (err) {
      console.error('Failed to toggle mode:', err);
    } finally {
      setToggling(false);
    }
  };

  const shadowRuns = runs.filter((r) => r.execution_mode === 'shadow');
  const liveRuns = runs.filter((r) => r.execution_mode === 'live');

  return (
    <div className="space-y-6">
      {/* Mode Toggle Card */}
      <div className="relative rounded-2xl border overflow-hidden"
        style={{
          borderColor: mode === 'live' ? '#22c55e40' : '#8b5cf640',
          background: mode === 'live'
            ? 'linear-gradient(135deg, #0f2a1a 0%, #0f172a 60%)'
            : 'linear-gradient(135deg, #1a0f2a 0%, #0f172a 60%)',
        }}
      >
        {/* Glow effect */}
        <div
          className="absolute inset-0 opacity-10 pointer-events-none"
          style={{
            background: mode === 'live'
              ? 'radial-gradient(circle at 20% 50%, #22c55e 0%, transparent 60%)'
              : 'radial-gradient(circle at 20% 50%, #8b5cf6 0%, transparent 60%)',
          }}
        />

        <div className="relative px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center"
              style={{
                background: mode === 'live' ? '#22c55e15' : '#8b5cf615',
                border: `1px solid ${mode === 'live' ? '#22c55e40' : '#8b5cf640'}`,
              }}
            >
              {mode === 'live' ? (
                <Zap size={24} className="text-emerald-400" />
              ) : (
                <Eye size={24} className="text-violet-400" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span
                  className="font-bold text-lg"
                  style={{ color: mode === 'live' ? '#22c55e' : '#a78bfa' }}
                >
                  {mode === 'live' ? '🟢 LIVE MODE' : '🔮 SHADOW MODE'}
                </span>
                {mode === 'live' && (
                  <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full animate-pulse">
                    REAL MONEY
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-400 mt-0.5">
                {mode === 'live'
                  ? 'AI đang tiêu tiền thật trên Facebook Ads. Giám sát chặt chẽ.'
                  : 'AI tính toán thật nhưng KHÔNG POST lên Facebook Ads. An toàn để quan sát.'}
              </p>
            </div>
          </div>

          {/* Toggle button */}
          <button
            onClick={handleToggle}
            disabled={toggling}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 disabled:opacity-50 ${
              mode === 'live'
                ? 'bg-violet-500/20 text-violet-300 hover:bg-violet-500/30 border border-violet-500/30'
                : 'bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/30'
            }`}
          >
            {toggling ? (
              <span className="animate-spin">⟳</span>
            ) : mode === 'live' ? (
              <EyeOff size={16} />
            ) : (
              <Zap size={16} />
            )}
            {mode === 'live' ? 'Switch to Shadow' : 'Go Live'}
          </button>
        </div>

        {/* Stats bar */}
        <div className="border-t border-white/5 px-6 py-3 grid grid-cols-3 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-violet-400">{shadowRuns.length}</p>
            <p className="text-xs text-slate-500">Shadow Runs</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-emerald-400">{liveRuns.length}</p>
            <p className="text-xs text-slate-500">Live Runs</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-slate-200">{runs.length}</p>
            <p className="text-xs text-slate-500">Total Runs</p>
          </div>
        </div>
      </div>

      {/* Go Live Confirm Modal */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-slate-900 border border-amber-500/30 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-amber-500/20 rounded-xl flex items-center justify-center">
                <AlertTriangle size={20} className="text-amber-400" />
              </div>
              <h3 className="text-lg font-bold text-slate-100">Chuyển sang Live Mode?</h3>
            </div>
            <p className="text-sm text-slate-300 mb-2">
              Khi ở <strong className="text-emerald-400">Live Mode</strong>, AI sẽ thực sự
              POST quảng cáo lên Facebook Ads và <strong>tiêu tiền thật</strong>.
            </p>
            <p className="text-sm text-slate-400 mb-6">
              Hãy đảm bảo team đã quan sát Shadow Mode ít nhất 1-2 tuần và đánh giá
              độ chính xác của AI trước khi tiếp tục.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-700 text-slate-300 hover:bg-slate-800 transition-colors text-sm"
              >
                Huỷ
              </button>
              <button
                onClick={() => doToggle('live')}
                className="flex-1 px-4 py-2.5 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30 transition-colors text-sm font-semibold"
              >
                Xác nhận Go Live
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Dynamic Runs List (Shadow vs Live) */}
      <div>
        <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-2">
          <div className="flex gap-2">
            <button
              onClick={() => setListTab('shadow')}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
                listTab === 'shadow'
                  ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30 font-semibold'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <Eye size={12} /> Shadow Decisions ({shadowRuns.length})
            </button>
            <button
              onClick={() => setListTab('live')}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
                listTab === 'live'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <Zap size={12} /> Live Decisions ({liveRuns.length})
            </button>
          </div>
          <button
            onClick={fetchData}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            ↻ Refresh
          </button>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 rounded-xl bg-slate-800/50 animate-pulse" />
            ))}
          </div>
        ) : listTab === 'shadow' ? (
          shadowRuns.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <Eye size={32} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">Chưa có Shadow Run nào.</p>
              <p className="text-xs mt-1">Trigger một pipeline từ tab Execute Agent.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {shadowRuns.map((run) => (
                <ShadowRunCard key={run.id} run={run} />
              ))}
            </div>
          )
        ) : (
          liveRuns.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <Zap size={32} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">Chưa có Live Run nào.</p>
              <p className="text-xs mt-1">Bật Live Mode và trigger một pipeline để chạy thật.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {liveRuns.map((run) => (
                <ShadowRunCard key={run.id} run={run} />
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}
