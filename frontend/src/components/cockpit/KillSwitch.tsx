'use client';
// src/components/cockpit/KillSwitch.tsx
// Emergency Kill Switch: halt all external API calls immediately

import { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, Zap, ZapOff, Clock, User, RefreshCw, Shield } from 'lucide-react';
import { cockpitApi } from '@/lib/api';
import { useCockpitWebSocket } from '@/hooks/useCockpitWebSocket';
import type { KillSwitchStatus, CockpitWebSocketEvent } from '@/lib/types';

// ─── Animated Kill Switch Button ──────────────────────────────────────────────

function KillSwitchButton({
  isActive,
  onClick,
  disabled,
}: {
  isActive: boolean;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        relative w-full max-w-xs mx-auto flex flex-col items-center justify-center
        rounded-full aspect-square p-8 transition-all duration-500
        disabled:opacity-50 disabled:cursor-not-allowed
        group select-none
        ${isActive
          ? 'bg-red-950 border-4 border-red-500 shadow-[0_0_60px_rgba(239,68,68,0.6)] hover:shadow-[0_0_80px_rgba(239,68,68,0.8)] kill-switch-active'
          : 'bg-slate-900 border-2 border-slate-700 hover:border-slate-500 hover:shadow-[0_0_30px_rgba(100,116,139,0.3)]'
        }
      `}
    >
      {/* Outer glow ring when active */}
      {isActive && (
        <div className="absolute inset-0 rounded-full border-4 border-red-400 animate-ping opacity-30" />
      )}

      {/* Icon */}
      <div className={`mb-3 transition-transform duration-300 group-hover:scale-110 ${isActive ? 'text-red-400' : 'text-slate-500'}`}>
        {isActive ? <ZapOff size={48} /> : <Zap size={48} />}
      </div>

      {/* Label */}
      <p className={`text-sm font-black uppercase tracking-widest text-center leading-tight ${
        isActive ? 'text-red-300' : 'text-slate-400'
      }`}>
        {isActive ? 'HALTED' : 'ACTIVATE'}
      </p>
      <p className={`text-xs mt-1 text-center ${isActive ? 'text-red-400/70' : 'text-slate-600'}`}>
        {isActive ? 'All APIs Frozen' : 'Kill Switch'}
      </p>
    </button>
  );
}

// ─── Confirm Modal ─────────────────────────────────────────────────────────────

function ConfirmActivateModal({
  onConfirm,
  onCancel,
}: {
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}) {
  const [reason, setReason] = useState('');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-red-500/40 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-red-500/20 rounded-2xl flex items-center justify-center">
            <AlertTriangle size={24} className="text-red-400" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-red-300">Kích hoạt Kill Switch?</h3>
            <p className="text-xs text-slate-500">Hành động này không thể hoàn tác ngay lập tức</p>
          </div>
        </div>

        <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 mb-4 space-y-1.5">
          <p className="text-xs text-red-300 font-semibold">Khi kích hoạt:</p>
          <ul className="text-xs text-slate-300 space-y-1 list-disc list-inside">
            <li>Toàn bộ lệnh POST lên Facebook Ads API bị chặn</li>
            <li>Celery social publisher tasks bị blocked</li>
            <li>Pipeline nội bộ vẫn chạy để phân tích</li>
            <li><strong className="text-red-300">Không có tiền nào bị tiêu</strong> cho đến khi tắt Kill Switch</li>
          </ul>
        </div>

        <label className="block mb-4">
          <span className="text-xs text-slate-400 mb-1.5 block font-medium">
            Lý do kích hoạt <span className="text-red-400">*</span>
          </span>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="VD: Phát hiện chi tiêu bất thường, sự kiện khủng hoảng thương hiệu..."
            rows={3}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-red-500 resize-none"
          />
        </label>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-700 text-slate-300 hover:bg-slate-800 transition-colors text-sm"
          >
            Huỷ bỏ
          </button>
          <button
            onClick={() => reason.trim() && onConfirm(reason.trim())}
            disabled={!reason.trim()}
            className="flex-1 px-4 py-2.5 rounded-xl bg-red-500/20 border border-red-500/40 text-red-300 hover:bg-red-500/30 transition-colors text-sm font-bold disabled:opacity-40 disabled:cursor-not-allowed"
          >
            ⚡ KÍCH HOẠT
          </button>
        </div>
      </div>
    </div>
  );
}

function ConfirmDeactivateModal({
  onConfirm,
  onCancel,
}: {
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [step, setStep] = useState(1);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-emerald-500/40 rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-emerald-500/20 rounded-xl flex items-center justify-center">
            <Shield size={18} className="text-emerald-400" />
          </div>
          <h3 className="font-bold text-emerald-300">Tắt Kill Switch?</h3>
        </div>

        {step === 1 ? (
          <>
            <p className="text-sm text-slate-300 mb-2">
              Tắt Kill Switch sẽ cho phép hệ thống tiếp tục tiêu tiền trên Facebook Ads.
            </p>
            <p className="text-xs text-slate-500 mb-4">
              Hãy đảm bảo vấn đề đã được giải quyết trước khi tiếp tục.
            </p>
            <div className="flex gap-3">
              <button onClick={onCancel} className="flex-1 px-4 py-2 rounded-xl border border-slate-700 text-slate-400 text-sm">Huỷ</button>
              <button onClick={() => setStep(2)} className="flex-1 px-4 py-2 rounded-xl bg-amber-500/20 border border-amber-500/30 text-amber-300 text-sm">
                Xác nhận lần 1
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="text-sm text-amber-300 font-bold mb-3">Xác nhận lần 2 — Resume APIs?</p>
            <div className="flex gap-3">
              <button onClick={onCancel} className="flex-1 px-4 py-2 rounded-xl border border-slate-700 text-slate-400 text-sm">Huỷ</button>
              <button
                onClick={onConfirm}
                className="flex-1 px-4 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-sm font-bold"
              >
                ✅ RESUME APIS
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Main KillSwitch ──────────────────────────────────────────────────────────

export default function KillSwitch() {
  const [status, setStatus] = useState<KillSwitchStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [showActivateModal, setShowActivateModal] = useState(false);
  const [showDeactivateModal, setShowDeactivateModal] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await cockpitApi.getKillSwitch();
      setStatus(data);
    } catch (err) {
      console.error('Failed to load kill switch status:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // Real-time WebSocket updates
  useCockpitWebSocket(
    useCallback((event: CockpitWebSocketEvent) => {
      if (event.type === 'kill_switch') {
        setStatus((prev) => prev ? {
          ...prev,
          is_active: event.data.is_active as boolean,
          activated_by: event.data.activated_by as string ?? prev.activated_by,
          activated_at: event.data.activated_at as string ?? prev.activated_at,
          reason: event.data.reason as string ?? prev.reason,
        } : null);
      }
    }, [])
  );

  const handleActivate = async (reason: string) => {
    setActing(true);
    setShowActivateModal(false);
    try {
      const data = await cockpitApi.activateKillSwitch({ reason, activated_by: 'Engineer' });
      setStatus(data);
    } catch (err) {
      console.error('Failed to activate kill switch:', err);
    } finally {
      setActing(false);
    }
  };

  const handleDeactivate = async () => {
    setActing(true);
    setShowDeactivateModal(false);
    try {
      const data = await cockpitApi.deactivateKillSwitch({ deactivated_by: 'Engineer' });
      setStatus(data);
    } catch (err) {
      console.error('Failed to deactivate kill switch:', err);
    } finally {
      setActing(false);
    }
  };

  const isActive = status?.is_active ?? false;

  return (
    <div className="space-y-6">
      {/* Main control */}
      <div className={`relative rounded-2xl border overflow-hidden transition-all duration-500 ${
        isActive
          ? 'border-red-500/50 bg-red-950/30'
          : 'border-slate-800 bg-slate-900/40'
      }`}>
        {/* Active background glow */}
        {isActive && (
          <div className="absolute inset-0 bg-gradient-to-br from-red-950/50 via-transparent to-transparent pointer-events-none" />
        )}

        <div className="relative px-8 py-10 flex flex-col items-center gap-6">
          {/* Status banner */}
          {isActive ? (
            <div className="flex items-center gap-3 bg-red-500/20 border border-red-500/40 rounded-xl px-5 py-3 w-full justify-center">
              <span className="w-2 h-2 rounded-full bg-red-400 animate-ping" />
              <span className="text-red-300 font-bold text-sm tracking-wide">
                ⚠️ ALL EXTERNAL APIS HALTED
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-5 py-3 w-full justify-center">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-emerald-400 font-medium text-sm">✅ Systems Normal — APIs Active</span>
            </div>
          )}

          {/* The Big Button */}
          {loading ? (
            <div className="w-56 h-56 rounded-full bg-slate-800/50 animate-pulse" />
          ) : (
            <KillSwitchButton
              isActive={isActive}
              disabled={acting}
              onClick={() => isActive ? setShowDeactivateModal(true) : setShowActivateModal(true)}
            />
          )}

          {/* Acting spinner */}
          {acting && (
            <div className="flex items-center gap-2 text-slate-400 text-sm">
              <RefreshCw size={14} className="animate-spin" />
              Processing…
            </div>
          )}
        </div>
      </div>

      {/* Kill switch details (when active) */}
      {isActive && status && (
        <div className="rounded-xl border border-red-500/20 bg-red-950/20 p-5 space-y-3">
          <h4 className="text-sm font-semibold text-red-300 flex items-center gap-2">
            <AlertTriangle size={14} /> Kill Switch Active Details
          </h4>
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <p className="text-slate-500 mb-1 flex items-center gap-1"><User size={10} /> Activated By</p>
              <p className="text-slate-200 font-medium">{status.activated_by ?? '—'}</p>
            </div>
            <div>
              <p className="text-slate-500 mb-1 flex items-center gap-1"><Clock size={10} /> Activated At</p>
              <p className="text-slate-200 font-medium">
                {status.activated_at ? new Date(status.activated_at).toLocaleString() : '—'}
              </p>
            </div>
            <div className="col-span-2">
              <p className="text-slate-500 mb-1 font-medium">Reason</p>
              <p className="text-red-200 bg-red-500/10 rounded-lg px-3 py-2">{status.reason ?? '—'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Information panel */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5 space-y-3">
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Phạm vi ảnh hưởng của Kill Switch
        </h4>
        <div className="space-y-2">
          {[
            { icon: '🔴', label: 'Facebook Ads API', desc: 'Blocked — No creative/ads publishing', blocked: true },
            { icon: '🔴', label: 'Social Publisher (Celery)', desc: 'Blocked — Queue paused', blocked: true },
            { icon: '🔴', label: 'Media Sync Tasks', desc: 'Blocked — No spend operations', blocked: true },
            { icon: '🟢', label: 'Internal LangGraph', desc: 'Active — Graph continues for analysis', blocked: false },
            { icon: '🟢', label: 'Dashboard & Monitoring', desc: 'Active — Full observability maintained', blocked: false },
            { icon: '🟢', label: 'RAG & Knowledge Base', desc: 'Active — Reading ops unaffected', blocked: false },
          ].map(({ icon, label, desc, blocked }) => (
            <div key={label} className="flex items-start gap-3">
              <span className="text-sm shrink-0">{icon}</span>
              <div>
                <p className={`text-xs font-medium ${blocked ? 'text-red-300' : 'text-emerald-300'}`}>
                  {label}
                </p>
                <p className="text-xs text-slate-500">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Modals */}
      {showActivateModal && (
        <ConfirmActivateModal
          onConfirm={handleActivate}
          onCancel={() => setShowActivateModal(false)}
        />
      )}
      {showDeactivateModal && (
        <ConfirmDeactivateModal
          onConfirm={handleDeactivate}
          onCancel={() => setShowDeactivateModal(false)}
        />
      )}
    </div>
  );
}
