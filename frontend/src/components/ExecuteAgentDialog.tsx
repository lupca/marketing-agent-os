"use client";

import React from "react";
import { Zap, X, Loader2 } from "lucide-react";

interface ExecuteAgentDialogProps {
  isExecuteOpen: boolean;
  setIsExecuteOpen: React.Dispatch<React.SetStateAction<boolean>>;
  isExecuting: boolean;
  objective: string;
  setObjective: React.Dispatch<React.SetStateAction<string>>;
  campaignName: string;
  setCampaignName: React.Dispatch<React.SetStateAction<string>>;
  campaignId: string;
  setCampaignId: React.Dispatch<React.SetStateAction<string>>;
  productId: string;
  setProductId: React.Dispatch<React.SetStateAction<string>>;
  selectedWorkspaceId: string;
  setSelectedWorkspaceId: React.Dispatch<React.SetStateAction<string>>;
  workspaces: any[];
  campaigns: any[];
  handleExecuteAgentLive: (e: React.FormEvent) => Promise<void>;
}

export default function ExecuteAgentDialog({
  isExecuteOpen,
  setIsExecuteOpen,
  isExecuting,
  objective,
  setObjective,
  campaignName,
  setCampaignName,
  campaignId,
  setCampaignId,
  productId,
  setProductId,
  selectedWorkspaceId,
  setSelectedWorkspaceId,
  workspaces,
  campaigns,
  handleExecuteAgentLive
}: ExecuteAgentDialogProps) {
  if (!isExecuteOpen) return null;

  const handleCampaignChange = (campaignIdVal: string) => {
    const selectedCamp = campaigns.find(c => c.id === campaignIdVal);
    if (selectedCamp) {
      setCampaignId(selectedCamp.id);
      setCampaignName(selectedCamp.name);
      
      // Auto-set the workspace of this campaign
      setSelectedWorkspaceId(selectedCamp.workspace_id);
      
      // Auto-set the objective based on campaign type
      const typeLower = selectedCamp.campaign_type ? selectedCamp.campaign_type.toLowerCase() : "";
      if (typeLower.includes("awareness")) {
        setObjective("BRAND_AWARENESS");
      } else if (typeLower.includes("conversion") || typeLower.includes("lead")) {
        setObjective("LEAD_GEN");
      }
    } else {
      setCampaignId("");
      setCampaignName("");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/60 backdrop-blur-sm font-sans text-xs">
      <div className="absolute inset-0" onClick={() => !isExecuting && setIsExecuteOpen(false)}></div>
      
      <div className="relative w-full max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl h-full flex flex-col justify-between p-6 animate-slide-in">
        <div className="space-y-6">
          <div className="flex justify-between items-start border-b border-slate-800 pb-4">
            <div className="space-y-1">
              <h3 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                <Zap className="h-4 w-4 text-blue-500 fill-current animate-pulse" /> Execute MAB AI Agent
              </h3>
              <p className="text-xs text-slate-500 font-sans">Trigger the stateless, autonomous Multi-Armed Bandit workflow loop.</p>
            </div>
            <button
              onClick={() => setIsExecuteOpen(false)}
              disabled={isExecuting}
              className="text-slate-500 hover:text-slate-300 disabled:opacity-50 p-1 hover:bg-slate-800 rounded cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <form onSubmit={handleExecuteAgentLive} className="space-y-4 font-mono text-xs">
            <div className="space-y-2">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Campaign Objective</label>
              <div className="grid grid-cols-2 gap-3 font-sans">
                <button
                  type="button"
                  onClick={() => setObjective("LEAD_GEN")}
                  disabled={isExecuting}
                  className={`px-3 py-2.5 rounded-lg border text-left flex flex-col gap-1 transition-all cursor-pointer ${
                    objective === "LEAD_GEN"
                      ? "bg-blue-950/30 border-blue-500 text-blue-400 font-semibold"
                      : "border-slate-800 text-slate-400 bg-slate-950/40 hover:bg-slate-800/40"
                  }`}
                >
                  <span className="text-xs">LEAD_GEN</span>
                  <span className="text-[9px] text-slate-500 font-normal leading-normal">Maximize CPA inversions</span>
                </button>
                <button
                  type="button"
                  onClick={() => setObjective("BRAND_AWARENESS")}
                  disabled={isExecuting}
                  className={`px-3 py-2.5 rounded-lg border text-left flex flex-col gap-1 transition-all cursor-pointer ${
                    objective === "BRAND_AWARENESS"
                      ? "bg-cyan-950/30 border-cyan-500 text-cyan-400 font-semibold"
                      : "border-slate-800 text-slate-400 bg-slate-950/40 hover:bg-slate-800/40"
                  }`}
                >
                  <span className="text-xs">BRAND_AWARENESS</span>
                  <span className="text-[9px] text-slate-500 font-normal leading-normal">Maximize CTR and CPM weights</span>
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Workspace Execution Path</label>
              <select
                value={selectedWorkspaceId}
                onChange={(e) => {
                  const newWsId = e.target.value;
                  setSelectedWorkspaceId(newWsId);
                  // Clear selected campaign if it doesn't belong to the new workspace
                  const currentCamp = campaigns.find(c => c.id === campaignId);
                  if (currentCamp && currentCamp.workspace_id !== newWsId) {
                    setCampaignId("");
                    setCampaignName("");
                  }
                }}
                disabled={isExecuting}
                className="w-full bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-slate-200 outline-none transition-all font-mono cursor-pointer"
              >
                {workspaces.map(w => (
                  <option key={w.id} value={w.id}>
                    {w.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Select Marketing Campaign</label>
              <select
                value={campaignId}
                onChange={(e) => handleCampaignChange(e.target.value)}
                disabled={isExecuting}
                required
                className="w-full bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-slate-200 outline-none transition-all font-mono cursor-pointer"
              >
                <option value="">-- Choose Campaign --</option>
                {campaigns
                  .filter(c => c.workspace_id === selectedWorkspaceId)
                  .map(c => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
              </select>
            </div>

            {campaignId && (
              <div className="space-y-1.5 p-2.5 bg-slate-950/40 border border-slate-800/80 rounded-lg">
                <div className="flex justify-between">
                  <span className="text-[9px] uppercase font-bold text-slate-500">Selected Campaign ID:</span>
                  <span className="text-[9px] text-blue-400 font-bold font-mono">{campaignId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[9px] uppercase font-bold text-slate-500">Campaign Name:</span>
                  <span className="text-[9px] text-slate-350 font-mono">{campaignName}</span>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Product Mapping Reference</label>
              <select
                value={productId}
                onChange={(e) => setProductId(e.target.value)}
                disabled={isExecuting}
                className="w-full bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-slate-200 outline-none transition-all font-mono cursor-pointer"
              >
                <option value="prod_topvnsport_shoe_88">TOPVNSPORT Badminton Racket Elite (Yonex Astrox 88 Play)</option>
                <option value="prod_topvnsport_apparel_02">TOPVNSPORT Breathable Jersey v2 (Official Teamwear)</option>
                <option value="prod_generic_other">General MAB Experiment Sandbox</option>
              </select>
            </div>
            
            <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg font-sans text-xs text-slate-400 space-y-1.5 leading-normal">
              <span className="font-semibold text-slate-300 font-mono text-[10px]">Execution Directives:</span>
              <ul className="list-disc pl-4 space-y-1 text-[11px]">
                <li>Initializes scoring pipeline completely stateless.</li>
                <li>Fetches PostgreSQL average baselines for cold start if required.</li>
                <li>Commits transactional atomic edits with immediate rollback fallback.</li>
              </ul>
            </div>

            <button
              type="submit"
              disabled={isExecuting}
              className="w-full py-2.5 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold uppercase tracking-widest rounded-lg flex items-center justify-center gap-2 border border-blue-500/25 transition-all duration-200 shadow-lg shadow-blue-500/10 font-mono cursor-pointer"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-yellow-300" />
                  <span>Executing Pipeline...</span>
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4 text-yellow-300 fill-current animate-bounce" />
                  <span>Trigger Autonomous Flow</span>
                </>
              )}
            </button>
          </form>
        </div>

        <div className="border-t border-slate-800 pt-4 flex items-center justify-between text-[10px] text-slate-500 font-mono">
          <span>MAB ENGINE V3.0</span>
          <span>PORT: 8000</span>
        </div>
      </div>
    </div>
  );
}
