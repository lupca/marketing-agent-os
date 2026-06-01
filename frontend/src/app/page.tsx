"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  LayoutDashboard,
  Play,
  RotateCcw,
  AlertTriangle,
  FileCode2,
  Terminal,
  Settings,
  Zap,
  CheckCircle2,
  AlertCircle,
  Database,
  Cpu,
  Clock,
  Sparkles,
  Sliders,
  ChevronRight,
  Loader2,
  User,
  PanelLeftClose,
  PanelLeftOpen,
  ArrowRight,
  TrendingUp,
  X,
  Gauge,
  Info,
  Search,
  RefreshCw,
  Trash2,
  Code2,
  Flame,
  Binary,
  Layers,
  ChevronDown,
  Eye,
  EyeOff,
  Plus,
  Filter,
  Check
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

interface IntegrationRecord {
  id: string;
  platform_name: string;
  config_key: string;
  config_value: string;
  is_active: boolean;
  created_at?: string;
}

interface AIModelRecord {
  id: string;
  model_id: string;
  name: string;
  provider: string;
  description?: string;
  category: string;
  tags: string[];
  series?: string;
  context_window?: string;
  model_size?: string;
  special_badge?: string;
  api_url?: string;
  api_key?: string;
  is_custom: boolean;
  is_new?: boolean;
}

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  
  // Execution dialog states
  const [isExecuteOpen, setIsExecuteOpen] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [objective, setObjective] = useState("LEAD_GEN");
  const [campaignName, setCampaignName] = useState("TOP VN SPORTS Autumn Campaign");
  const [campaignId, setCampaignId] = useState("ab510edb-0d33-4c94-b554-633481fee8d4");
  const [productId, setProductId] = useState("prod_vn_sport_shoe_88");
  
  // Live output variables from DB
  const [generatedVariants, setGeneratedVariants] = useState<any[]>([]);
  const [sandboxFeedbacks, setSandboxFeedbacks] = useState<any[]>([]);

  // Custom toast notification system
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastType, setToastType] = useState<"success" | "error" | "info">("success");

  // Telemetry fluctuation states
  const [indexingSpeed, setIndexingSpeed] = useState(45);
  const [mutationRate, setMutationRate] = useState(3.2);
  const [quotaUsed, setQuotaUsed] = useState(78);

  // Live WebSocket Telemetry state
  const [logs, setLogs] = useState<any[]>([
    { time: "System", tag: "INFO", src: "init", msg: "Telemetry channel ready. Waiting for backend connection..." }
  ]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Phase 2: Error Management tab state
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
  const [expectedSchema, setExpectedSchema] = useState(`{
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

  // Tab 4: Concurrency and Race Lock states
  const [isLockReleased, setIsLockReleased] = useState(false);

  // Configuration management states (MIGRATED LEGACY CODE)
  const [configSubTab, setConfigSubTab] = useState("integrations");
  const [integrations, setIntegrations] = useState<IntegrationRecord[]>([]);
  const [visibleKeyIds, setVisibleKeyIds] = useState<Set<string>>(new Set());
  const [editingIntId, setEditingIntId] = useState<string | null>(null);
  
  // Integration Form States
  const [formIntPlatform, setFormIntPlatform] = useState("");
  const [formIntKey, setFormIntKey] = useState("");
  const [formIntValue, setFormIntValue] = useState("");
  const [formIntActive, setFormIntActive] = useState(true);

  // Model Config States
  const [modelsList, setModelsList] = useState<AIModelRecord[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [selectedSeries, setSelectedSeries] = useState<string | null>(null);
  const [modelSearch, setModelSearch] = useState("");
  
  // Global LLM Parameter States
  const [currentAiModel, setCurrentAiModel] = useState("Qwen/Qwen2.5-7B-Instruct");
  const [customModelId, setCustomModelId] = useState("");
  const [temperature, setTemperature] = useState(0.2);
  const [contextLimit, setContextLimit] = useState(14000);
  const [recursionLimit, setRecursionLimit] = useState(5);
  const [rerankerMode, setRerankerMode] = useState("local");
  const [siliconFlowKey, setSiliconFlowKey] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("https://api.siliconflow.com/v1");
  const [enableThinking, setEnableThinking] = useState(false);

  // Model Form Modal States
  const [isModelModalOpen, setIsModelModalOpen] = useState(false);
  const [formModelUuid, setFormModelUuid] = useState("");
  const [formModelName, setFormModelName] = useState("");
  const [formModelId, setFormModelId] = useState("");
  const [formModelProvider, setFormModelProvider] = useState("");
  const [formModelCategory, setFormModelCategory] = useState("Chat");
  const [formModelSeries, setFormModelSeries] = useState("");
  const [formModelContext, setFormModelContext] = useState(">= 128K");
  const [formModelSize, setFormModelSize] = useState("10 ~ 50B");
  const [formModelBadge, setFormModelBadge] = useState("");
  const [formModelTagsText, setFormModelTagsText] = useState("");
  const [formModelApiUrl, setFormModelApiUrl] = useState("");
  const [formModelApiKey, setFormModelApiKey] = useState("");
  const [formModelDescription, setFormModelDescription] = useState("");

  const showToast = (message: string, type: "success" | "error" | "info" = "success") => {
    setToastMessage(message);
    setToastType(type);
    setTimeout(() => {
      setToastMessage(null);
    }, 4500);
  };

  // ──────────────────────────────────────────────────────────
  // WebSocket Telemetry Connection
  // ──────────────────────────────────────────────────────────
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/api/ws/telemetry");
    
    ws.onopen = () => {
      console.log("Telemetry WebSocket connected.");
      setLogs(prev => [
        ...prev,
        { time: new Date().toLocaleTimeString(), tag: "SUCCESS", src: "ws", msg: "Real-time Telemetry channel synchronized with FastAPI server." }
      ]);
    };

    ws.onmessage = (event) => {
      const rawLog = event.data;
      // Parse standard Python format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
      console.error("Telemetry WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("Telemetry WebSocket disconnected. Retrying connection...");
      setLogs(prev => [
        ...prev,
        { time: new Date().toLocaleTimeString(), tag: "WARN", src: "ws", msg: "WebSocket closed. Auto-reconnect in progress..." }
      ]);
    };

    return () => {
      ws.close();
    };
  }, []);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Load configuration items
  useEffect(() => {
    if (activeTab === "config") {
      fetchIntegrations();
      fetchAISettings();
      fetchModelsList();
    }
  }, [activeTab]);

  // Telemetry fluctuation intervals
  useEffect(() => {
    const interval = setInterval(() => {
      setIndexingSpeed(prev => Math.max(38, Math.min(52, +(prev + (Math.random() - 0.5) * 2).toFixed(1))));
      setMutationRate(prev => Math.max(1.5, Math.min(6.5, +(prev + (Math.random() - 0.5) * 0.4).toFixed(2))));
      setQuotaUsed(prev => Math.max(75, Math.min(84, +(prev + (Math.random() - 0.5) * 0.5).toFixed(1))));
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // Backoff countdown timer simulation
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isBackoffActive && backoffCountdown > 0 && activeTab === "errors") {
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
  }, [backoffCountdown, isBackoffActive, activeTab]);

  // ──────────────────────────────────────────────────────────
  // Backend Integrations API calls
  // ──────────────────────────────────────────────────────────
  const fetchIntegrations = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/workspace/integrations");
      const res = await response.json();
      if (res.status === "success") {
        setIntegrations(res.data || []);
      } else {
        showToast("Error loading integrations: " + (res.error || "Unknown"), "error");
      }
    } catch (e: any) {
      showToast("Connection to backend workspace integrations failed.", "error");
    }
  };

  const handleSaveIntegration = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formIntPlatform || !formIntKey || !formIntValue) {
      showToast("Please fill all required integration parameters.", "error");
      return;
    }

    const payload: any = {
      platform_name: formIntPlatform.trim().toLowerCase(),
      config_key: formIntKey.trim().toLowerCase(),
      config_value: formIntValue.trim(),
      is_active: formIntActive
    };
    if (editingIntId) {
      payload.id = editingIntId;
    }

    try {
      const response = await fetch("http://localhost:8000/api/workspace/integrations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const res = await response.json();
      if (res.status === "success") {
        showToast("Third-party integration synchronized successfully.", "success");
        handleCancelEditInt();
        fetchIntegrations();
      } else {
        showToast("Error saving integration: " + res.message, "error");
      }
    } catch (e) {
      showToast("Integration API connection failed.", "error");
    }
  };

  const toggleIntStatus = async (id: string, currentStatus: boolean) => {
    const record = integrations.find(r => r.id === id);
    if (!record) return;

    const payload = {
      id: record.id,
      platform_name: record.platform_name,
      config_key: record.config_key,
      config_value: record.config_value,
      is_active: !currentStatus
    };

    try {
      const response = await fetch("http://localhost:8000/api/workspace/integrations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const res = await response.json();
      if (res.status === "success") {
        showToast("Integration active status updated successfully.", "success");
        fetchIntegrations();
      } else {
        showToast("Failed to toggle status: " + res.message, "error");
      }
    } catch (e) {
      showToast("API connectivity failure.", "error");
    }
  };

  const handleDeleteIntegration = async (id: string) => {
    if (!confirm("Are you sure you want to permanently delete this credential?")) return;

    try {
      const response = await fetch("http://localhost:8000/api/workspace/integrations/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id })
      });
      const res = await response.json();
      if (res.status === "success") {
        showToast("Integration removed successfully.", "success");
        fetchIntegrations();
      } else {
        showToast("Delete failure: " + res.error, "error");
      }
    } catch (e) {
      showToast("API deletion failure.", "error");
    }
  };

  const handleStartEditInt = (id: string) => {
    const record = integrations.find(r => r.id === id);
    if (!record) return;
    setEditingIntId(id);
    setFormIntPlatform(record.platform_name);
    setFormIntKey(record.config_key);
    setFormIntValue(record.config_value);
    setFormIntActive(record.is_active);
  };

  const handleCancelEditInt = () => {
    setEditingIntId(null);
    setFormIntPlatform("");
    setFormIntKey("");
    setFormIntValue("");
    setFormIntActive(true);
  };

  const toggleKeyMask = (id: string) => {
    const updated = new Set(visibleKeyIds);
    if (updated.has(id)) {
      updated.delete(id);
    } else {
      updated.add(id);
    }
    setVisibleKeyIds(updated);
  };

  // ──────────────────────────────────────────────────────────
  // AI Settings & Models API calls
  // ──────────────────────────────────────────────────────────
  const fetchAISettings = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/workspace/settings");
      const settings = await response.json();
      
      if (settings.ai_model) {
        const predefined = [
          "Qwen/Qwen3.6-35B-A3B",
          "Qwen/Qwen3-32B",
          "deepseek-ai/DeepSeek-V3",
          "Qwen/Qwen2.5-7B-Instruct"
        ];
        
        if (predefined.includes(settings.ai_model)) {
          setCurrentAiModel(settings.ai_model);
        } else {
          setCurrentAiModel("custom");
          setCustomModelId(settings.ai_model);
        }
      }
      
      if (settings.temperature !== undefined) setTemperature(settings.temperature);
      if (settings.max_tokens) setContextLimit(settings.max_tokens);
      if (settings.recursion_limit) setRecursionLimit(settings.recursion_limit);
      if (settings.reranker_mode) setRerankerMode(settings.reranker_mode);
      if (settings.siliconflow_api_key) setSiliconFlowKey(settings.siliconflow_api_key);
      if (settings.ai_api_url) setApiBaseUrl(settings.ai_api_url);
      if (settings.enable_thinking !== undefined) setEnableThinking(settings.enable_thinking);
    } catch (e) {
      console.error("Failed to load workspace settings from backend.");
    }
  };

  const handleSaveAISettings = async (showNotification = true) => {
    const modelId = currentAiModel === "custom" ? customModelId.trim() : currentAiModel;
    if (!modelId) {
      showToast("Please supply a valid LLM Model ID.", "error");
      return;
    }

    const payload = {
      ai_model: modelId,
      temperature,
      max_tokens: contextLimit,
      recursion_limit: recursionLimit,
      reranker_mode: rerankerMode,
      siliconflow_api_key: siliconFlowKey,
      ai_api_url: apiBaseUrl.trim(),
      enable_thinking: enableThinking
    };

    try {
      const response = await fetch("http://localhost:8000/api/workspace/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const res = await response.json();
      if (res.status === "success") {
        if (showNotification) {
          showToast("Global System LLM Settings saved to database.", "success");
        }
      } else {
        showToast("Error saving LLM settings: " + res.message, "error");
      }
    } catch (e) {
      showToast("Failed to connect to LLM settings API.", "error");
    }
  };

  const fetchModelsList = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/workspace/models");
      const res = await response.json();
      if (res.status === "success") {
        setModelsList(res.data || []);
      }
    } catch (e) {
      console.error("Failed to load models catalog.");
    }
  };

  const handleActivateModel = async (modelId: string) => {
    const predefined = [
      "Qwen/Qwen3.6-35B-A3B",
      "Qwen/Qwen3-32B",
      "deepseek-ai/DeepSeek-V3",
      "Qwen/Qwen2.5-7B-Instruct"
    ];

    let targetModel = modelId;
    if (predefined.includes(modelId)) {
      setCurrentAiModel(modelId);
    } else {
      setCurrentAiModel("custom");
      setCustomModelId(modelId);
    }

    // Auto load custom overrides if matching custom model
    const m = modelsList.find(item => item.model_id === modelId);
    if (m) {
      if (m.api_url) setApiBaseUrl(m.api_url);
      if (m.api_key) setSiliconFlowKey(m.api_key);
    }

    showToast(`Activating model: ${modelId}...`, "info");
    
    // Automatically save immediately to DB
    const payload = {
      ai_model: modelId,
      temperature,
      max_tokens: contextLimit,
      recursion_limit: recursionLimit,
      reranker_mode: rerankerMode,
      siliconflow_api_key: m?.api_key || siliconFlowKey,
      ai_api_url: m?.api_url || apiBaseUrl,
      enable_thinking: enableThinking
    };

    try {
      const response = await fetch("http://localhost:8000/api/workspace/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const res = await response.json();
      if (res.status === "success") {
        showToast(`Model ${modelId} activated and saved successfully!`, "success");
      }
    } catch (e) {
      showToast("Autosave activation connection failed.", "error");
    }
  };

  const handleOpenNewModelModal = () => {
    setFormModelUuid("");
    setFormModelName("");
    setFormModelId("");
    setFormModelProvider("");
    setFormModelCategory("Chat");
    setFormModelSeries("");
    setFormModelContext(">= 128K");
    setFormModelSize("10 ~ 50B");
    setFormModelBadge("");
    setFormModelTagsText("");
    setFormModelApiUrl("");
    setFormModelApiKey("");
    setFormModelDescription("");
    setIsModelModalOpen(true);
  };

  const handleOpenEditModelModal = (id: string) => {
    const m = modelsList.find(item => item.id === id);
    if (!m) return;
    setFormModelUuid(m.id);
    setFormModelName(m.name);
    setFormModelId(m.model_id);
    setFormModelProvider(m.provider);
    setFormModelCategory(m.category);
    setFormModelSeries(m.series || "");
    setFormModelContext(m.context_window || ">= 128K");
    setFormModelSize(m.model_size || "10 ~ 50B");
    setFormModelBadge(m.special_badge || "");
    setFormModelTagsText(m.tags ? m.tags.join(", ") : "");
    setFormModelApiUrl(m.api_url || "");
    setFormModelApiKey(m.api_key || "");
    setFormModelDescription(m.description || "");
    setIsModelModalOpen(true);
  };

  const handleSaveModelForm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formModelName || !formModelId || !formModelProvider) {
      showToast("Please fill all required custom model attributes.", "error");
      return;
    }

    const tags = formModelTagsText 
      ? formModelTagsText.split(",").map(t => t.trim()).filter(t => t.length > 0)
      : [];

    const payload = {
      name: formModelName.trim(),
      model_id: formModelId.trim(),
      provider: formModelProvider.trim(),
      category: formModelCategory,
      series: formModelSeries.trim() || formModelProvider.trim(),
      context_window: formModelContext,
      model_size: formModelSize,
      special_badge: formModelBadge.trim() || null,
      tags,
      description: formModelDescription.trim(),
      api_url: formModelApiUrl.trim() || null,
      api_key: formModelApiKey.trim() || null
    };

    const targetUrl = formModelUuid 
      ? `http://localhost:8000/api/workspace/models/${formModelUuid}` 
      : "http://localhost:8000/api/workspace/models";
    const targetMethod = formModelUuid ? "PUT" : "POST";

    try {
      const response = await fetch(targetUrl, {
        method: targetMethod,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const res = await response.json();
      if (res.status === "success") {
        showToast("Custom model configuration synced with database successfully.", "success");
        setIsModelModalOpen(false);
        fetchModelsList();
      } else {
        showToast("Error: " + res.error, "error");
      }
    } catch (e) {
      showToast("API models saving failure.", "error");
    }
  };

  const handleDeleteModel = async (id: string) => {
    if (!confirm("Are you sure you want to permanently delete this model from library?")) return;

    try {
      const response = await fetch(`http://localhost:8000/api/workspace/models/${id}`, {
        method: "DELETE"
      });
      const res = await response.json();
      if (res.status === "success") {
        showToast("Model deleted from library.", "success");
        fetchModelsList();
      } else {
        showToast("Delete failed: " + res.error, "error");
      }
    } catch (e) {
      showToast("API models deletion failure.", "error");
    }
  };

  // ──────────────────────────────────────────────────────────
  // Execute MAB Agent API Wiring
  // ──────────────────────────────────────────────────────────
  const handleExecuteAgentLive = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsExecuting(true);
    showToast("Starting live MAB pipeline invocation...", "info");

    try {
      const response = await fetch(`http://localhost:8000/api/test/trigger-autonomous/${campaignId}`, {
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
            <button onClick={() => setIsSidebarOpen(false)} className="text-slate-500 hover:text-slate-200">
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
        </div>

        <nav className="flex-1 p-2 space-y-1">
          {[
            { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
            { id: "tasks", label: "Task Management", icon: Play },
            { id: "errors", label: "Error Management", icon: AlertTriangle, badge: "EDGE CASES" },
            { id: "logs", label: "Log Monitoring", icon: Terminal },
            { id: "config", label: "Configuration", icon: Settings },
          ].map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all group relative ${
                  isActive
                    ? "bg-blue-950/40 text-blue-400 border border-blue-900/40 shadow-inner"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/30 border border-transparent"
                }`}
              >
                <Icon className={`h-4 w-4 shrink-0 ${isActive ? "text-blue-400" : "text-slate-500 group-hover:text-slate-200"}`} />
                {isSidebarOpen && <span className="truncate">{item.label}</span>}
                {isSidebarOpen && item.badge && (
                  <span className="ml-auto text-[8px] font-bold tracking-widest uppercase bg-rose-500/10 text-rose-400 px-1.5 py-0.5 rounded border border-rose-900/30">
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

        <div className="p-3 border-t border-slate-900 flex flex-col gap-2">
          {isSidebarOpen ? (
            <div className="flex items-center gap-3 p-1">
              <div className="h-8 w-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
                <User className="h-4 w-4" />
              </div>
              <div className="flex flex-col overflow-hidden">
                <span className="text-xs font-semibold truncate text-slate-300">Admin Platform</span>
                <span className="text-[9px] text-slate-500 font-mono truncate">v3.0.0-stateless</span>
              </div>
            </div>
          ) : (
            <button onClick={() => setIsSidebarOpen(true)} className="mx-auto text-slate-400 hover:text-slate-200 py-2">
              <PanelLeftOpen className="h-4 w-4" />
            </button>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Sticky Top Navbar */}
        <header className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-md border-b border-slate-900 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-base font-extrabold tracking-widest text-slate-200 uppercase font-mono">
              {activeTab === "dashboard" ? "System Health & Metrics Overview" : activeTab === "errors" ? "Edge Case Hardening Hub" : `${activeTab} Management`}
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-900/30">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Autonomous Engine Active
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <div className="text-[9px] font-mono text-slate-500">MAB ALGORITHM STATE</div>
              <div className="text-xs font-semibold text-slate-300 font-mono">80% EXPLOIT / 20% EXPLORE</div>
            </div>
            
            <button
              onClick={() => setIsExecuteOpen(true)}
              className="relative inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-xs font-bold uppercase tracking-widest rounded-lg shadow-lg shadow-blue-500/15 hover:shadow-blue-500/25 hover:-translate-y-0.5 transition-all duration-200 border border-blue-500/30 font-mono"
            >
              <Zap className="h-3.5 w-3.5 fill-current animate-pulse text-yellow-300" />
              <span>Execute AI Agent</span>
            </button>
          </div>
        </header>

        {/* Dynamic Pages Area */}
        <main className="flex-1 p-6 space-y-6">
          {activeTab === "dashboard" && (
            <>
              {/* TOP KPI GRID */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Metric 1: Vector Indexing Speed */}
                <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 hover:border-slate-800/80 transition-all flex flex-col gap-3 group relative overflow-hidden">
                  <div className="absolute top-0 right-0 h-16 w-16 bg-blue-500/5 blur-2xl group-hover:bg-blue-500/10 transition-all"></div>
                  <div className="flex justify-between items-start">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">Vector Indexing Speed</span>
                    <Database className="h-4 w-4 text-blue-500" />
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-extrabold tracking-tight text-slate-100 font-mono">
                      {indexingSpeed}ms
                    </span>
                    <span className="text-xs font-semibold text-slate-500 font-mono">/ chunk</span>
                  </div>
                  <div className="flex items-center justify-between mt-1 text-[11px] text-slate-400">
                    <div className="flex items-center gap-1 font-mono text-emerald-400">
                      <TrendingUp className="h-3 w-3" />
                      <span>-4.2% (Faster)</span>
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
                <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 hover:border-slate-800/80 transition-all flex flex-col gap-3 group relative overflow-hidden">
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
                <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 hover:border-slate-800/80 transition-all flex flex-col gap-3 group relative overflow-hidden">
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
              <div className="bg-slate-900/25 border border-slate-900 rounded-xl p-5 space-y-4">
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
                <div className="bg-slate-900/25 border border-emerald-500/20 rounded-xl p-5 space-y-4">
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
                      <div key={i} className="bg-slate-950/60 border border-slate-900 rounded-lg p-4 space-y-3 font-mono">
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
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
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
                      { node: "creative_generation_node", desc: "Asset extraction & LLM copies writing", state: "COMPLETED", duration: "1150ms", logs: "Successfully loaded TOP VN SPORTS identity metrics." },
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
                    <div ref={logsEndRef} />
                  </div>
                </div>

              </div>
            </>
          )}

          {activeTab === "errors" && (
            <div className="space-y-6">
              <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="space-y-1">
                  <h2 className="text-sm font-extrabold uppercase tracking-widest font-mono text-slate-300 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-rose-500 fill-rose-500/10" /> Autonomous Agent Edge Case Troubleshooting
                  </h2>
                  <p className="text-xs text-slate-400">Deep-observability dashboard for handling cold-starts, LLM hallucinations, rate-limits, and lock race conditions.</p>
                </div>
                <span className="text-[10px] font-mono bg-rose-950/20 text-rose-400 px-3 py-1 rounded-full border border-rose-900/30 shrink-0 font-bold">
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
                      className={`flex items-center gap-2 px-4 py-3 border-b-2 font-bold tracking-widest transition-all ${
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
                                <td className="p-3 text-rose-400 text-[10px] font-bold">
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
                        <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider text-rose-400">
                          <span>Raw Hallucinated LLM Output</span>
                          <span className="bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded border border-rose-900/25">DIRTY STATE</span>
                        </div>
                        <textarea
                          value={rawLlmOutput}
                          onChange={(e) => setRawLlmOutput(e.target.value)}
                          className="w-full h-56 bg-slate-950 border border-slate-900 rounded-lg p-3 outline-none text-rose-300 font-mono text-[11px] leading-relaxed focus:border-rose-900"
                        />
                      </div>

                      {/* Right Block: Expected Compliant output */}
                      <div className="flex flex-col gap-2">
                        <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider text-emerald-400">
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
                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 text-white text-xs font-bold uppercase tracking-widest rounded-lg shadow-md border border-blue-500/30 hover:-translate-y-0.5 transition-all font-mono"
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
                                  : "border-amber-950/30 text-amber-400 bg-amber-950/5 animate-pulse"
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
                      <div className="bg-slate-950/40 border border-slate-900 rounded-xl p-5 flex flex-col justify-between items-center gap-4 text-center">
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
                            className="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold uppercase tracking-wider rounded text-[10px] border border-slate-700 font-mono"
                          >
                            Force Retry
                          </button>
                          <button
                            onClick={() => {
                              setIsBackoffActive(false);
                              showToast("Retry thread terminated by developer", "error");
                            }}
                            className="flex-1 py-1.5 bg-rose-950/20 text-rose-400 hover:bg-rose-950/40 font-bold uppercase tracking-wider rounded text-[10px] border border-rose-900/30 font-mono"
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
                      <span className="text-[10px] font-mono bg-rose-950/20 text-rose-400 border border-rose-900/30 px-2 py-0.5 rounded">
                        CONCURRENCY COLLISION
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 leading-relaxed font-sans max-w-3xl">
                      In highly active parallel executions, threads trying to resolve `PlatformVariant` inserts and write mapped `AdMapper` relations can experience database deadlocks. 
                      Our single atomic transaction blocks automatically capture locks, rolling back cleanly on failures to avoid orphan records.
                    </p>

                    <div className="space-y-4 font-mono text-xs">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Database Concurrency Collision Timeline</div>

                      <div className="bg-slate-950 border border-slate-900 rounded-lg p-5 space-y-4">
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
                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-rose-600 to-rose-700 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-500 disabled:border-slate-800 text-white text-xs font-bold uppercase tracking-widest rounded-lg shadow-md border border-rose-500/30 hover:-translate-y-0.5 transition-all font-mono"
                      >
                        {isLockReleased ? "✓ Deadlock Released & Rolled Back" : "Release Lock & Trigger Rollback"}
                      </button>
                    </div>
                  </div>
                )}

              </div>
            </div>
          )}

          {activeTab === "config" && (
            <div className="space-y-6">
              {/* SUB-TAB TOGGLES (Integrations vs System Models) */}
              <div className="flex border-b border-slate-900 gap-2 font-mono text-xs uppercase overflow-x-auto whitespace-nowrap">
                <button
                  onClick={() => setConfigSubTab("integrations")}
                  className={`flex items-center gap-2 px-4 py-3 border-b-2 font-bold tracking-widest transition-all ${
                    configSubTab === "integrations"
                      ? "border-blue-500 text-blue-400 bg-slate-900/10"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <span>🔌 Workspace Integrations</span>
                </button>
                <button
                  onClick={() => setConfigSubTab("models")}
                  className={`flex items-center gap-2 px-4 py-3 border-b-2 font-bold tracking-widest transition-all ${
                    configSubTab === "models"
                      ? "border-blue-500 text-blue-400 bg-slate-900/10"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <span>🤖 Models & LLM Parameters</span>
                </button>
              </div>

              {/* CONFIG VIEW ISOLATOR */}
              {configSubTab === "integrations" ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  
                  {/* Left: Active Integration List */}
                  <div className="lg:col-span-2 space-y-4">
                    <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-slate-300">
                      🔑 Active Credentials Registry
                    </h3>
                    
                    {integrations.length === 0 ? (
                      <div className="bg-slate-900/10 border border-slate-900 rounded-xl p-12 text-center text-slate-500">
                        <Database className="h-10 w-10 mx-auto text-slate-700 mb-3" />
                        <p className="text-xs font-mono">No third-party integrations loaded. Register one in the panel.</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {integrations.map((int) => {
                          const isMasked = !visibleKeyIds.has(int.id);
                          return (
                            <div key={int.id} className="bg-slate-900/35 border border-slate-900 rounded-xl p-4 flex justify-between items-center gap-4 hover:border-slate-800/80 transition-all font-mono text-xs">
                              <div className="flex flex-col gap-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="text-indigo-400 font-bold uppercase">{int.platform_name}</span>
                                  <span className="text-slate-700">/</span>
                                  <span className="text-slate-300 font-semibold">{int.config_key}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-[11px] text-slate-500 truncate max-w-[200px] sm:max-w-sm">
                                    {isMasked ? "••••••••••••••••" : int.config_value}
                                  </span>
                                  <button onClick={() => toggleKeyMask(int.id)} className="text-slate-500 hover:text-slate-300">
                                    {isMasked ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
                                  </button>
                                </div>
                              </div>
                              
                              <div className="flex items-center gap-3 shrink-0">
                                <button
                                  onClick={() => toggleIntStatus(int.id, int.is_active)}
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                    int.is_active
                                      ? "bg-emerald-500/15 text-emerald-400 border border-emerald-900/30"
                                      : "bg-slate-800 text-slate-500 border border-slate-700"
                                  }`}
                                >
                                  {int.is_active ? "Active" : "Inactive"}
                                </button>
                                
                                <button onClick={() => handleStartEditInt(int.id)} className="text-slate-400 hover:text-slate-200">
                                  ✏️
                                </button>
                                <button onClick={() => handleDeleteIntegration(int.id)} className="text-slate-500 hover:text-rose-400">
                                  ❌
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Right: Add / Update Credentials form */}
                  <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 h-fit space-y-4">
                    <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-indigo-400">
                      {editingIntId ? "✏️ Edit Integration Record" : "📝 Register Integration API"}
                    </h3>

                    <form onSubmit={handleSaveIntegration} className="space-y-4 font-mono text-xs">
                      
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Platform Name</label>
                        <input
                          type="text"
                          required
                          placeholder="E.g. serpapi, slack, openai..."
                          value={formIntPlatform}
                          onChange={(e) => setFormIntPlatform(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded px-3 py-2 text-slate-200 outline-none"
                        />
                        <div className="flex gap-1.5 pt-1 overflow-x-auto whitespace-nowrap">
                          {["upload-post", "serpapi", "slack", "openai"].map((s) => (
                            <button
                              key={s}
                              type="button"
                              onClick={() => setFormIntPlatform(s)}
                              className="text-[9px] bg-slate-950 text-slate-500 hover:text-slate-300 border border-slate-800 px-1.5 py-0.5 rounded"
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Config Key</label>
                        <input
                          type="text"
                          required
                          placeholder="E.g. api_key, webhook_url..."
                          value={formIntKey}
                          onChange={(e) => setFormIntKey(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded px-3 py-2 text-slate-200 outline-none"
                        />
                        <div className="flex gap-1.5 pt-1 overflow-x-auto whitespace-nowrap">
                          {["api_key", "token", "webhook_url"].map((s) => (
                            <button
                              key={s}
                              type="button"
                              onClick={() => setFormIntKey(s)}
                              className="text-[9px] bg-slate-950 text-slate-500 hover:text-slate-300 border border-slate-800 px-1.5 py-0.5 rounded"
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Config Value</label>
                        <input
                          type="password"
                          required
                          placeholder="Paste API credential value..."
                          value={formIntValue}
                          onChange={(e) => setFormIntValue(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded px-3 py-2 text-slate-200 outline-none"
                        />
                      </div>

                      <div className="flex items-center gap-2 pt-2">
                        <input
                          type="checkbox"
                          id="active-check"
                          checked={formIntActive}
                          onChange={(e) => setFormIntActive(e.target.checked)}
                          className="w-4 h-4 accent-indigo-500"
                        />
                        <label htmlFor="active-check" className="text-[11px] text-slate-300 cursor-pointer">Active State Status</label>
                      </div>

                      <div className="flex gap-2 pt-2">
                        <button
                          type="submit"
                          className="flex-1 py-2 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-bold uppercase tracking-wider rounded border border-indigo-500/30"
                        >
                          💾 Save Credential
                        </button>
                        {editingIntId && (
                          <button
                            type="button"
                            onClick={handleCancelEditInt}
                            className="px-3 bg-slate-900 border border-slate-800 text-slate-400 rounded hover:text-slate-200"
                          >
                            Cancel
                          </button>
                        )}
                      </div>

                    </form>
                  </div>

                </div>
              ) : (
                <div className="space-y-6">
                  
                  {/* wide LLM Model Configurations Toolbar */}
                  <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
                    
                    {/* Left: Filters Sidebar */}
                    <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 space-y-4 h-fit">
                      <div className="flex justify-between items-center border-b border-slate-900 pb-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">Catalog Filter Matrix</span>
                        <Filter className="h-3.5 w-3.5 text-slate-500" />
                      </div>

                      <div className="space-y-3 font-mono text-xs">
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-500 block">Category</span>
                          <div className="flex flex-wrap gap-1.5">
                            {["Chat", "Image", "Video", "Embedding", "Reranker"].map(c => (
                              <button
                                key={c}
                                onClick={() => setSelectedCategory(prev => prev === c ? null : c)}
                                className={`px-2 py-0.5 rounded text-[10px] border ${
                                  selectedCategory === c
                                    ? "bg-blue-500/20 border-blue-500 text-blue-400 font-bold"
                                    : "border-slate-800 text-slate-400 hover:border-slate-700"
                                }`}
                              >
                                {c}
                              </button>
                            ))}
                          </div>
                        </div>

                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-500 block">Tags</span>
                          <div className="flex flex-wrap gap-1.5">
                            {["VLM", "MoE", "Reasoning", "Tools", "Coder"].map(t => (
                              <button
                                key={t}
                                onClick={() => setSelectedTag(prev => prev === t ? null : t)}
                                className={`px-2 py-0.5 rounded text-[10px] border ${
                                  selectedTag === t
                                    ? "bg-purple-500/20 border-purple-500 text-purple-400 font-bold"
                                    : "border-slate-800 text-slate-400 hover:border-slate-700"
                                }`}
                              >
                                {t}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Middle: spacious Models grid catalog */}
                    <div className="xl:col-span-2 space-y-4">
                      <div className="flex justify-between items-center">
                        <div className="relative w-full max-w-sm">
                          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                          <input
                            type="text"
                            placeholder="Filter model catalogs..."
                            value={modelSearch}
                            onChange={(e) => setModelSearch(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs font-mono text-slate-200 outline-none focus:border-slate-700"
                          />
                        </div>

                        <button
                          onClick={handleOpenNewModelModal}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold uppercase tracking-wider rounded-lg flex items-center gap-1 font-mono border border-blue-500/25 shrink-0"
                        >
                          <Plus className="h-3.5 w-3.5" /> Add Custom Model
                        </button>
                      </div>

                      {/* Dynamic grid container */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {modelsList
                          .filter(m => {
                            if (modelSearch && !m.name.toLowerCase().includes(modelSearch.toLowerCase()) && !m.model_id.toLowerCase().includes(modelSearch.toLowerCase())) return false;
                            if (selectedCategory && m.category !== selectedCategory) return false;
                            if (selectedTag && !m.tags.includes(selectedTag)) return false;
                            return true;
                          })
                          .map((m) => {
                            const isActivated = currentAiModel === m.model_id || (currentAiModel === "custom" && customModelId === m.model_id);
                            return (
                              <div key={m.id} className={`bg-slate-900/35 border rounded-xl p-4 flex flex-col justify-between gap-3 hover:border-slate-800/80 transition-all ${
                                isActivated ? "border-blue-500/60 shadow-[0_0_20px_rgba(59,130,246,0.1)]" : "border-slate-900"
                              }`}>
                                <div className="space-y-2">
                                  <div className="flex justify-between items-start gap-2">
                                    <h4 className="font-extrabold text-xs font-mono truncate text-slate-200" title={m.name}>{m.name}</h4>
                                    {isActivated ? (
                                      <span className="text-[8px] font-mono font-bold bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-900/30 shrink-0 uppercase tracking-widest">Activated</span>
                                    ) : (
                                      <button
                                        onClick={() => handleActivateModel(m.model_id)}
                                        className="text-[8px] font-mono font-bold bg-slate-800 text-slate-400 hover:text-slate-200 px-1.5 py-0.5 rounded border border-slate-700 shrink-0 uppercase tracking-widest"
                                      >
                                        Activate
                                      </button>
                                    )}
                                  </div>
                                  <p className="text-[11px] text-slate-400 leading-normal line-clamp-2 font-sans">{m.description || "No model description available."}</p>
                                </div>

                                <div className="space-y-2">
                                  <div className="flex flex-wrap gap-1">
                                    {m.tags.map(t => (
                                      <span key={t} className="bg-slate-950 text-slate-500 border border-slate-900 px-1.5 py-0.2 rounded text-[8px] font-mono">{t}</span>
                                    ))}
                                  </div>
                                  
                                  <div className="flex justify-between items-center pt-2 border-t border-slate-950/60 text-[9px] font-mono text-slate-500">
                                    <span>{m.provider}</span>
                                    <div className="flex gap-2">
                                      <button onClick={() => handleOpenEditModelModal(m.id)} className="hover:text-slate-300">Edit</button>
                                      <button onClick={() => handleDeleteModel(m.id)} className="hover:text-rose-400">Delete</button>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    </div>

                    {/* Right Panel: Compact Parameters config */}
                    <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 space-y-4 h-fit">
                      <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-indigo-400 border-b border-slate-900 pb-2">
                        ⚙️ System Parameters
                      </h3>

                      <div className="space-y-4 font-mono text-xs">
                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">🧠 active model select</label>
                          <select
                            value={currentAiModel}
                            onChange={(e) => {
                              setCurrentAiModel(e.target.value);
                              if (e.target.value !== "custom") handleActivateModel(e.target.value);
                            }}
                            className="w-full bg-slate-950 border border-slate-800 px-3 py-2 text-slate-200 outline-none rounded"
                          >
                            <option value="Qwen/Qwen3.6-35B-A3B">Qwen 3.6 - 35B</option>
                            <option value="Qwen/Qwen3-32B">Qwen 3 - 32B</option>
                            <option value="deepseek-ai/DeepSeek-V3">DeepSeek V3</option>
                            <option value="Qwen/Qwen2.5-7B-Instruct">Qwen 2.5 - 7B (Local)</option>
                            <option value="custom">Custom model override...</option>
                          </select>
                          {currentAiModel === "custom" && (
                            <input
                              type="text"
                              placeholder="E.g. deepseek-reasoner..."
                              value={customModelId}
                              onChange={(e) => setCustomModelId(e.target.value)}
                              className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded px-3 py-2 text-slate-200 outline-none mt-2"
                            />
                          )}
                        </div>

                        <div className="space-y-1">
                          <div className="flex justify-between items-center text-[10px]">
                            <span className="font-bold uppercase tracking-wider text-slate-400">🎨 Temperature</span>
                            <span className="text-indigo-400 font-bold">{temperature.toFixed(2)}</span>
                          </div>
                          <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.05"
                            value={temperature}
                            onChange={(e) => setTemperature(parseFloat(e.target.value))}
                            className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer"
                          />
                        </div>

                        <div className="space-y-1">
                          <div className="flex justify-between items-center text-[10px]">
                            <span className="font-bold uppercase tracking-wider text-slate-400">📏 Context window</span>
                            <span className="text-indigo-400 font-bold">{contextLimit.toLocaleString()}</span>
                          </div>
                          <input
                            type="range"
                            min="4000"
                            max="20000"
                            step="1000"
                            value={contextLimit}
                            onChange={(e) => setContextLimit(parseInt(e.target.value))}
                            className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer"
                          />
                        </div>

                        <div className="space-y-1">
                          <div className="flex justify-between items-center text-[10px]">
                            <span className="font-bold uppercase tracking-wider text-slate-400">🔄 Loop limit</span>
                            <span className="text-indigo-400 font-bold">{recursionLimit}</span>
                          </div>
                          <input
                            type="range"
                            min="2"
                            max="15"
                            step="1"
                            value={recursionLimit}
                            onChange={(e) => setRecursionLimit(parseInt(e.target.value))}
                            className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">🔍 Reranker layer</label>
                          <select
                            value={rerankerMode}
                            onChange={(e) => setRerankerMode(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 px-3 py-2 text-slate-200 outline-none rounded"
                          >
                            <option value="local">Local GPU (bge-reranker-large)</option>
                            <option value="cloud">Cloud API (SiliconFlow)</option>
                          </select>
                        </div>

                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">🔑 SiliconFlow API Key</label>
                          <input
                            type="password"
                            placeholder="sk-................................"
                            value={siliconFlowKey}
                            onChange={(e) => setSiliconFlowKey(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 px-3 py-2 text-slate-200 outline-none rounded"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">🌐 API base url override</label>
                          <input
                            type="text"
                            placeholder="Https://api.siliconflow.com/v1"
                            value={apiBaseUrl}
                            onChange={(e) => setApiBaseUrl(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 px-3 py-2 text-slate-200 outline-none rounded"
                          />
                        </div>

                        <div className="flex items-center gap-2 pt-2">
                          <input
                            type="checkbox"
                            id="thinking-check"
                            checked={enableThinking}
                            onChange={(e) => setEnableThinking(e.target.checked)}
                            className="w-4 h-4 accent-indigo-500"
                          />
                          <label htmlFor="thinking-check" className="text-[11px] text-slate-300 cursor-pointer">Enable Thinking Mode</label>
                        </div>

                        <button
                          onClick={() => handleSaveAISettings(true)}
                          className="w-full py-2 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-bold uppercase tracking-wider rounded border border-indigo-500/30 mt-2"
                        >
                          💾 Save parameters
                        </button>
                      </div>

                    </div>

                  </div>

                </div>
              )}

            </div>
          )}

          {(activeTab !== "dashboard" && activeTab !== "errors" && activeTab !== "config") && (
            <div className="bg-slate-900/20 border border-slate-900 rounded-xl p-12 flex flex-col items-center justify-center text-center space-y-4">
              <div className="h-12 w-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 border border-slate-700">
                <Sliders className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <h3 className="font-bold text-slate-200 uppercase tracking-wider text-sm">{activeTab} Section</h3>
                <p className="text-xs text-slate-500 max-w-sm">This module is reserved for mock pipeline viewing. The Dashboard layouts, configurations, and Error Management systems are fully operational.</p>
              </div>
              <button
                onClick={() => setActiveTab("dashboard")}
                className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center gap-1 font-semibold uppercase tracking-wider"
              >
                Return to Dashboard <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </main>
      </div>

      {/* Execute Agent Dialog Slide-Over */}
      {isExecuteOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/60 backdrop-blur-sm">
          <div className="absolute inset-0" onClick={() => !isExecuting && setIsExecuteOpen(false)}></div>
          
          <div className="relative w-full max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl h-full flex flex-col justify-between p-6 animate-slide-in">
            <div className="space-y-6">
              <div className="flex justify-between items-start border-b border-slate-800 pb-4">
                <div className="space-y-1">
                  <h3 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                    <Zap className="h-4 w-4 text-blue-500 fill-current" /> Execute MAB AI Agent
                  </h3>
                  <p className="text-xs text-slate-500">Trigger the stateless, autonomous Multi-Armed Bandit workflow loop.</p>
                </div>
                <button
                  onClick={() => setIsExecuteOpen(false)}
                  disabled={isExecuting}
                  className="text-slate-500 hover:text-slate-300 disabled:opacity-50 p-1 hover:bg-slate-800 rounded"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <form onSubmit={handleExecuteAgentLive} className="space-y-4 text-xs font-mono">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Campaign Objective</label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setObjective("LEAD_GEN")}
                      disabled={isExecuting}
                      className={`px-3 py-2.5 rounded-lg border text-left flex flex-col gap-1 transition-all ${
                        objective === "LEAD_GEN"
                          ? "bg-blue-950/30 border-blue-500 text-blue-400 font-semibold"
                          : "border-slate-800 text-slate-400 bg-slate-950/40 hover:bg-slate-800/40"
                      }`}
                    >
                      <span className="text-xs">LEAD_GEN</span>
                      <span className="text-[9px] text-slate-500 font-normal font-sans">Maximize CPA inversions</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setObjective("BRAND_AWARENESS")}
                      disabled={isExecuting}
                      className={`px-3 py-2.5 rounded-lg border text-left flex flex-col gap-1 transition-all ${
                        objective === "BRAND_AWARENESS"
                          ? "bg-cyan-950/30 border-cyan-500 text-cyan-400 font-semibold"
                          : "border-slate-800 text-slate-400 bg-slate-950/40 hover:bg-slate-800/40"
                      }`}
                    >
                      <span className="text-xs">BRAND_AWARENESS</span>
                      <span className="text-[9px] text-slate-500 font-normal font-sans">Maximize CTR and CPM weights</span>
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Campaign Name Identifier</label>
                  <input
                    type="text"
                    required
                    value={campaignName}
                    onChange={(e) => setCampaignName(e.target.value)}
                    disabled={isExecuting}
                    className="w-full bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-slate-200 outline-none transition-all font-mono"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Campaign UUID</label>
                  <input
                    type="text"
                    required
                    value={campaignId}
                    onChange={(e) => setCampaignId(e.target.value)}
                    disabled={isExecuting}
                    className="w-full bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-slate-200 outline-none transition-all font-mono text-[10px]"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Product Mapping Reference</label>
                  <select
                    value={productId}
                    onChange={(e) => setProductId(e.target.value)}
                    disabled={isExecuting}
                    className="w-full bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-slate-200 outline-none transition-all font-mono"
                  >
                    <option value="prod_vn_sport_shoe_88">ShopVNB Badminton Racket Elite (TOP VN SPORTS)</option>
                    <option value="prod_vnb_apparel_02">ShopVNB Breathable Jersey v2 (TOP VN SPORTS)</option>
                    <option value="prod_generic_other">General MAB Experiment Sandbox</option>
                  </select>
                </div>
                
                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg font-sans text-xs text-slate-400 space-y-1.5">
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
                  className="w-full py-2.5 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold uppercase tracking-widest rounded-lg flex items-center justify-center gap-2 border border-blue-500/25 hover:from-blue-500 hover:to-cyan-500 transition-all duration-200 shadow-lg shadow-blue-500/10 font-mono"
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
      )}

      {/* Model Catalog Register/Edit Modal */}
      {isModelModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-6 space-y-4 font-mono text-xs animate-scale-in">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="font-extrabold text-sm text-indigo-400">
                {formModelUuid ? "✏️ Edit Model Library Entry" : "➕ Register New Custom Model"}
              </h3>
              <button onClick={() => setIsModelModalOpen(false)} className="text-slate-500 hover:text-slate-300">
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleSaveModelForm} className="space-y-3">
              
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Model Name</label>
                  <input
                    type="text"
                    required
                    placeholder="E.g. Qwen 2.5 Local"
                    value={formModelName}
                    onChange={(e) => setFormModelName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                  />
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Model ID Identifier</label>
                  <input
                    type="text"
                    required
                    placeholder="E.g. Qwen/Qwen2.5-7B"
                    value={formModelId}
                    onChange={(e) => setFormModelId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Provider</label>
                  <input
                    type="text"
                    required
                    placeholder="E.g. qwen, ollama, deepseek..."
                    value={formModelProvider}
                    onChange={(e) => setFormModelProvider(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Category</label>
                  <select
                    value={formModelCategory}
                    onChange={(e) => setFormModelCategory(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                  >
                    <option value="Chat">Chat</option>
                    <option value="Image">Image</option>
                    <option value="Video">Video</option>
                    <option value="Embedding">Embedding</option>
                    <option value="Reranker">Reranker</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Series</label>
                  <input
                    type="text"
                    placeholder="E.g. Qwen, Llama"
                    value={formModelSeries}
                    onChange={(e) => setFormModelSeries(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Context Window</label>
                  <select
                    value={formModelContext}
                    onChange={(e) => setFormModelContext(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                  >
                    <option value=">= 8K">&ge; 8K</option>
                    <option value=">= 16K">&ge; 16K</option>
                    <option value=">= 32K">&ge; 32K</option>
                    <option value=">= 128K">&ge; 128K</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Model Size</label>
                  <select
                    value={formModelSize}
                    onChange={(e) => setFormModelSize(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                  >
                    <option value="Under 10B">&lt; 10B</option>
                    <option value="10 ~ 50B">10B ~ 50B</option>
                    <option value="50 ~ 100B">50B ~ 100B</option>
                    <option value="Over 100B">&gt; 100B</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Special Badge</label>
                  <input
                    type="text"
                    placeholder="E.g. NEW, HOT"
                    value={formModelBadge}
                    onChange={(e) => setFormModelBadge(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Tags (Separated by commas)</label>
                <input
                  type="text"
                  placeholder="E.g. Chat, Tools, MoE"
                  value={formModelTagsText}
                  onChange={(e) => setFormModelTagsText(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-slate-400">API URL Override</label>
                  <input
                    type="text"
                    placeholder="E.g. https://api.siliconflow.com/v1"
                    value={formModelApiUrl}
                    onChange={(e) => setFormModelApiUrl(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                  />
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-slate-400">API Key Override</label>
                  <input
                    type="password"
                    placeholder="E.g. sk-................................"
                    value={formModelApiKey}
                    onChange={(e) => setFormModelApiKey(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Description</label>
                <textarea
                  placeholder="Model highlights or purpose..."
                  value={formModelDescription}
                  onChange={(e) => setFormModelDescription(e.target.value)}
                  rows={2}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none resize-none"
                />
              </div>

              <div className="flex gap-3 justify-end pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModelModalOpen(false)}
                  className="px-4 py-2 bg-slate-950 hover:bg-slate-800 text-slate-400 rounded border border-slate-800"
                >
                  Cancel
                </button>
                
                <button
                  type="submit"
                  className="px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold uppercase tracking-wider rounded border border-blue-500/25 shadow-lg"
                >
                  💾 Save Model Configuration
                </button>
              </div>

            </form>
          </div>
        </div>
      )}
    </div>
  );
}
