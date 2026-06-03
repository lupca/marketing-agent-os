"use client";

import React from "react";
import {
  Cpu,
  Sparkles,
  Gauge,
  Sliders,
  Terminal,
  RotateCcw,
  Zap
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Line,
  LineChart as RechartsLineChart
} from "recharts";

// Mock Data for Performance Area Chart (Last 24 Hours)
const performanceData = [
  { hour: "00:00", successful: 42, edgeCases: 2 },
  { hour: "02:00", successful: 48, edgeCases: 4 },
  { hour: "04:00", successful: 35, edgeCases: 5 },
  { hour: "06:00", successful: 55, edgeCases: 3 },
  { hour: "08:00", successful: 72, edgeCases: 8 },
  { hour: "10:00", successful: 95, edgeCases: 12 },
  { hour: "12:00", successful: 110, edgeCases: 15 },
  { hour: "14:00", successful: 88, edgeCases: 9 },
  { hour: "16:00", successful: 104, edgeCases: 6 },
  { hour: "18:00", successful: 120, edgeCases: 4 },
  { hour: "20:00", successful: 135, edgeCases: 7 },
  { hour: "22:00", successful: 98, edgeCases: 3 }
];

// Sparkline Mock Data for Vector Indexing
const sparklineData = [
  { val: 40 }, { val: 42 }, { val: 45 }, { val: 41 }, { val: 48 }, { val: 44 }, { val: 45 }
];

interface EngineTelemetryProps {
  indexingSpeed: number;
  mutationRate: number;
  quotaUsed: number;
  generatedVariants: any[];
  objective: string;
  campaignName: string;
  logs: any[];
  setLogs: React.Dispatch<React.SetStateAction<any[]>>;
}

export default function EngineTelemetry({
  indexingSpeed,
  mutationRate,
  quotaUsed,
  generatedVariants,
  objective,
  campaignName,
  logs,
  setLogs
}: EngineTelemetryProps) {
  return (
    <>
      {/* METRICS CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Metric 1: Vector Indexing Speed */}
        <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 hover:border-slate-800/80 transition-all flex flex-col gap-3 group relative overflow-hidden font-sans">
          <div className="absolute top-0 right-0 h-16 w-16 bg-blue-500/5 blur-2xl group-hover:bg-blue-500/10 transition-all"></div>
          <div className="flex justify-between items-start">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">HNSW Indexing Velocity</span>
            <Cpu className="h-4 w-4 text-blue-500 animate-spin-slow" />
          </div>
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold tracking-tight text-slate-100 font-mono">
                {indexingSpeed}
              </span>
              <span className="text-xs font-semibold text-slate-500 font-mono">nodes/sec</span>
            </div>
            <div className="h-6 w-24">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsLineChart data={sparklineData}>
                  <Line type="monotone" dataKey="val" stroke="#3b82f6" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                </RechartsLineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Metric 2: LLM Format Mutation Rate */}
        <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 hover:border-slate-800/80 transition-all flex flex-col gap-3 group relative overflow-hidden font-sans">
          <div className="absolute top-0 right-0 h-16 w-16 bg-rose-500/5 blur-2xl group-hover:bg-rose-500/10 transition-all"></div>
          <div className="flex justify-between items-start">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">Format Mutation Rate</span>
            <Sparkles className="h-4 w-4 text-rose-500" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-3xl font-extrabold tracking-tight font-mono transition-colors duration-300 ${mutationRate > 5.0 ? "text-rose-500" : "text-slate-100"}`}>
              {mutationRate}%
            </span>
            <span className="text-xs font-semibold text-slate-500 font-mono">avg 24h</span>
          </div>
          <div className="flex items-center justify-between mt-1 text-[11px] text-slate-400">
            <span className={mutationRate > 5.0 ? "text-rose-400 font-semibold" : "text-slate-500"}>
              {mutationRate > 5.0 ? "⚠️ Critical: Halucinations High" : "✓ Within Safe Margin"}
            </span>
            <span className="text-[9px] font-mono bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700">
              Limit 5.0%
            </span>
          </div>
        </div>

        {/* Metric 3: API Quota Status */}
        <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 hover:border-slate-800/80 transition-all flex flex-col gap-3 group relative overflow-hidden font-sans">
          <div className="absolute top-0 right-0 h-16 w-16 bg-amber-500/5 blur-2xl group-hover:bg-amber-500/10 transition-all"></div>
          <div className="flex justify-between items-start">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">API Quota Usage</span>
            <Gauge className="h-4 w-4 text-amber-500" />
          </div>
          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-col">
              <span className="text-3xl font-extrabold tracking-tight text-slate-100 font-mono">
                {quotaUsed}%
              </span>
              <span className="text-[10px] text-slate-500 font-mono">1.2M tokens used today</span>
            </div>
            <div className="relative h-12 w-12 shrink-0">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path className="text-slate-800" strokeWidth="3" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path className={`${quotaUsed > 80 ? "text-amber-500" : "text-blue-500"} transition-all duration-500`} strokeWidth="3.5" strokeDasharray={`${quotaUsed}, 100`} strokeLinecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-slate-400">
                80%
              </div>
            </div>
          </div>
          <div className="flex items-center justify-between mt-1 text-[11px] text-slate-400">
            <span className={quotaUsed > 80 ? "text-amber-400" : "text-slate-500"}>
              {quotaUsed > 80 ? "⚠️ Approaching Daily Quota" : "✓ Normal Rate Limit Status"}
            </span>
          </div>
        </div>

      </div>

      {/* PERFORMANCE CHART */}
      <div className="bg-slate-900/25 border border-slate-900 rounded-xl p-5 space-y-4 font-sans">
        <div className="flex justify-between items-center">
          <div className="flex flex-col">
            <h2 className="text-sm font-extrabold text-slate-200 uppercase tracking-widest font-mono">Execution Performance Timeline</h2>
            <p className="text-xs text-slate-500 font-sans">Real-time aggregate comparison of successful autonomous executions vs edge-case triggers.</p>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-blue-500"></span>
              <span className="text-slate-400">Successful</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-rose-500"></span>
              <span className="text-slate-400">Edge Case Failed</span>
            </div>
          </div>
        </div>
        
        <div className="h-[280px] w-full bg-slate-950/20 p-2 border border-slate-900/60 rounded-lg">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={performanceData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorEdge" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="hour" stroke="#64748b" fontSize={10} fontStyle="mono" tickLine={false} />
              <YAxis stroke="#64748b" fontSize={10} fontStyle="mono" tickLine={false} />
              <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f1f5f9" }} />
              <Area type="monotone" dataKey="successful" stroke="#3b82f6" fillOpacity={1} fill="url(#colorSuccess)" strokeWidth={2} />
              <Area type="monotone" dataKey="edgeCases" stroke="#ef4444" fillOpacity={1} fill="url(#colorEdge)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* DYNAMIC RESULTS DISPLAY (REAL-TIME WIRING RESPONSE) */}
      {generatedVariants.length > 0 && (
        <div className="bg-slate-900/25 border border-emerald-500/20 rounded-xl p-5 space-y-4 font-sans">
          <div className="flex justify-between items-center border-b border-slate-900 pb-3">
            <div className="flex items-center gap-2">
              <Zap className="h-4.5 w-4.5 text-emerald-400 fill-emerald-400/10" />
              <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-slate-200">Generated Ad Creative Variants (Live Backend Payload)</h3>
            </div>
            <span className="text-[9px] font-mono bg-emerald-950/20 text-emerald-400 border border-emerald-900/30 px-3 py-0.5 rounded-full font-bold">
              PIPELINE COMPLETED
            </span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {generatedVariants.map((v, i) => (
              <div key={i} className="bg-slate-950/60 border border-slate-900 rounded-lg p-4 space-y-3 font-mono text-xs">
                <div className="flex justify-between items-center text-[10px] text-slate-400">
                  <span className="font-bold uppercase tracking-wider text-blue-400">{v.platform || "Platform"} variant</span>
                  <span>ID: {v.variant_id}</span>
                </div>
                <p className="text-xs text-slate-200 font-sans whitespace-pre-wrap leading-relaxed">{v.adapted_copy || v.copy}</p>
                <div className="flex justify-between items-center border-t border-slate-900/80 pt-2 text-[9px] text-slate-500">
                  <span>Objective: {objective}</span>
                  <span className="bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">ADMAPPER_LINKED</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SYSTEM INFORMATION OBSERVED (HIGH DENSITY TABLE) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 font-sans">
        
        {/* Section A: Live Node Monitor */}
        <div className="bg-slate-900/25 border border-slate-900 rounded-xl p-5 space-y-4 lg:col-span-2">
          <div className="flex justify-between items-center border-b border-slate-900 pb-3">
            <div className="flex items-center gap-2">
              <Sliders className="h-4 w-4 text-blue-400" />
              <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-slate-300">Stateless Agent Pipeline Operations</h3>
            </div>
            <span className="text-[9px] font-mono font-bold tracking-widest bg-slate-800 text-slate-400 px-2 py-0.5 rounded border border-slate-700">
              LIVE NODES
            </span>
          </div>
          
          <div className="space-y-3 font-mono text-xs">
            {[
              { node: "scoring_node", desc: "MAB Beliefs evaluation and ranking", state: "COMPLETED", duration: "12ms", logs: "Solved cold-start baseline averages successfully." },
              { node: "action_selector_node", desc: "Epsilon-Greedy 80/20 creative mix formulation", state: "COMPLETED", duration: "5ms", logs: "Mix formulated: ['Social Proof', 'Social Proof', 'Social Proof', 'Social Proof', 'Urgency']" },
              { node: "creative_generation_node", desc: "Asset extraction & LLM copies writing", state: "COMPLETED", duration: "1150ms", logs: "Successfully loaded TOPVNSPORT identity metrics." },
              { node: "guardian_sandbox_node", desc: "Compliance safety and anti-pattern assessment", state: "COMPLETED", duration: "320ms", logs: "Sandbox score: 92. Safety constraints cleared." },
              { node: "insight_generator_node", desc: "Metrics drift explanation writing", state: "COMPLETED", duration: "840ms", logs: "Insight safely parsed and persisted in ai_insights_pending." }
            ].map((item, idx) => (
              <div key={idx} className="flex flex-col md:flex-row md:items-center justify-between p-3 bg-slate-950/40 border border-slate-900 rounded-lg gap-2 hover:border-slate-800/80 transition-all">
                <div className="flex flex-col gap-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-blue-400 font-bold">{item.node}</span>
                    <span className="text-slate-600 font-sans">|</span>
                    <span className="text-slate-500 font-sans text-[11px] truncate">{item.desc}</span>
                  </div>
                  <span className="text-slate-400 text-[10px] truncate">&gt; {item.logs}</span>
                </div>
                <div className="flex items-center justify-between md:justify-end gap-4 shrink-0 text-right">
                  <span className="text-[11px] text-slate-500">{item.duration}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-950/30">
                    {item.state}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Section B: Live Web Telemetry (REAL-TIME WS BROADCSTER) */}
        <div className="bg-slate-900/25 border border-slate-900 rounded-xl p-5 space-y-4">
          <div className="flex justify-between items-center border-b border-slate-900 pb-3">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-emerald-400" />
              <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-slate-300">Live Agent Telemetry Stream</h3>
            </div>
            <button
              onClick={() => setLogs([])}
              className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1 font-mono"
            >
              <RotateCcw className="h-3 w-3" /> CLEAR
            </button>
          </div>
          
          <div className="space-y-3 h-[250px] overflow-y-auto pr-1 font-mono text-[9px] leading-relaxed">
            {logs.map((log, idx) => (
              <div key={idx} className="flex gap-2 text-slate-300">
                <span className="text-slate-500 shrink-0 select-none">{log.time}</span>
                <span className={`font-bold shrink-0 select-none ${
                  log.tag === "SUCCESS" || log.tag === "INFO"
                    ? "text-blue-500"
                    : log.tag === "WARNING" || log.tag === "WARN"
                    ? "text-amber-500"
                    : "text-rose-500"
                }`}>
                  [{log.tag}]
                </span>
                <span className="text-slate-400 shrink-0 font-bold select-none">{log.src}:</span>
                <span className="text-slate-300 break-all">{log.msg}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </>
  );
}
