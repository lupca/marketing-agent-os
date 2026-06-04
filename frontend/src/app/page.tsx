"use client";

import React, { useState, useEffect, useRef } from "react";
import BiDashboard from "@/components/BiDashboard";
import KnowledgeBase from "@/components/KnowledgeBase";
import ScriptVault from "@/components/ScriptVault";
import EngineTelemetry from "@/components/EngineTelemetry";
import ErrorManagement from "@/components/ErrorManagement";
import Configuration from "@/components/Configuration";
import ExecuteAgentDialog from "@/components/ExecuteAgentDialog";
import { ToastProvider, useToast } from "@/components/ui/Toast";
import Link from "next/link";
import AuthGuard from "@/components/AuthGuard";
import {
  LayoutDashboard,
  Play,
  AlertTriangle,
  FileText,
  Terminal,
  Settings,
  Zap,
  BookOpen,
  Cpu,
  PanelLeftClose,
  PanelLeftOpen,
  ArrowRight,
  Sliders,
  Radio
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function Dashboard() {
  return (
    <AuthGuard>
      <ToastProvider>
        <DashboardContent />
      </ToastProvider>
    </AuthGuard>
  );
}

function DashboardContent() {
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState("dashboard");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  
  // Execution dialog states
  const [isExecuteOpen, setIsExecuteOpen] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [objective, setObjective] = useState("LEAD_GEN");
  const [campaignName, setCampaignName] = useState("TOPVNSPORT Autumn Campaign");
  const [campaignId, setCampaignId] = useState("ab510edb-0d33-4c94-b554-633481fee8d4");
  const [productId, setProductId] = useState("prod_topvnsport_shoe_88");
  
  // Live output variables from DB
  const [generatedVariants, setGeneratedVariants] = useState<any[]>([]);
  const [sandboxFeedbacks, setSandboxFeedbacks] = useState<any[]>([]);

  // Telemetry fluctuation states
  const [indexingSpeed, setIndexingSpeed] = useState(45);
  const [mutationRate, setMutationRate] = useState(3.2);
  const [quotaUsed, setQuotaUsed] = useState(78);

  // Live WebSocket Telemetry state
  const [logs, setLogs] = useState<any[]>([
    { time: "System", tag: "INFO", src: "init", msg: "Telemetry channel ready. Waiting for backend connection..." }
  ]);

  // Workspaces and Campaigns states
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");

  // Tab: Deadlock State Shared with ErrorManagement
  const [isLockReleased, setIsLockReleased] = useState(false);

  // WebSocket Telemetry Connection
  useEffect(() => {
    // Derive WebSocket URL from API_BASE dynamically
    const wsBase = API_BASE.startsWith("http")
      ? API_BASE.replace(/^http/, "ws")
      : "ws://127.0.0.1:8000";
    
    let ws: WebSocket;
    try {
      ws = new WebSocket(`${wsBase}/api/ws/telemetry`);
      
      ws.onopen = () => {
        console.log("Telemetry WebSocket connected.");
        setLogs(prev => [
          ...prev,
          { time: new Date().toLocaleTimeString(), tag: "SUCCESS", src: "ws", msg: "Real-time Telemetry channel synchronized with FastAPI server." }
        ]);
      };

      ws.onmessage = (event) => {
        const rawLog = event.data;
        const parts = rawLog.split(" - ");
        if (parts.length >= 4) {
          const timePart = parts[0].split(" ")[1]?.split(",")[0] || parts[0];
          const srcPart = parts[1];
          const tagPart = parts[2];
          const msgPart = parts.slice(3).join(" - ");

          setLogs(prev => [
            ...prev,
            { time: timePart, tag: tagPart, src: srcPart, msg: msgPart }
          ]);
        } else {
          setLogs(prev => [
            ...prev,
            { time: new Date().toLocaleTimeString(), tag: "INFO", src: "telemetry", msg: rawLog }
          ]);
        }
      };

      ws.onerror = (error) => {
        // Silently log websocket status to console log state in UI instead of console.error to prevent Turbopack overlays
        setLogs(prev => [
          ...prev,
          { time: new Date().toLocaleTimeString(), tag: "WARN", src: "ws", msg: "Không thể kết nối đến kênh Telemetry thời gian thực." }
        ]);
      };

      ws.onclose = () => {
        console.log("Telemetry WebSocket disconnected. Retrying connection...");
        setLogs(prev => [
          ...prev,
          { time: new Date().toLocaleTimeString(), tag: "WARN", src: "ws", msg: "WebSocket closed. Auto-reconnect in progress..." }
        ]);
      };
    } catch (e) {
      console.warn("WebSocket init error:", e);
    }

    return () => {
      if (ws) ws.close();
    };
  }, []);

  // Fetch workspaces and campaigns list
  useEffect(() => {
    const fetchWorkspacesAndCampaigns = async () => {
      try {
        const wsRes = await fetch(`${API_BASE}/api/workspace/list`);
        const wsData = await wsRes.json();
        if (wsData.status === "success" && wsData.data && wsData.data.length > 0) {
          setWorkspaces(wsData.data);
          const teamAlpha = wsData.data.find((w: any) => w.name === "Team Alpha Workspace");
          setSelectedWorkspaceId(teamAlpha ? teamAlpha.id : wsData.data[0].id);
        }
        const campRes = await fetch(`${API_BASE}/api/workspace/campaigns`);
        const campData = await campRes.json();
        if (campData.status === "success") {
          setCampaigns(campData.data || []);
        }
      } catch (err) {
        console.error("Failed to load workspaces or campaigns:", err);
      }
    };
    fetchWorkspacesAndCampaigns();
  }, []);

  // Telemetry fluctuation intervals
  useEffect(() => {
    const interval = setInterval(() => {
      setIndexingSpeed(prev => Math.max(38, Math.min(52, +(prev + (Math.random() - 0.5) * 2).toFixed(1))));
      setMutationRate(prev => Math.max(1.5, Math.min(6.5, +(prev + (Math.random() - 0.5) * 0.4).toFixed(2))));
      setQuotaUsed(prev => Math.max(75, Math.min(84, +(prev + (Math.random() - 0.5) * 0.5).toFixed(1))));
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleExecuteAgentLive = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsExecuting(true);
    showToast("Starting live MAB pipeline invocation...", "info");

    try {
      const response = await fetch(`${API_BASE}/api/test/trigger-autonomous/${campaignId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status} - Pipeline execution failed.`);
      }

      const finalState = await response.json();
      
      if (finalState && finalState.sop_stage === "completed") {
        setGeneratedVariants(finalState.generated_variants || []);
        setSandboxFeedbacks(finalState.sandbox_feedbacks || []);
        setIsExecuting(false);
        setIsExecuteOpen(false);
        showToast(`Stateless execution successfully finished for '${campaignName}'!`, "success");
      } else {
        throw new Error(finalState?.detail || "Execution interrupted before completion.");
      }
    } catch (error: any) {
      setIsExecuting(false);
      showToast("MAB Pipeline Error: " + error.message, "error");
    }
  };

  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-100 overflow-hidden font-sans">
      
      {/* Sidebar Navigation */}
      <aside className={`border-r border-slate-900 bg-slate-900/40 backdrop-blur-md flex flex-col transition-all duration-300 ${isSidebarOpen ? "w-64" : "w-16"}`}>
        <div className="p-4 border-b border-slate-900 flex items-center justify-between">
          {isSidebarOpen ? (
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-500/25">
                <Zap className="h-4 w-4 text-white animate-pulse" />
              </div>
              <span className="font-semibold text-xs tracking-widest uppercase bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent font-mono">
                MAB ENGINE
              </span>
            </div>
          ) : (
            <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center mx-auto shadow-lg shadow-blue-500/25">
              <Zap className="h-4 w-4 text-white" />
            </div>
          )}
          {isSidebarOpen && (
            <button onClick={() => setIsSidebarOpen(false)} className="text-slate-500 hover:text-slate-200 cursor-pointer">
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
        </div>

        {isSidebarOpen && (
          <div className="px-4 py-3 border-b border-slate-900 space-y-1 bg-slate-950/20">
            <span className="text-[9px] uppercase font-bold tracking-widest text-slate-500 block">Workspace</span>
            <select
              value={selectedWorkspaceId}
              onChange={(e) => setSelectedWorkspaceId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded px-2.5 py-1.5 text-xs text-slate-200 outline-none transition-all font-mono cursor-pointer"
            >
              {workspaces.map(w => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <nav className="flex-1 p-2 space-y-1">
          {[
            { id: "dashboard", label: "Engine Telemetry", icon: Cpu },
            { id: "bi-dashboard", label: "CMO BI Dashboard", icon: LayoutDashboard },
            { id: "knowledge-base", label: "RAG Knowledge Base", icon: BookOpen },
            { id: "vault", label: "Script Vault", icon: FileText },
            { id: "errors", label: "Error Management", icon: AlertTriangle, badge: "EDGE CASES" },
            { id: "config", label: "Configuration", icon: Settings },
            { id: "cockpit", label: "Autopilot Cockpit", icon: Radio, path: "/cockpit" },
          ].map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            if (item.path) {
              return (
                <Link
                  key={item.id}
                  href={item.path}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all group relative cursor-pointer text-slate-400 hover:text-slate-200 hover:bg-slate-800/30 border border-transparent"
                >
                  <Icon className="h-4 w-4 shrink-0 text-slate-500 group-hover:text-slate-200" />
                  {isSidebarOpen && <span className="truncate">{item.label}</span>}
                  {!isSidebarOpen && (
                    <div className="absolute left-14 bg-slate-900 border border-slate-800 text-slate-200 text-[10px] px-2 py-1 rounded shadow-xl opacity-0 group-hover:opacity-100 pointer-events-none transition-all duration-200 whitespace-nowrap z-50">
                      {item.label}
                    </div>
                  )}
                </Link>
              );
            }

            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all group relative cursor-pointer ${
                  isActive
                    ? "bg-blue-950/40 text-blue-400 border border-blue-900/40 shadow-inner"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/30 border border-transparent"
                }`}
              >
                <Icon className={`h-4 w-4 shrink-0 ${isActive ? "text-blue-400" : "text-slate-500 group-hover:text-slate-200"}`} />
                {isSidebarOpen && <span className="truncate">{item.label}</span>}
                {isSidebarOpen && item.badge && (
                  <span className="ml-auto text-[8px] font-bold tracking-widest uppercase bg-rose-500/10 text-rose-450 px-1.5 py-0.5 rounded border border-rose-900/30">
                    {item.badge}
                  </span>
                )}
                {!isSidebarOpen && (
                  <div className="absolute left-14 bg-slate-900 border border-slate-800 text-slate-200 text-[10px] px-2 py-1 rounded shadow-xl opacity-0 group-hover:opacity-100 pointer-events-none transition-all duration-200 whitespace-nowrap z-50">
                    {item.label}
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        {isSidebarOpen && (
          <div className="p-4 border-t border-slate-900 space-y-3">
            <button
              onClick={() => setIsExecuteOpen(true)}
              className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold uppercase tracking-widest text-[10px] py-2.5 rounded-lg border border-blue-500/20 shadow-lg shadow-blue-500/10 flex items-center justify-center gap-1.5 transition-all cursor-pointer"
            >
              <Zap className="h-3.5 w-3.5 fill-current" /> RUN MAB AGENT
            </button>
            
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center">
                <Sliders className="h-4 w-4 text-slate-400" />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-[10px] font-bold text-slate-300 font-mono truncate">CMO Strategic OS</span>
                <span className="text-[9px] text-slate-500 font-mono">Status: AUTONOMOUS</span>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Main Container Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        
        {/* Header Bar */}
        <header className="h-14 border-b border-slate-900 bg-slate-900/10 backdrop-blur-md flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-3">
            {!isSidebarOpen && (
              <button onClick={() => setIsSidebarOpen(true)} className="text-slate-500 hover:text-slate-200 cursor-pointer">
                <PanelLeftOpen className="h-4 w-4" />
              </button>
            )}
            <h1 className="text-xs font-mono font-bold uppercase tracking-widest text-slate-400">
              {activeTab === "dashboard" 
                ? "Engine Telemetry" 
                : activeTab === "bi-dashboard" 
                ? "CMO Strategic BI Dashboard" 
                : activeTab === "knowledge-base" 
                ? "Enterprise RAG Knowledge Library" 
                : activeTab === "vault" 
                ? "Approved Script Vault" 
                : activeTab === "errors" 
                ? "System Immunology Console" 
                : "Configuration Console"}
            </h1>
          </div>

          <div className="flex items-center gap-4 text-[10px] font-mono">
            <div className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-slate-500 uppercase">Agent Loop Active</span>
            </div>
            <span className="text-slate-700">|</span>
            <div className="text-slate-500">
              WORKSPACE: <span className="text-blue-400 font-bold">{workspaces.find(w => w.id === selectedWorkspaceId)?.name || "Default"}</span>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-950/40">
          
          {activeTab === "dashboard" && (
            <EngineTelemetry
              indexingSpeed={indexingSpeed}
              mutationRate={mutationRate}
              quotaUsed={quotaUsed}
              generatedVariants={generatedVariants}
              objective={objective}
              campaignName={campaignName}
              logs={logs}
              setLogs={setLogs}
            />
          )}

          {activeTab === "bi-dashboard" && (
            <BiDashboard />
          )}

          {activeTab === "knowledge-base" && (
            <KnowledgeBase />
          )}

          {activeTab === "vault" && (
            <ScriptVault />
          )}

          {activeTab === "errors" && (
            <ErrorManagement
              mutationRate={mutationRate}
              isLockReleased={isLockReleased}
              setIsLockReleased={setIsLockReleased}
            />
          )}

          {activeTab === "config" && (
            <Configuration
              selectedWorkspaceId={selectedWorkspaceId}
              workspaces={workspaces}
            />
          )}

        </main>
      </div>

      {/* Execute Agent Dialog Slide-Over */}
      <ExecuteAgentDialog
        isExecuteOpen={isExecuteOpen}
        setIsExecuteOpen={setIsExecuteOpen}
        isExecuting={isExecuting}
        objective={objective}
        setObjective={setObjective}
        campaignName={campaignName}
        setCampaignName={setCampaignName}
        campaignId={campaignId}
        setCampaignId={setCampaignId}
        productId={productId}
        setProductId={setProductId}
        selectedWorkspaceId={selectedWorkspaceId}
        setSelectedWorkspaceId={setSelectedWorkspaceId}
        workspaces={workspaces}
        campaigns={campaigns}
        handleExecuteAgentLive={handleExecuteAgentLive}
      />
    </div>
  );
}
