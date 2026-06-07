"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Database,
  Eye,
  EyeOff,
  Search,
  Plus,
  Filter
} from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { apiFetch } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

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

interface SocialAccountRecord {
  id: string;
  platform: string;
  account_name: string;
  account_id: string;
  app_id?: string;
  app_secret?: string;
  access_token?: string;
  status: string;
  created_at?: string;
}

interface ConfigurationProps {
  selectedWorkspaceId: string;
  workspaces?: unknown[];
}

export default function Configuration({
  selectedWorkspaceId
}: ConfigurationProps) {
  const { showToast } = useToast();
  const [configSubTab, setConfigSubTab] = useState("integrations");

  // Integrations states
  const [integrations, setIntegrations] = useState<IntegrationRecord[]>([]);
  const [visibleKeyIds, setVisibleKeyIds] = useState<Set<string>>(new Set());
  const [editingIntId, setEditingIntId] = useState<string | null>(null);
  
  // Integration Form States
  const [formIntPlatform, setFormIntPlatform] = useState("");
  const [formIntKey, setFormIntKey] = useState("");
  const [formIntValue, setFormIntValue] = useState("");
  const [formIntActive, setFormIntActive] = useState(true);

  // Tab: Social Accounts States
  const [socialAccounts, setSocialAccounts] = useState<SocialAccountRecord[]>([]);
  const [editingSocialId, setEditingSocialId] = useState<string | null>(null);
  
  // Social Account Form States
  const [formSocialPlatform, setFormSocialPlatform] = useState("facebook");
  const [formSocialAccountName, setFormSocialAccountName] = useState("");
  const [formSocialAccountId, setFormSocialAccountId] = useState("");
  const [formSocialAppId, setFormSocialAppId] = useState("");
  const [formSocialAppSecret, setFormSocialAppSecret] = useState("");
  const [formSocialAccessToken, setFormSocialAccessToken] = useState("");
  const [formSocialStatus, setFormSocialStatus] = useState("active");

  // Model Config States
  const [modelsList, setModelsList] = useState<AIModelRecord[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [selectedSeries, setSelectedSeries] = useState<string | null>(null);
  const [selectedModelSize, setSelectedModelSize] = useState<string | null>(null);
  const [selectedContext, setSelectedContext] = useState<string | null>(null);
  const [modelSearch, setModelSearch] = useState("");
  
  // Global LLM Parameter States
  const [currentAiModel, setCurrentAiModel] = useState("Qwen/Qwen2.5-7B-Instruct");
  const [customModelId, setCustomModelId] = useState("");
  const [embedModel, setEmbedModel] = useState("Qwen/Qwen3-Embedding-0.6B");
  const [rerankModel, setRerankModel] = useState("Qwen/Qwen3-Reranker-0.6B");
  const [temperature, setTemperature] = useState(0.2);
  const [contextLimit, setContextLimit] = useState(14000);
  const [recursionLimit, setRecursionLimit] = useState(5);
  const [rerankerMode, setRerankerMode] = useState("cloud");
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

  // API - Integrations
  const fetchIntegrations = useCallback(async () => {
    try {
      const res = await apiFetch<{ status: string; data?: IntegrationRecord[]; error?: string }>(
        `/api/workspace/integrations?workspace_id=${selectedWorkspaceId}`
      );
      if (res.status === "success") {
        setIntegrations(res.data || []);
      } else {
        showToast("Error loading integrations: " + (res.error || "Unknown"), "error");
      }
    } catch (e) {
      console.error(e);
      showToast("Connection to backend workspace integrations failed.", "error");
    }
  }, [selectedWorkspaceId, showToast]);

  // API - Social Accounts
  const fetchSocialAccounts = useCallback(async () => {
    try {
      const res = await apiFetch<{ status: string; data?: SocialAccountRecord[]; error?: string }>(
        `/api/workspace/social-accounts?workspace_id=${selectedWorkspaceId}`
      );
      if (res.status === "success") {
        setSocialAccounts(res.data || []);
      } else {
        showToast("Error loading social accounts: " + (res.error || "Unknown"), "error");
      }
    } catch (e) {
      console.error(e);
      showToast("Connection to backend social accounts failed.", "error");
    }
  }, [selectedWorkspaceId, showToast]);

  // API - AI parameters and models
  const fetchAISettings = useCallback(async () => {
    try {
      const settings = await apiFetch<Record<string, any>>(
        `/api/workspace/settings?workspace_id=${selectedWorkspaceId}`
      );
      
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
      if (settings.embed_model) setEmbedModel(settings.embed_model);
      if (settings.rerank_model) setRerankModel(settings.rerank_model);
      if (settings.siliconflow_api_key) setSiliconFlowKey(settings.siliconflow_api_key);
      if (settings.ai_api_url) setApiBaseUrl(settings.ai_api_url);
      if (settings.enable_thinking !== undefined) setEnableThinking(settings.enable_thinking);
    } catch (e) {
      console.error("Failed to load workspace settings from backend.", e);
    }
  }, [selectedWorkspaceId]);

  const fetchModelsList = useCallback(async () => {
    try {
      const res = await apiFetch<{ status: string; data?: AIModelRecord[] }>(
        `/api/workspace/models?workspace_id=${selectedWorkspaceId}`
      );
      if (res.status === "success") {
        setModelsList(res.data || []);
      }
    } catch (e) {
      console.error("Failed to load models catalog.", e);
    }
  }, [selectedWorkspaceId]);

  // Load configuration details
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchIntegrations();
      fetchSocialAccounts();
      fetchModelsList();
      fetchAISettings();
    }, 0);
    return () => clearTimeout(timer);
  }, [selectedWorkspaceId, fetchAISettings, fetchIntegrations, fetchModelsList, fetchSocialAccounts]);

  const handleSaveIntegration = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formIntPlatform || !formIntKey || !formIntValue) {
      showToast("Please fill all required integration parameters.", "error");
      return;
    }

    const payload: Partial<IntegrationRecord> & { id?: string } = {
      platform_name: formIntPlatform.trim().toLowerCase(),
      config_key: formIntKey.trim().toLowerCase(),
      config_value: formIntValue.trim(),
      is_active: formIntActive
    };
    if (editingIntId) {
      payload.id = editingIntId;
    }

    try {
      const res = await apiFetch<{ status: string; message?: string }>(
        `/api/workspace/integrations?workspace_id=${selectedWorkspaceId}`,
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      );
      if (res.status === "success") {
        showToast("Third-party integration synchronized successfully.", "success");
        handleCancelEditInt();
        fetchIntegrations();
      } else {
        showToast("Error saving integration: " + res.message, "error");
      }
    } catch {
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
      const res = await apiFetch<{ status: string; message?: string }>(
        `/api/workspace/integrations?workspace_id=${selectedWorkspaceId}`,
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      );
      if (res.status === "success") {
        showToast("Integration active status updated successfully.", "success");
        fetchIntegrations();
      } else {
        showToast("Failed to toggle status: " + res.message, "error");
      }
    } catch {
      showToast("API connectivity failure.", "error");
    }
  };

  const handleDeleteIntegration = async (id: string) => {
    if (!confirm("Are you sure you want to permanently delete this credential?")) return;

    try {
      const res = await apiFetch<{ status: string; error?: string }>(
        `/api/workspace/integrations/delete`,
        {
          method: "POST",
          body: JSON.stringify({ id })
        }
      );
      if (res.status === "success") {
        showToast("Integration removed successfully.", "success");
        fetchIntegrations();
      } else {
        showToast("Delete failure: " + res.error, "error");
      }
    } catch {
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

  const handleSaveSocialAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formSocialPlatform || !formSocialAccountName || !formSocialAccountId) {
      showToast("Please fill all required social account parameters.", "error");
      return;
    }

    const payload: Partial<SocialAccountRecord> & { id?: string } = {
      platform: formSocialPlatform.trim().toLowerCase(),
      account_name: formSocialAccountName.trim(),
      account_id: formSocialAccountId.trim(),
      app_id: formSocialAppId.trim(),
      app_secret: formSocialAppSecret.trim(),
      access_token: formSocialAccessToken.trim(),
      status: formSocialStatus
    };
    if (editingSocialId) {
      payload.id = editingSocialId;
    }

    try {
      const res = await apiFetch<{ status: string; message?: string }>(
        `/api/workspace/social-accounts?workspace_id=${selectedWorkspaceId}`,
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      );
      if (res.status === "success") {
        showToast("Social account synchronized successfully.", "success");
        handleCancelEditSocial();
        fetchSocialAccounts();
      } else {
        showToast("Error saving social account: " + res.message, "error");
      }
    } catch {
      showToast("Social account API connection failed.", "error");
    }
  };

  const handleDeleteSocialAccount = async (id: string) => {
    if (!confirm("Are you sure you want to permanently delete this social account credential?")) return;

    try {
      const res = await apiFetch<{ status: string; error?: string }>(
        `/api/workspace/social-accounts/${id}`,
        {
          method: "DELETE"
        }
      );
      if (res.status === "success") {
        showToast("Social account removed successfully.", "success");
        fetchSocialAccounts();
      } else {
        showToast("Delete failure: " + res.error, "error");
      }
    } catch {
      showToast("API deletion failure.", "error");
    }
  };

  const handleStartEditSocial = (id: string) => {
    const record = socialAccounts.find(r => r.id === id);
    if (!record) return;
    setEditingSocialId(id);
    setFormSocialPlatform(record.platform);
    setFormSocialAccountName(record.account_name);
    setFormSocialAccountId(record.account_id);
    setFormSocialAppId(record.app_id || "");
    setFormSocialAppSecret(record.app_secret || "");
    setFormSocialAccessToken(record.access_token || "");
    setFormSocialStatus(record.status);
  };

  const handleCancelEditSocial = () => {
    setEditingSocialId(null);
    setFormSocialPlatform("facebook");
    setFormSocialAccountName("");
    setFormSocialAccountId("");
    setFormSocialAppId("");
    setFormSocialAppSecret("");
    setFormSocialAccessToken("");
    setFormSocialStatus("active");
  };

  // AI parameters and models actions

  const handleSaveAISettings = async (showNotification = true) => {
    const modelId = currentAiModel === "custom" ? customModelId.trim() : currentAiModel;
    if (!modelId) {
      showToast("Please supply a valid LLM Model ID.", "error");
      return;
    }

    const payload = {
      ai_model: modelId,
      embed_model: embedModel,
      rerank_model: rerankModel,
      temperature,
      max_tokens: contextLimit,
      recursion_limit: recursionLimit,
      reranker_mode: rerankerMode,
      siliconflow_api_key: siliconFlowKey,
      ai_api_url: apiBaseUrl.trim(),
      enable_thinking: enableThinking
    };

    try {
      const res = await apiFetch<{ status: string; message?: string }>(
        `/api/workspace/settings?workspace_id=${selectedWorkspaceId}`,
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      );
      if (res.status === "success") {
        if (showNotification) {
          showToast("Global System LLM Settings saved to database.", "success");
        }
      } else {
        showToast("Error saving LLM settings: " + res.message, "error");
      }
    } catch {
      showToast("Failed to connect to LLM settings API.", "error");
    }
  };

  // Models actions

  const handleActivateModel = async (modelId: string, category: string = "Chat") => {
    const m = modelsList.find(item => item.model_id === modelId);
    const cat = m ? m.category : category;
    
    let newAiModel = currentAiModel;
    let newEmbedModel = embedModel;
    let newRerankModel = rerankModel;

    if (cat === "Embedding") {
      setEmbedModel(modelId);
      newEmbedModel = modelId;
    } else if (cat === "Reranker") {
      setRerankModel(modelId);
      newRerankModel = modelId;
    } else {
      const predefined = [
        "Qwen/Qwen3.6-35B-A3B",
        "Qwen/Qwen3-32B",
        "deepseek-ai/DeepSeek-V3",
        "Qwen/Qwen2.5-7B-Instruct"
      ];
      if (predefined.includes(modelId)) {
        setCurrentAiModel(modelId);
        newAiModel = modelId;
      } else {
        setCurrentAiModel("custom");
        setCustomModelId(modelId);
        newAiModel = modelId;
      }
    }

    if (m) {
      if (m.api_url) setApiBaseUrl(m.api_url);
      if (m.api_key) setSiliconFlowKey(m.api_key);
    }

    showToast(`Activating model: ${modelId}...`, "info");
    
    const payload = {
      ai_model: newAiModel,
      embed_model: newEmbedModel,
      rerank_model: newRerankModel,
      temperature,
      max_tokens: contextLimit,
      recursion_limit: recursionLimit,
      reranker_mode: rerankerMode,
      siliconflow_api_key: m?.api_key || siliconFlowKey,
      ai_api_url: m?.api_url || apiBaseUrl,
      enable_thinking: enableThinking
    };

    try {
      const res = await apiFetch<{ status: string }>(
        `/api/workspace/settings?workspace_id=${selectedWorkspaceId}`,
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      );
      if (res.status === "success") {
        showToast(`Model ${modelId} activated and saved successfully!`, "success");
      }
    } catch {
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
      api_url: formModelApiUrl.trim() || null,
      api_key: formModelApiKey.trim() || null,
      description: formModelDescription.trim() || null,
      is_custom: true
    };

    const url = formModelUuid 
      ? `/api/workspace/models/${formModelUuid}`
      : `/api/workspace/models?workspace_id=${selectedWorkspaceId}`;

    try {
      const res = await apiFetch<{ status: string; error?: string }>(
        url,
        {
          method: formModelUuid ? "PUT" : "POST",
          body: JSON.stringify(payload)
        }
      );
      if (res.status === "success") {
        showToast("Custom model configuration synced with database successfully.", "success");
        setIsModelModalOpen(false);
        fetchModelsList();
      } else {
        showToast("Error: " + res.error, "error");
      }
    } catch {
      showToast("API models saving failure.", "error");
    }
  };

  const handleDeleteModel = async (id: string) => {
    if (!confirm("Are you sure you want to permanently delete this model from library?")) return;

    try {
      const res = await apiFetch<{ status: string; error?: string }>(
        `/api/workspace/models/${id}`,
        {
          method: "DELETE"
        }
      );
      if (res.status === "success") {
        showToast("Model deleted from library.", "success");
        fetchModelsList();
      } else {
        showToast("Delete failed: " + res.error, "error");
      }
    } catch {
      showToast("API models deletion failure.", "error");
    }
  };

  return (
    <div className="space-y-6 font-sans">
      {/* SUB-TAB TOGGLES (Integrations vs System Models vs Social Accounts) */}
      <div className="flex border-b border-slate-900 gap-2 font-mono text-xs uppercase overflow-x-auto whitespace-nowrap">
        <button
          onClick={() => setConfigSubTab("integrations")}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 font-bold tracking-widest transition-all cursor-pointer ${
            configSubTab === "integrations"
              ? "border-blue-500 text-blue-400 bg-slate-900/10"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🔌 Workspace Integrations</span>
        </button>
        <button
          onClick={() => setConfigSubTab("models")}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 font-bold tracking-widest transition-all cursor-pointer ${
            configSubTab === "models"
              ? "border-blue-500 text-blue-400 bg-slate-900/10"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🤖 Models & LLM Parameters</span>
        </button>
        <button
          onClick={() => setConfigSubTab("social-accounts")}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 font-bold tracking-widest transition-all cursor-pointer ${
            configSubTab === "social-accounts"
              ? "border-blue-500 text-blue-400 bg-slate-900/10"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>📊 Social Accounts Manager</span>
        </button>
      </div>

      {/* CONFIG VIEW ISOLATOR */}
      {configSubTab === "integrations" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left: Active Integration List */}
          <div className="lg:col-span-2 space-y-4">
            <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-slate-350">
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
                      <div className="flex flex-col gap-1.5 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-indigo-400 font-bold uppercase">{int.platform_name}</span>
                          <span className="text-slate-700">/</span>
                          <span className="text-slate-300 font-semibold">{int.config_key}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] text-slate-500 truncate max-w-[200px] sm:max-w-sm">
                            {isMasked ? "••••••••••••••••" : int.config_value}
                          </span>
                          <button onClick={() => toggleKeyMask(int.id)} className="text-slate-500 hover:text-slate-300 cursor-pointer">
                            {isMasked ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
                          </button>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 shrink-0">
                        <button
                          onClick={() => toggleIntStatus(int.id, int.is_active)}
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider transition-all cursor-pointer ${
                            int.is_active
                              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-900/30"
                              : "bg-slate-800 text-slate-500 border border-slate-700"
                          }`}
                        >
                          {int.is_active ? "Active" : "Inactive"}
                        </button>
                        
                        <button onClick={() => handleStartEditInt(int.id)} className="text-slate-400 hover:text-slate-200 cursor-pointer">
                          ✏️
                        </button>
                        <button onClick={() => handleDeleteIntegration(int.id)} className="text-slate-500 hover:text-rose-455 cursor-pointer">
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
                      className="text-[9px] bg-slate-950 text-slate-500 hover:text-slate-350 border border-slate-800 px-1.5 py-0.5 rounded cursor-pointer"
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
                      className="text-[9px] bg-slate-950 text-slate-500 hover:text-slate-350 border border-slate-800 px-1.5 py-0.5 rounded cursor-pointer"
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
                  className="w-4 h-4 accent-indigo-500 cursor-pointer"
                />
                <label htmlFor="active-check" className="text-[11px] text-slate-300 cursor-pointer">Active State Status</label>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  className="flex-1 py-2 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-bold uppercase tracking-wider rounded border border-indigo-500/30 cursor-pointer"
                >
                  💾 Save Credential
                </button>
                {editingIntId && (
                  <button
                    type="button"
                    onClick={handleCancelEditInt}
                    className="px-3 bg-slate-900 border border-slate-800 text-slate-400 rounded hover:text-slate-200 cursor-pointer"
                  >
                    Cancel
                  </button>
                )}
              </div>

            </form>
          </div>

        </div>
      )}

      {configSubTab === "models" && (
        <div className="space-y-6">
          
          {/* Wide LLM Model Configurations Toolbar */}
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
            
            {/* Left: Filters Sidebar */}
            <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 space-y-4 h-fit">
              <div className="flex justify-between items-center border-b border-slate-900 pb-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">Catalog Filter Matrix</span>
                {(selectedCategory || selectedTag || selectedSeries || selectedModelSize || selectedContext) && (
                  <button
                    onClick={() => {
                      setSelectedCategory(null);
                      setSelectedTag(null);
                      setSelectedSeries(null);
                      setSelectedModelSize(null);
                      setSelectedContext(null);
                    }}
                    className="text-[9px] text-rose-455 hover:text-rose-300 font-mono underline cursor-pointer bg-transparent border-none p-0 outline-none"
                  >
                    Clear all
                  </button>
                )}
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
                        className={`px-2 py-0.5 rounded text-[10px] border cursor-pointer ${
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
                  <span className="text-[10px] text-slate-500 block">Model Size</span>
                  <div className="flex flex-wrap gap-1.5">
                    {["Under 10B", "10 ~ 50B", "50 ~ 100B", "Over 100B"].map(sz => (
                      <button
                        key={sz}
                        onClick={() => setSelectedModelSize(prev => prev === sz ? null : sz)}
                        className={`px-2 py-0.5 rounded text-[10px] border cursor-pointer ${
                          selectedModelSize === sz
                            ? "bg-emerald-500/20 border-emerald-500 text-emerald-400 font-bold"
                            : "border-slate-800 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        {sz}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] text-slate-500 block">Context Window</span>
                  <div className="flex flex-wrap gap-1.5">
                    {[">= 8K", ">= 16K", ">= 32K", ">= 128K"].map(ctx => (
                      <button
                        key={ctx}
                        onClick={() => setSelectedContext(prev => prev === ctx ? null : ctx)}
                        className={`px-2 py-0.5 rounded text-[10px] border cursor-pointer ${
                          selectedContext === ctx
                            ? "bg-amber-500/20 border-amber-500 text-amber-400 font-bold"
                            : "border-slate-800 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        {ctx}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] text-slate-500 block">Series</span>
                  <div className="flex flex-wrap gap-1.5">
                    {["Qwen", "DeepSeek", "Llama", "Kimi"].map(ser => (
                      <button
                        key={ser}
                        onClick={() => setSelectedSeries(prev => prev === ser ? null : ser)}
                        className={`px-2 py-0.5 rounded text-[10px] border cursor-pointer ${
                          selectedSeries === ser
                            ? "bg-indigo-500/20 border-indigo-500 text-indigo-400 font-bold"
                            : "border-slate-800 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        {ser}
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
                        className={`px-2 py-0.5 rounded text-[10px] border cursor-pointer ${
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

            {/* Middle: Spacious Models grid catalog */}
            <div className="xl:col-span-2 space-y-4">
              <div className="flex justify-between items-center gap-3 flex-wrap">
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
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold uppercase tracking-wider rounded-lg flex items-center gap-1 font-mono border border-blue-500/25 shrink-0 cursor-pointer"
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
                    if (selectedSeries && m.series !== selectedSeries) return false;
                    if (selectedModelSize && m.model_size !== selectedModelSize) return false;
                    if (selectedContext && m.context_window !== selectedContext) return false;
                    return true;
                  })
                  .map((m) => {
                    const isActivated = 
                      (m.category === "Embedding" && embedModel === m.model_id) ||
                      (m.category === "Reranker" && rerankModel === m.model_id) ||
                      (m.category !== "Embedding" && m.category !== "Reranker" && (currentAiModel === m.model_id || (currentAiModel === "custom" && customModelId === m.model_id)));
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
                                onClick={() => handleActivateModel(m.model_id, m.category)}
                                className="text-[8px] font-mono font-bold bg-slate-800 text-slate-400 hover:text-slate-200 px-1.5 py-0.5 rounded border border-slate-700 shrink-0 uppercase tracking-widest cursor-pointer"
                              >
                                Activate
                              </button>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-400 leading-normal line-clamp-2 font-sans">{m.description || "No model description available."}</p>
                        </div>

                        <div className="space-y-2">
                          <div className="flex flex-wrap gap-1">
                            {m.special_badge && (
                              <span className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-1.5 py-0.2 rounded text-[8px] font-mono font-bold uppercase">{m.special_badge}</span>
                            )}
                            {m.series && (
                              <span className="bg-slate-950 text-indigo-400 border border-slate-900 px-1.5 py-0.2 rounded text-[8px] font-mono">Series: {m.series}</span>
                            )}
                            {m.model_size && (
                              <span className="bg-slate-950 text-emerald-400 border border-slate-900 px-1.5 py-0.2 rounded text-[8px] font-mono">Size: {m.model_size}</span>
                            )}
                            {m.context_window && (
                              <span className="bg-slate-950 text-amber-400 border border-slate-900 px-1.5 py-0.2 rounded text-[8px] font-mono">Ctx: {m.context_window}</span>
                            )}
                            {m.tags.map(t => (
                              <span key={t} className="bg-slate-950 text-slate-500 border border-slate-900 px-1.5 py-0.2 rounded text-[8px] font-mono">{t}</span>
                            ))}
                          </div>
                          
                          <div className="flex justify-between items-center pt-2 border-t border-slate-950/60 text-[9px] font-mono text-slate-500">
                            <span>{m.provider}</span>
                            <div className="flex gap-2">
                              <button onClick={() => handleOpenEditModelModal(m.id)} className="hover:text-slate-350 cursor-pointer">Edit</button>
                              <button onClick={() => handleDeleteModel(m.id)} className="hover:text-rose-455 cursor-pointer">Delete</button>
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
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">🧠 Active Model Select</label>
                  <select
                    value={currentAiModel}
                    onChange={(e) => {
                      setCurrentAiModel(e.target.value);
                      if (e.target.value !== "custom") handleActivateModel(e.target.value);
                    }}
                    className="w-full bg-slate-950 border border-slate-800 px-3 py-2 text-slate-200 outline-none rounded cursor-pointer"
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
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">🧠 Active Embed Model</label>
                  <select
                    value={modelsList.some(m => m.model_id === embedModel) ? embedModel : "custom"}
                    onChange={(e) => {
                      if (e.target.value !== "custom") setEmbedModel(e.target.value);
                    }}
                    className="w-full bg-slate-950 border border-slate-800 px-3 py-2 text-slate-200 outline-none rounded cursor-pointer"
                  >
                    <option value="Qwen/Qwen3-Embedding-0.6B">Qwen 3 Embedding 0.6B (Default)</option>
                    {modelsList.filter(m => m.category === "Embedding").map(m => (
                      <option key={m.id} value={m.model_id}>{m.name}</option>
                    ))}
                    <option value="custom">Custom model override...</option>
                  </select>
                  {(!modelsList.some(m => m.model_id === embedModel) && embedModel !== "Qwen/Qwen3-Embedding-0.6B") && (
                    <input
                      type="text"
                      placeholder="Custom Embedding ID..."
                      value={embedModel}
                      onChange={(e) => setEmbedModel(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded px-3 py-2 text-slate-200 outline-none mt-2"
                    />
                  )}
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">🧠 Active Reranker Model</label>
                  <select
                    value={modelsList.some(m => m.model_id === rerankModel) ? rerankModel : "custom"}
                    onChange={(e) => {
                      if (e.target.value !== "custom") setRerankModel(e.target.value);
                    }}
                    className="w-full bg-slate-950 border border-slate-800 px-3 py-2 text-slate-200 outline-none rounded cursor-pointer"
                  >
                    <option value="Qwen/Qwen3-Reranker-0.6B">Qwen 3 Reranker 0.6B (Default)</option>
                    {modelsList.filter(m => m.category === "Reranker").map(m => (
                      <option key={m.id} value={m.model_id}>{m.name}</option>
                    ))}
                    <option value="custom">Custom model override...</option>
                  </select>
                  {(!modelsList.some(m => m.model_id === rerankModel) && rerankModel !== "Qwen/Qwen3-Reranker-0.6B") && (
                    <input
                      type="text"
                      placeholder="Custom Reranker ID..."
                      value={rerankModel}
                      onChange={(e) => setRerankModel(e.target.value)}
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
                    className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="font-bold uppercase tracking-wider text-slate-400">📏 Context Window</span>
                    <span className="text-indigo-400 font-bold">{contextLimit.toLocaleString()}</span>
                  </div>
                  <input
                    type="range"
                    min="4000"
                    max="20000"
                    step="1000"
                    value={contextLimit}
                    onChange={(e) => setContextLimit(parseInt(e.target.value))}
                    className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="font-bold uppercase tracking-wider text-slate-400">🔄 Loop Limit</span>
                    <span className="text-indigo-400 font-bold">{recursionLimit}</span>
                  </div>
                  <input
                    type="range"
                    min="2"
                    max="15"
                    step="1"
                    value={recursionLimit}
                    onChange={(e) => setRecursionLimit(parseInt(e.target.value))}
                    className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">🔍 Reranker Layer</label>
                  <select
                    value={rerankerMode}
                    onChange={(e) => setRerankerMode(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 px-3 py-2 text-slate-200 outline-none rounded cursor-pointer"
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
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">🌐 API Base URL Override</label>
                  <input
                    type="text"
                    placeholder="https://api.siliconflow.com/v1"
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
                    className="w-4 h-4 accent-indigo-500 cursor-pointer"
                  />
                  <label htmlFor="thinking-check" className="text-[11px] text-slate-300 cursor-pointer">Enable Thinking Mode</label>
                </div>

                <button
                  onClick={() => handleSaveAISettings(true)}
                  className="w-full py-2 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-bold uppercase tracking-wider rounded border border-indigo-500/30 mt-2 cursor-pointer transition-all"
                >
                  💾 Save Parameters
                </button>
              </div>

            </div>

          </div>

        </div>
      )}

      {configSubTab === "social-accounts" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Active Social Accounts List */}
          <div className="lg:col-span-2 space-y-4">
            <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-slate-350">
              📊 Registered Social Accounts
            </h3>
            
            {socialAccounts.length === 0 ? (
              <div className="bg-slate-900/10 border border-slate-900 rounded-xl p-12 text-center text-slate-500">
                <Database className="h-10 w-10 mx-auto text-slate-700 mb-3" />
                <p className="text-xs font-mono">No social media accounts connected. Connect one in the panel.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {socialAccounts.map((acc) => {
                  const isMasked = !visibleKeyIds.has(acc.id);
                  return (
                    <div key={acc.id} className="bg-slate-900/35 border border-slate-900 rounded-xl p-4 flex justify-between items-center gap-4 hover:border-slate-800/80 transition-all font-mono text-xs">
                      <div className="flex flex-col gap-1.5 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-blue-400 font-bold uppercase">{acc.platform}</span>
                          <span className="text-slate-700">/</span>
                          <span className="text-slate-300 font-semibold">{acc.account_name}</span>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-slate-400">
                          <div><span className="text-slate-600">Ad Account:</span> {acc.account_id}</div>
                          <div><span className="text-slate-600">App ID:</span> {acc.app_id || "N/A"}</div>
                          {acc.access_token && (
                            <div className="col-span-1 md:col-span-2 flex items-center gap-2">
                              <span className="text-slate-600">Token:</span> 
                              <span className="truncate max-w-[200px] sm:max-w-sm">
                                {isMasked ? "••••••••••••••••" : acc.access_token}
                              </span>
                              <button onClick={() => toggleKeyMask(acc.id)} className="text-slate-500 hover:text-slate-300 cursor-pointer">
                                {isMasked ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 shrink-0">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          acc.status === 'active'
                            ? "bg-emerald-500/15 text-emerald-400 border border-emerald-900/30"
                            : "bg-rose-500/15 text-rose-400 border border-rose-900/30"
                        }`}>
                          {acc.status}
                        </span>
                        
                        <button onClick={() => handleStartEditSocial(acc.id)} className="text-slate-400 hover:text-slate-200 cursor-pointer">
                          ✏️
                        </button>
                        <button onClick={() => handleDeleteSocialAccount(acc.id)} className="text-slate-500 hover:text-rose-455 cursor-pointer">
                          ❌
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right: Add / Update Social Account form */}
          <div className="bg-slate-900/35 border border-slate-900 rounded-xl p-5 h-fit space-y-4">
            <h3 className="text-xs font-extrabold uppercase tracking-widest font-mono text-blue-400">
              {editingSocialId ? "✏️ Edit Social Account" : "📝 Link Social Media Account"}
            </h3>

            <form onSubmit={handleSaveSocialAccount} className="space-y-4 font-mono text-xs">
              
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Platform</label>
                <select
                  value={formSocialPlatform}
                  onChange={(e) => setFormSocialPlatform(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded px-3 py-2 text-slate-200 outline-none cursor-pointer"
                >
                  <option value="facebook">Facebook Ads</option>
                  <option value="tiktok">TikTok Ads</option>
                  <option value="instagram">Instagram Ads</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Account Display Name</label>
                <input
                  type="text"
                  required
                  placeholder="E.g. TOPVNSPORT Main Page..."
                  value={formSocialAccountName}
                  onChange={(e) => setFormSocialAccountName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded px-3 py-2 text-slate-200 outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Ad Account ID</label>
                <input
                  type="text"
                  required
                  placeholder="E.g. act_12345678..."
                  value={formSocialAccountId}
                  onChange={(e) => setFormSocialAccountId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded px-3 py-2 text-slate-200 outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">OAuth App ID</label>
                <input
                  type="text"
                  placeholder="Facebook App ID..."
                  value={formSocialAppId}
                  onChange={(e) => setFormSocialAppId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded px-3 py-2 text-slate-200 outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">OAuth App Secret</label>
                <input
                  type="password"
                  placeholder="Facebook App Secret..."
                  value={formSocialAppSecret}
                  onChange={(e) => setFormSocialAppSecret(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded px-3 py-2 text-slate-200 outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">User Access Token</label>
                <textarea
                  placeholder="EAAYigFc8hHsBR..."
                  rows={3}
                  value={formSocialAccessToken}
                  onChange={(e) => setFormSocialAccessToken(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded px-3 py-2 text-slate-200 outline-none resize-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Account Status</label>
                <select
                  value={formSocialStatus}
                  onChange={(e) => setFormSocialStatus(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded px-3 py-2 text-slate-200 outline-none cursor-pointer"
                >
                  <option value="active">Active State</option>
                  <option value="disabled">Disabled State</option>
                  <option value="restricted">Restricted State</option>
                </select>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  className="flex-1 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold uppercase tracking-wider rounded border border-blue-500/30 cursor-pointer"
                >
                  💾 Save Connection
                </button>
                {editingSocialId && (
                  <button
                    type="button"
                    onClick={handleCancelEditSocial}
                    className="px-3 bg-slate-900 border border-slate-800 text-slate-400 rounded hover:text-slate-200 cursor-pointer"
                  >
                    Cancel
                  </button>
                )}
              </div>

            </form>
          </div>
        </div>
      )}

      {/* Model Catalog Register/Edit Modal */}
      <Modal
        isOpen={isModelModalOpen}
        onClose={() => setIsModelModalOpen(false)}
        title={formModelUuid ? "✏️ Edit Model Library Entry" : "➕ Register New Custom Model"}
        maxWidth="lg"
      >
        <form onSubmit={handleSaveModelForm} className="space-y-3 font-mono text-xs">
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
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none cursor-pointer"
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
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none cursor-pointer"
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
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 outline-none cursor-pointer"
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
              className="px-4 py-2 bg-slate-950 hover:bg-slate-800 text-slate-400 rounded border border-slate-800 cursor-pointer"
            >
              Cancel
            </button>
            
            <button
              type="submit"
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-505 hover:to-cyan-505 text-white font-bold uppercase tracking-wider rounded border border-blue-500/25 shadow-lg cursor-pointer"
            >
              💾 Save Model Configuration
            </button>
          </div>
        </form>
      </Modal>

    </div>
  );
}
