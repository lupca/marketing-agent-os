'use client';
// src/components/cockpit/CockpitLayout.tsx
// The Autopilot Cockpit — Main layout wrapper with 4 sub-tabs

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Eye, Radio, ShieldAlert, Zap, Wifi, WifiOff, AlertTriangle } from 'lucide-react';
import { useCockpitWebSocket } from '@/hooks/useCockpitWebSocket';
import { cockpitApi } from '@/lib/api';

import DagRadar from './DagRadar';
import QuarantineZone from './QuarantineZone';
import KillSwitch from './KillSwitch';
import type { CockpitWebSocketEvent } from '@/lib/types';

type CockpitTab = 'radar' | 'quarantine' | 'killswitch';

const TABS: { id: CockpitTab; label: string; icon: React.ReactNode; desc: string }[] = [
  {
    id: 'radar',
    label: 'DAG Radar',
    icon: <Radio size={16} />,
    desc: 'Real-time pipeline Glass-box monitor',
  },
  {
    id: 'quarantine',
    label: 'Quarantine Zone',
    icon: <ShieldAlert size={16} />,
    desc: 'Isolated tasks & state rehydration',
  },
  {
    id: 'killswitch',
    label: 'Kill Switch',
    icon: <Zap size={16} />,
    desc: 'Halt all external APIs immediately',
  },
];

export default function CockpitLayout() {
  const [activeTab, setActiveTab] = useState<CockpitTab>('radar');
  const [killSwitchActive, setKillSwitchActive] = useState(false);
  const [quarantineCount, setQuarantineCount] = useState(0);
  const [liveRunActive, setLiveRunActive] = useState(false);

  // Track kill switch and quarantine count via WebSocket
  const { connectionState } = useCockpitWebSocket((event: CockpitWebSocketEvent) => {
    if (event.type === 'kill_switch') {
      setKillSwitchActive(event.data.is_active as boolean);
    }
    if (event.type === 'quarantine') {
      setQuarantineCount((c) => c + 1);
    }
    if (event.type === 'run_start') {
      setLiveRunActive(true);
    }
    if (['run_complete', 'run_fail'].includes(event.type)) {
      setLiveRunActive(false);
    }
  });

  // Initial load
  useEffect(() => {
    const init = async () => {
      try {
        const [ks, qt] = await Promise.all([
          cockpitApi.getKillSwitch(),
          cockpitApi.getQuarantinedTasks(),
        ]);
        setKillSwitchActive(ks.is_active);
        setQuarantineCount((qt?.tasks ?? []).filter((t) => t.resolution_status === 'pending').length);
      } catch { /* ignore */ }
    };
    init();
  }, []);

  const isConnected = connectionState === 'connected';

  return (
    <div className="flex flex-col h-full">
      {/* Cockpit header */}
      <div className="flex flex-col gap-4 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
              <span className="text-3xl">🛩️</span>
              The Autopilot Cockpit
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Human-ON-the-Loop • Observability by Default, Intervention by Exception
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap justify-end">
            {/* Back to Dashboard Link */}
            <Link
              href="/"
              className="flex items-center gap-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white text-xs px-3 py-1.5 rounded-lg font-mono font-bold transition-all cursor-pointer mr-2"
            >
              ← Quay lại Dashboard
            </Link>

            {/* Kill switch warning badge */}
            {killSwitchActive && (
              <div className="flex items-center gap-1.5 bg-red-500/20 border border-red-500/40 text-red-300 text-xs px-3 py-1.5 rounded-lg font-bold animate-pulse">
                <AlertTriangle size={12} />
                KILL SWITCH ACTIVE
              </div>
            )}

            {/* Live run indicator */}
            {liveRunActive && (
              <div className="flex items-center gap-1.5 bg-blue-500/20 border border-blue-500/30 text-blue-300 text-xs px-3 py-1.5 rounded-lg">
                <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping" />
                Pipeline Running
              </div>
            )}

            {/* Quarantine alert */}
            {quarantineCount > 0 && (
              <div
                className="flex items-center gap-1.5 bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs px-3 py-1.5 rounded-lg cursor-pointer hover:bg-amber-500/30 transition-colors"
                onClick={() => setActiveTab('quarantine')}
              >
                <ShieldAlert size={12} />
                {quarantineCount} Quarantined
              </div>
            )}

            {/* WS connection */}
            <div className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border ${
              isConnected
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : 'bg-slate-800/50 border-slate-700 text-slate-500'
            }`}>
              {isConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
              {isConnected ? 'Live Stream' : 'Offline'}
            </div>
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex gap-2 border-b border-slate-800 pb-0">
          {TABS.map(({ id, label, icon, desc }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`
                relative flex items-center gap-2 px-4 py-3 text-sm font-medium
                border-b-2 transition-all duration-200 -mb-px rounded-t-lg
                ${activeTab === id
                  ? id === 'killswitch'
                    ? 'border-red-500 text-red-300 bg-red-500/5'
                    : id === 'quarantine'
                    ? 'border-amber-500 text-amber-300 bg-amber-500/5'
                    : id === 'radar'
                    ? 'border-blue-500 text-blue-300 bg-blue-500/5'
                    : 'border-violet-500 text-violet-300 bg-violet-500/5'
                  : 'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-600'
                }
              `}
              title={desc}
            >
              {icon}
              {label}

              {/* Badges */}
              {id === 'quarantine' && quarantineCount > 0 && (
                <span className="bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
                  {quarantineCount}
                </span>
              )}
              {id === 'killswitch' && killSwitchActive && (
                <span className="w-2 h-2 rounded-full bg-red-400 animate-ping" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'radar'      && <DagRadar />}
        {activeTab === 'quarantine' && <QuarantineZone />}
        {activeTab === 'killswitch' && <KillSwitch />}
      </div>
    </div>
  );
}
