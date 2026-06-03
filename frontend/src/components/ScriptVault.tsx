"use client";

import React, { useState, useEffect } from "react";
import { Search, RefreshCw, Copy, Check, FileText, Calendar, Award } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface VaultVariant {
  platform: string;
  adapted_copy: string;
  publish_status: string;
  created_at: string | null;
}

interface VaultContent {
  id: string;
  campaign_name: string;
  core_message: string;
  created_at: string | null;
  variants: VaultVariant[];
}

export default function ScriptVault() {
  const [contents, setContents] = useState<VaultContent[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activePlatformTab, setActivePlatformTab] = useState<{ [key: string]: number }>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  
  // Custom toast notification
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const loadVaultContents = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/vault/contents`);
      if (!response.ok) throw new Error("HTTP error " + response.status);
      const data = await response.json();
      setContents(data);
      
      // Auto initialize first platform index as active tab for each card
      const initialTabState: { [key: string]: number } = {};
      data.forEach((item: VaultContent) => {
        initialTabState[item.id] = 0;
      });
      setActivePlatformTab(initialTabState);
    } catch (error) {
      console.error(error);
      showToast("❌ Lỗi tải dữ liệu kho lưu trữ kịch bản.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVaultContents();
  }, []);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(id);
      showToast("📋 Đã sao chép kịch bản vào bộ nhớ tạm!");
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  // Filter logic
  const getFilteredContents = () => {
    return contents.filter(item => {
      const matchesName = item.campaign_name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesMessage = item.core_message.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesVariants = item.variants.some(v => 
        v.adapted_copy.toLowerCase().includes(searchQuery.toLowerCase()) ||
        v.platform.toLowerCase().includes(searchQuery.toLowerCase())
      );
      return matchesName || matchesMessage || matchesVariants;
    });
  };

  const filteredContents = getFilteredContents();

  return (
    <div className="space-y-6">
      {/* Toast popup */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-lg border border-emerald-500/20 bg-slate-900/90 text-emerald-400 border-l-4 border-l-emerald-500 shadow-xl backdrop-blur-md transition-all duration-300">
          <span>✅</span>
          <span className="text-xs font-semibold text-slate-200">{toast}</span>
        </div>
      )}

      {/* Action Header */}
      <div className="flex flex-wrap gap-4 items-center justify-between">
        <div className="flex-1 min-w-[280px] relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Tìm kiếm kịch bản, tên chiến dịch, hoặc nền tảng..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-900 focus:border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-200 outline-none transition-all font-sans"
          />
        </div>
        <button
          onClick={loadVaultContents}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-slate-900 border border-slate-800 text-xs font-bold uppercase tracking-wider text-slate-300 rounded-lg hover:bg-slate-800 hover:text-white transition-all disabled:opacity-50 cursor-pointer font-mono"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Tải lại dữ liệu
        </button>
      </div>

      {/* Script cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {loading ? (
          <div className="col-span-2 py-20 text-center text-xs text-slate-500 flex items-center justify-center gap-2 font-mono">
            <RefreshCw className="h-4 w-4 animate-spin text-blue-500" />
            Đang tải kịch bản từ kho lưu trữ...
          </div>
        ) : filteredContents.length > 0 ? (
          filteredContents.map(item => {
            const activeTabIdx = activePlatformTab[item.id] || 0;
            const activeVariant = item.variants[activeTabIdx];

            return (
              <div
                key={item.id}
                className="bg-slate-900/25 border border-slate-900 rounded-xl p-5 hover:border-slate-800/80 transition-all flex flex-col gap-4 relative overflow-hidden group"
              >
                {/* Visual border marker */}
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-600"></div>
                
                {/* Header */}
                <div className="flex justify-between items-start gap-4 pb-3 border-b border-slate-900/80">
                  <div className="space-y-0.5">
                    <h4 className="text-sm font-bold text-slate-200 font-sans group-hover:text-white transition-colors">{item.campaign_name}</h4>
                    <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1">
                      <Calendar className="h-2.5 w-2.5" />
                      Duyệt: {item.created_at || "Không rõ"}
                    </span>
                  </div>
                  <span className="text-[9px] font-mono font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-900/20 px-2 py-0.5 rounded uppercase tracking-wider flex items-center gap-1">
                    <Award className="h-3 w-3" />
                    APPROVED
                  </span>
                </div>

                {/* Core Message */}
                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-blue-500 uppercase tracking-widest font-mono">Thông điệp cốt lõi (Core Message)</span>
                  <div className="text-xs font-serif italic text-slate-300 bg-blue-950/5 border-l border-l-blue-500/50 p-2.5 rounded leading-relaxed">
                    &quot;{item.core_message}&quot;
                  </div>
                </div>

                {/* Variants Adaptive */}
                <div className="space-y-2 flex-1 flex flex-col justify-end">
                  <span className="text-[10px] font-bold text-blue-500 uppercase tracking-widest font-mono">Kịch bản thích ứng</span>
                  
                  {/* Platform Tab Buttons */}
                  <div className="flex flex-wrap gap-1 bg-slate-950/60 border border-slate-900/80 p-1 rounded-lg shrink-0 w-max">
                    {item.variants.length > 0 ? (
                      item.variants.map((v, idx) => (
                        <button
                          key={idx}
                          onClick={() => setActivePlatformTab(prev => ({ ...prev, [item.id]: idx }))}
                          className={`px-3 py-1.5 text-[9px] font-extrabold uppercase tracking-widest rounded-md transition-all duration-200 cursor-pointer ${
                            activeTabIdx === idx
                              ? "bg-blue-950/80 text-blue-400 border border-blue-900/40 shadow-sm"
                              : "text-slate-500 hover:text-slate-300 border border-transparent"
                          }`}
                        >
                          {v.platform}
                        </button>
                      ))
                    ) : (
                      <span className="text-[10px] text-slate-500 font-sans px-2">Không có thích ứng kênh</span>
                    )}
                  </div>

                  {/* Content Area */}
                  <div className="bg-slate-950 border border-slate-900 rounded-lg p-3 relative flex-1 flex flex-col justify-between min-h-[140px] font-mono text-[11px] group/copy">
                    {activeVariant ? (
                      <>
                        <p className="text-slate-300 font-sans whitespace-pre-wrap leading-relaxed pr-8 pb-4">
                          {activeVariant.adapted_copy}
                        </p>
                        <button
                          onClick={() => handleCopy(activeVariant.adapted_copy, `${item.id}-${activeVariant.platform}`)}
                          className={`absolute top-2.5 right-2.5 bg-slate-900 border border-slate-800 hover:border-slate-750 p-1.5 rounded transition-all cursor-pointer opacity-0 group-hover/copy:opacity-100 ${
                            copiedId === `${item.id}-${activeVariant.platform}`
                              ? "text-emerald-400 border-emerald-500/35 bg-emerald-950/20"
                              : "text-slate-400 hover:text-slate-200"
                          }`}
                          title="Copy kịch bản"
                        >
                          {copiedId === `${item.id}-${activeVariant.platform}` ? (
                            <Check className="h-3 w-3 text-emerald-400" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </button>
                        <div className="flex justify-between items-center text-[8px] text-slate-600 mt-2 shrink-0 border-t border-slate-900 pt-1.5">
                          <span>PLATFORM: {activeVariant.platform.toUpperCase()}</span>
                          <span>STATUS: {activeVariant.publish_status.toUpperCase()}</span>
                        </div>
                      </>
                    ) : (
                      <p className="text-slate-500 italic py-8 text-center">Không tìm thấy bản dịch kịch bản cho nền tảng này.</p>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="col-span-2 text-center py-20 text-xs text-slate-500">
            🏛️ Chưa có kịch bản quảng cáo nào được duyệt trong kho tài sản.
          </div>
        )}
      </div>
    </div>
  );
}
