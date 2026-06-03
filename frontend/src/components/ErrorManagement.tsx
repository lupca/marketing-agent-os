"use client";

import React, { useState, useEffect } from "react";
import {
  AlertTriangle,
  Database,
  FileCode2,
  Clock,
  Layers,
  Flame,
  RefreshCw
} from "lucide-react";
import { useToast } from "@/components/ui/Toast";

interface ErrorManagementProps {
  mutationRate: number;
  isLockReleased: boolean;
  setIsLockReleased: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function ErrorManagement({
  mutationRate,
  isLockReleased,
  setIsLockReleased
}: ErrorManagementProps) {
  const { showToast } = useToast();
  const [errorTab, setErrorTab] = useState("cold-start");

  // Tab 2: LLM Format Mutation interactive states
  const [rawLlmOutput, setRawLlmOutput] = useState(`\`\`\`json
{
  "insight": "CPA reduction due to Social Proof focus",
  "recommended_bid": 1.25,
  "mab_priors": {
    "Fear": 0.16,
    "Social Proof": 0.8
  }
}
\`\`\``);

  const [expectedSchema] = useState(`{
  "insight": "CPA reduction due to Social Proof focus",
  "recommended_bid": 1.25,
  "mab_priors": {
    "Fear": 0.16,
    "Social Proof": 0.8
  }
}`);

  // Tab 3: Backoff / Timeout states
  const [backoffCountdown, setBackoffCountdown] = useState(8);
  const [isBackoffActive, setIsBackoffActive] = useState(true);
  const [backoffAttempts, setBackoffAttempts] = useState([
    { id: 1, type: "Ollama HTTP 429 Too Many Requests", delay: "2s", status: "FAILED" },
    { id: 2, type: "Ollama HTTP 429 Too Many Requests", delay: "4s", status: "FAILED" },
    { id: 3, type: "Active Connection Backoff", delay: "8s", status: "RETRYING" }
  ]);

  // Backoff countdown timer simulation
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isBackoffActive && backoffCountdown > 0 && errorTab === "backoff") {
      timer = setTimeout(() => setBackoffCountdown(prev => prev - 1), 1000);
    } else if (backoffCountdown === 0 && isBackoffActive) {
      setIsBackoffActive(false);
      setBackoffAttempts(prev => [
        ...prev.slice(0, 2),
        { id: 3, type: "Ollama Connection Established", delay: "8s", status: "SUCCESS" }
      ]);
      showToast("Rate limit timeout cleared. Execution finished.", "success");
    }
    return () => clearTimeout(timer);
  }, [backoffCountdown, isBackoffActive, errorTab, showToast]);

  const handleReparseJson = () => {
    showToast("Parsing and stripping markdown block...", "info");
    setTimeout(() => {
      setRawLlmOutput(expectedSchema);
      showToast("Markdown block stripped. JSON recovered successfully!", "success");
    }, 1000);
  };

  const handleForceBackoffRetry = () => {
    setBackoffCountdown(0);
    setIsBackoffActive(true);
    showToast("Manual force retry triggered immediately.", "info");
  };

  const handleReleaseDbLock = () => {
    setIsLockReleased(true);
    showToast("Transaction rolled back. Locks released successfully.", "success");
  };

  return (
    <div className="space-y-6 font-sans">
      <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="space-y-1">
          <h2 className="text-sm font-extrabold uppercase tracking-widest font-mono text-slate-350 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rose-500 fill-rose-500/10" /> Autonomous Agent Edge Case Troubleshooting
          </h2>
          <p className="text-xs text-slate-400">Deep-observability dashboard for handling cold-starts, LLM hallucinations, rate-limits, and lock race conditions.</p>
        </div>
        <span className="text-[10px] font-mono bg-rose-950/20 text-rose-450 px-3 py-1 rounded-full border border-rose-900/30 shrink-0 font-bold tracking-widest uppercase">
          SYSTEM IMMUNOLOGY ENGINE
        </span>
      </div>

      {/* TAB NAVIGATION SELECTORS */}
      <div className="flex border-b border-slate-900 gap-2 font-mono text-xs uppercase overflow-x-auto whitespace-nowrap">
        {[
          { id: "cold-start", label: "Cold Start Solver", icon: Database },
          { id: "mutation", label: "LLM Mutation Parser", icon: FileCode2 },
          { id: "backoff", label: "Timeout Backoff Monitor", icon: Clock },
          { id: "deadlock", label: "DB Concurrency Deadlock", icon: Layers }
        ].map((tab) => {
          const Icon = tab.icon;
          const isTabActive = errorTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setErrorTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 font-bold tracking-widest transition-all cursor-pointer ${
                isTabActive
                  ? "border-blue-500 text-blue-400 bg-slate-900/10"
                  : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/20"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB CONTENT ISOLATOR */}
      <div className="bg-slate-900/25 border border-slate-900 rounded-xl p-6">
        
        {/* TAB 1: COLD START SOLVER */}
        {errorTab === "cold-start" && (
          <div className="space-y-6">
            <div className="flex justify-between items-center border-b border-slate-900 pb-3">
              <div className="flex items-center gap-2">
                <Database className="h-4.5 w-4.5 text-blue-400" />
                <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-slate-200">Absolute Cold-Start Bootstrapping</h3>
              </div>
              <span className="text-[10px] font-mono bg-purple-950/20 text-purple-400 border border-purple-900/30 px-2 py-0.5 rounded">
                SQL BASELINE AVERAGES
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed font-sans max-w-3xl">
              When a campaign has zero historical performance data, MAB cannot construct metrics-based rewards. 
              Instead of semantic RAG queries that might poison local vector spaces, the system calculates average aggregates via a relational PostgreSQL database baseline, enabling uniform priors allocation.
            </p>

            <div className="space-y-4">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">Cold-Start Database Averages Table</div>
              
              <div className="overflow-x-auto border border-slate-900 rounded-lg">
                <table className="w-full text-left font-mono text-xs">
                  <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-900 uppercase text-[9px] tracking-wider font-bold">
                    <tr>
                      <th className="p-3">Campaign Reference</th>
                      <th className="p-3">Empty State Vector</th>
                      <th className="p-3">Injected SQL Baselines (AVG)</th>
                      <th className="p-3 text-right">Fallback Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900 bg-slate-950/20">
                    {[
                      { id: "ab510edb-0d33-4c94-b554-633481fee8d4", state: "EMPTY_MAB_BELIEFS", baseline: "impressions=10000.0, clicks=500.0, conv=10.0, spend=2M", status: "UNIFORM_PRIORS" },
                      { id: "e85cc120-cfbc-4188-8255-7ea7d1d293f9", state: "EMPTY_MAB_BELIEFS", baseline: "impressions=10000.0, clicks=500.0, conv=10.0, spend=2M", status: "UNIFORM_PRIORS" }
                    ].map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/10">
                        <td className="p-3 font-semibold text-slate-300 font-mono text-[11px] truncate max-w-[180px]">{row.id}</td>
                        <td className="p-3 text-rose-455 text-[10px] font-bold">
                          <span className="inline-flex items-center gap-1"><Flame className="h-3 w-3" /> {row.state}</span>
                        </td>
                        <td className="p-3 text-slate-400 text-[11px] font-mono">{row.baseline}</td>
                        <td className="p-3 text-right">
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-bold bg-purple-950/20 text-purple-400 border border-purple-900/30 uppercase tracking-widest font-mono">
                            {row.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: LLM MUTATION PARSER */}
        {errorTab === "mutation" && (
          <div className="space-y-6">
            <div className="flex justify-between items-center border-b border-slate-900 pb-3">
              <div className="flex items-center gap-2">
                <FileCode2 className="h-4.5 w-4.5 text-blue-400" />
                <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-slate-200">LLM Markdown & Format Mutation Recovery</h3>
              </div>
              <span className="text-[10px] font-mono bg-cyan-950/20 text-cyan-400 border border-cyan-900/30 px-2 py-0.5 rounded">
                MUTATION IMMUNITY DEPLOYED
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed font-sans max-w-3xl">
              LLM models frequently hallucinate raw markdown formatting (such as wrapping objects with ` ```json ` tags) which throws severe `JSONDecodeError` during relational database parsing operations. 
              Our robust Regex and regex-stripper filters isolate the JSON payload cleanly.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-mono text-xs">
              
              {/* Left Block: Raw Hallucinated output */}
              <div className="flex flex-col gap-2">
                <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider text-rose-450">
                  <span>Raw Hallucinated LLM Output</span>
                  <span className="bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded border border-rose-900/25">DIRTY STATE</span>
                </div>
                <textarea
                  value={rawLlmOutput}
                  onChange={(e) => setRawLlmOutput(e.target.value)}
                  className="w-full h-56 bg-slate-950 border border-slate-900 rounded-lg p-3 outline-none text-rose-350 font-mono text-[11px] leading-relaxed focus:border-rose-900 resize-none"
                />
              </div>

              {/* Right Block: Expected Compliant output */}
              <div className="flex flex-col gap-2">
                <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider text-emerald-450">
                  <span>Post-Regex Parsed Pure JSON Schema</span>
                  <span className="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-900/25">RECOVERED STATE</span>
                </div>
                <div className="w-full h-56 bg-slate-950 border border-slate-900 rounded-lg p-3 overflow-y-auto text-emerald-400 font-mono text-[11px] leading-relaxed">
                  <pre>{expectedSchema}</pre>
                </div>
              </div>

            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={handleReparseJson}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-xs font-bold uppercase tracking-widest rounded-lg shadow-md border border-blue-500/30 hover:-translate-y-0.5 transition-all font-mono cursor-pointer"
              >
                <RefreshCw className="h-3.5 w-3.5" /> Strip Markdown Wrapper & Reparse
              </button>
            </div>
          </div>
        )}

        {/* TAB 3: TIMEOUT BACKOFF MONITOR */}
        {errorTab === "backoff" && (
          <div className="space-y-6">
            <div className="flex justify-between items-center border-b border-slate-900 pb-3">
              <div className="flex items-center gap-2">
                <Clock className="h-4.5 w-4.5 text-blue-400" />
                <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-slate-200">Tenacity Exponential Backoff Retry Monitor</h3>
              </div>
              <span className="text-[10px] font-mono bg-amber-950/20 text-amber-400 border border-amber-900/30 px-2 py-0.5 rounded animate-pulse font-bold">
                RETRIES ENFORCED
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed font-sans max-w-3xl">
              LLM APIs routinely block calls due to network bottlenecks or rate limits (HTTP 429). 
              Rather than collapsing executions, a robust `tenacity` retry wrapper leverages exponential backoff and randomized jitter to guarantee auto-recovery.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 font-mono text-xs">
              
              {/* Left: Interactive Progress Area */}
              <div className="md:col-span-2 space-y-4">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">Retry Retrospective Timeline</div>
                
                <div className="space-y-3">
                  {backoffAttempts.map((attempt) => (
                    <div
                      key={attempt.id}
                      className={`p-3 bg-slate-950/40 border rounded-lg flex items-center justify-between gap-3 ${
                        attempt.status === "FAILED"
                          ? "border-rose-950/30 text-rose-400"
                          : attempt.status === "SUCCESS"
                          ? "border-emerald-950/30 text-emerald-400"
                          : "border-amber-950/30 text-amber-400 bg-amber-955/5 animate-pulse"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-bold">Attempt {attempt.id}:</span>
                        <span>{attempt.type}</span>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] shrink-0 font-bold">
                        <span>Backoff {attempt.delay}</span>
                        <span className={`px-2 py-0.5 rounded text-[9px] uppercase tracking-wider ${
                          attempt.status === "FAILED"
                            ? "bg-rose-500/10 text-rose-500"
                            : attempt.status === "SUCCESS"
                            ? "bg-emerald-500/10 text-emerald-500"
                            : "bg-amber-500/10 text-amber-500"
                        }`}>
                          {attempt.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right: countdown visualization */}
              <div className="bg-slate-955/40 border border-slate-900 rounded-xl p-5 flex flex-col justify-between items-center gap-4 text-center">
                <div className="space-y-1">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Backoff Countdown</div>
                  <div className="text-4xl font-extrabold text-amber-500 animate-pulse font-mono py-2">
                    {backoffCountdown > 0 ? `${backoffCountdown}s` : "RESOLVED"}
                  </div>
                </div>

                <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-amber-500 h-1.5 transition-all duration-1000"
                    style={{ width: `${(backoffCountdown / 8) * 100}%` }}
                  ></div>
                </div>

                <div className="flex gap-2 w-full">
                  <button
                    onClick={handleForceBackoffRetry}
                    className="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold uppercase tracking-wider rounded text-[10px] border border-slate-700 font-mono cursor-pointer"
                  >
                    Force Retry
                  </button>
                  <button
                    onClick={() => {
                      setIsBackoffActive(false);
                      showToast("Retry thread terminated by developer", "error");
                    }}
                    className="flex-1 py-1.5 bg-rose-955/20 text-rose-400 hover:bg-rose-955/40 font-bold uppercase tracking-wider rounded text-[10px] border border-rose-900/30 font-mono cursor-pointer"
                  >
                    Terminate
                  </button>
                </div>
              </div>

            </div>
          </div>
        )}

        {/* TAB 4: CONCURRENCY DEADLOCK */}
        {errorTab === "deadlock" && (
          <div className="space-y-6">
            <div className="flex justify-between items-center border-b border-slate-900 pb-3">
              <div className="flex items-center gap-2">
                <Layers className="h-4.5 w-4.5 text-blue-400" />
                <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-slate-200">Database Row-Lock Race Condition</h3>
              </div>
              <span className="text-[10px] font-mono bg-rose-950/20 text-rose-450 border border-rose-900/30 px-2 py-0.5 rounded">
                CONCURRENCY COLLISION
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed font-sans max-w-3xl">
              In highly active parallel executions, threads trying to resolve `PlatformVariant` inserts and write mapped `AdMapper` relations can experience database deadlocks. 
              Our single atomic transaction blocks automatically capture locks, rolling back cleanly on failures to avoid orphan records.
            </p>

            <div className="space-y-4 font-mono text-xs">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">Database Concurrency Collision Timeline</div>

              <div className="bg-slate-955 border border-slate-900 rounded-lg p-5 space-y-4">
                <div className="relative h-16 w-full bg-slate-900/50 border border-slate-800 rounded flex items-center overflow-hidden">
                  <div className="absolute left-6 h-7 w-[45%] bg-blue-500/10 border border-blue-500/40 text-blue-400 font-bold px-2 py-1 rounded flex items-center justify-between">
                    <span>PLATFORM_VARIANT Write</span>
                    <span>t=0ms</span>
                  </div>

                  <div className="absolute left-[38%] h-7 w-[45%] bg-purple-500/10 border border-purple-500/40 text-purple-400 font-bold px-2 py-1 rounded flex items-center justify-between">
                    <span>AD_MAPPER Insert</span>
                    <span>t=24.5ms</span>
                  </div>

                  {!isLockReleased && (
                    <div className="absolute left-[41%] top-0 bottom-0 w-0.5 bg-rose-500 flex items-center justify-center">
                      <div className="h-6 w-6 rounded-full bg-rose-500/25 border border-rose-500 flex items-center justify-center animate-ping">
                        <span className="text-[8px] text-white">X</span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex justify-between items-center text-[10px] text-slate-500">
                  <span>0ms</span>
                  <span>Collision Lock Detected at t=24.5ms</span>
                  <span>100ms</span>
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={handleReleaseDbLock}
                disabled={isLockReleased}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-500 disabled:border-slate-800 text-white text-xs font-bold uppercase tracking-widest rounded-lg shadow-md border border-rose-500/30 hover:-translate-y-0.5 transition-all font-mono cursor-pointer"
              >
                {isLockReleased ? "✓ Deadlock Released & Rolled Back" : "Release Lock & Trigger Rollback"}
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
