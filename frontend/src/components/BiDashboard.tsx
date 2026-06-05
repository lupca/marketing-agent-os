"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  TrendingUp,
  Cpu,
  RefreshCw,
  Layers,
  Activity,
  DollarSign,
  HelpCircle,
  Clock
} from "lucide-react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer
} from "recharts";
import { Card } from "@/components/ui/Card";
import { Slider } from "@/components/ui/Slider";
import { useToast } from "@/components/ui/Toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface KPIState {
  ad_spend: number;
  total_conversions: number;
  blended_cac: number;
  ltv_cac_ratio: number;
  ltv_cac_health: string;
  cac_payback_period: number;
  active_campaigns: number;
}

interface AnchorState {
  price: number;
  cost: number;
  target_cpa: number;
}

interface ChannelData {
  name: string;
  views: number;
  clicks: number;
  conversions: number;
  cpa: number;
}

interface FatigueAlert {
  platform: string;
  angle_name: string;
  cpa_3d: number;
  cpa_7d: number;
  ratio: number;
}

interface WinningBoardItem {
  platform: string;
  cpa: number;
  angle_name: string;
  adapted_copy: string;
  spend: number;
  conversions: number;
}

interface KilledBoardItem {
  platform: string;
  failed_cpa: number;
  angle_name: string;
  adapted_copy: string;
  reason_killed: string;
  spend: number;
}

interface AntiPattern {
  content: string;
  source_name: string;
}

interface AuditLog {
  action: string;
  metadata: string | Record<string, unknown> | null | undefined;
}

export default function BiDashboard() {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [kpis, setKpis] = useState<KPIState>({
    ad_spend: 0,
    total_conversions: 0,
    blended_cac: 0,
    ltv_cac_ratio: 0,
    ltv_cac_health: "healthy",
    cac_payback_period: 0,
    active_campaigns: 0
  });
  const [anchor, setAnchor] = useState<AnchorState>({
    price: 5000000,
    cost: 1500000,
    target_cpa: 1050000
  });
  const [fatigueAlerts, setFatigueAlerts] = useState<FatigueAlert[]>([]);
  const [winningBoard, setWinningBoard] = useState<WinningBoardItem[]>([]);
  const [killedBoard, setKilledBoard] = useState<KilledBoardItem[]>([]);
  const [antiPatterns, setAntiPatterns] = useState<AntiPattern[]>([]);
  const [trendChart, setTrendChart] = useState<{ labels: string[]; values: number[] }>({ labels: [], values: [] });
  const [channelData, setChannelData] = useState<ChannelData[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  // What-If Simulator Inputs
  const [simBudget, setSimBudget] = useState(10000000);
  const [simPrice, setSimPrice] = useState(5000000);
  const [simCost, setSimCost] = useState(1500000);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/dashboard/metrics`);
      if (!response.ok) throw new Error("HTTP error " + response.status);
      const data = await response.json();

      if (data.error) {
        showToast("Lỗi tải báo cáo: " + data.error, "error");
        return;
      }

      setKpis(data.kpis || {});
      if (data.anchor) {
        setAnchor(data.anchor);
        setSimPrice(data.anchor.price);
        setSimCost(data.anchor.cost);
      }
      setFatigueAlerts(data.fatigue || []);
      setWinningBoard(data.winning_board || []);
      setKilledBoard(data.killed_board || []);
      setAntiPatterns(data.anti_patterns || []);
      setTrendChart(data.trend_chart || { labels: [], values: [] });
      setChannelData(data.channel_data || []);
      setAuditLogs(data.audit_logs || []);

      showToast("Đã đồng bộ số liệu thời gian thực thành công!", "success");
    } catch (error) {
      console.error(error);
      showToast("Không thể kết nối máy chủ để tải số liệu thời gian thực.", "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  const handleSyncMetrics = async () => {
    setSyncing(true);
    try {
      const response = await fetch(`${API_BASE}/api/dashboard/sync-metrics`, {
        method: "POST"
      });
      const data = await response.json();
      showToast(data.message || "Đã gửi yêu cầu đồng bộ thành công!", "success");
    } catch (error) {
      console.error(error);
      showToast("Không thể đồng bộ số liệu quảng cáo.", "error");
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchMetrics();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchMetrics]);

  // Format currency in VND
  const formatVND = (value: number) => {
    return new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND"
    }).format(value).replace(",00 ₫", "đ");
  };

  // What-If Simulator Calculations
  const simMargin = simPrice - simCost;
  const simTargetCpa = simMargin * 0.3; // Safe CAC target capped at 30% margin
  const simBreakevenLeads = simMargin > 0 ? (simBudget / simMargin) : 0;
  const expectedLeads = simTargetCpa > 0 ? (simBudget / simTargetCpa) : 0;
  const expectedROAS = simBudget > 0 ? ((expectedLeads * simPrice) / simBudget) : 0;

  // Inverse CPA Budget Advisor
  const getAdvisorAllocations = () => {
    const defaultCpas: { [key: string]: number } = {
      Google: 680000,
      Facebook: 720000,
      TikTok: 880000
    };

    const cpas: { [key: string]: number } = {
      Google: channelData.find(c => c.name === "Google")?.cpa || defaultCpas.Google,
      Facebook: channelData.find(c => c.name === "Facebook")?.cpa || defaultCpas.Facebook,
      TikTok: channelData.find(c => c.name === "TikTok")?.cpa || defaultCpas.TikTok
    };

    let sumInverse = 0;
    const weights: { [key: string]: number } = {};
    for (const channel in cpas) {
      const cpa = cpas[channel];
      if (cpa > 0) {
        const inverseWeight = 1.0 / cpa;
        weights[channel] = inverseWeight;
        sumInverse += inverseWeight;
      } else {
        weights[channel] = 0;
      }
    }

    return Object.keys(cpas).map(channel => {
      const percent = sumInverse > 0 ? (weights[channel] / sumInverse) : 0.33;
      const allocatedBudget = Math.round(simBudget * percent);
      const expectedConvs = cpas[channel] > 0 ? (allocatedBudget / cpas[channel]) : 0;
      return {
        channel,
        cpa: cpas[channel],
        percent: percent * 100,
        allocatedBudget,
        expectedConvs
      };
    });
  };

  const allocations = getAdvisorAllocations();

  // Recharts Data formatting
  const rechartsTrendData = trendChart.labels.map((lbl, idx) => ({
    name: lbl,
    CPA: trendChart.values[idx] || 0
  }));

  const rechartsFunnelData = channelData.map(ch => ({
    name: ch.name,
    "Lượt Xem (Views)": ch.views,
    "Lượt Click (x10)": ch.clicks * 10,
    "Leads Đơn (x100)": ch.conversions * 100
  }));

  // Token Audit aggregates
  const getBillingStats = () => {
    const billingLogs = auditLogs.filter(
      log => log.action === "Execution Billing Audit" && log.metadata
    );

    let totalPrompt = 0;
    let totalCompletion = 0;
    let totalCost = 0;

    const chartData = billingLogs.map((log, index) => {
      const meta = typeof log.metadata === "string" ? JSON.parse(log.metadata) : log.metadata;
      const prompt = meta.prompt_tokens || 0;
      const completion = meta.completion_tokens || 0;
      const cost = meta.total_cost_usd || 0;

      totalPrompt += prompt;
      totalCompletion += completion;
      totalCost += cost;

      return {
        name: `#${index + 1}`,
        "Prompt Tokens": prompt,
        "Completion Tokens": completion,
        cost
      };
    });

    return {
      totalPrompt,
      totalCompletion,
      totalCost,
      callsCount: billingLogs.length,
      chartData
    };
  };

  const billingStats = getBillingStats();

  return (
    <div className="space-y-6">
      {/* Header Buttons */}
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-widest font-mono">CMO BI Controller</h2>
        </div>
        <div className="flex gap-3">
          <button
            onClick={fetchMetrics}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-900 border border-slate-800 text-xs font-bold uppercase tracking-wider text-slate-300 rounded hover:bg-slate-800 hover:text-white transition-all disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
            Tải Lại Số Liệu
          </button>
          <button
            onClick={handleSyncMetrics}
            disabled={syncing}
            className="flex items-center gap-2 px-3 py-1.5 bg-emerald-950/30 border border-emerald-900/40 text-xs font-bold uppercase tracking-wider text-emerald-400 rounded hover:bg-emerald-900/30 hover:text-emerald-300 transition-all disabled:opacity-50 cursor-pointer"
          >
            <Activity className="h-3 w-3" />
            {syncing ? "Đang đồng bộ..." : "Đồng Bộ Metrics"}
          </button>
        </div>
      </div>

      {/* KPI GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <Card glowColor="blue">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
            <DollarSign className="h-3.5 w-3.5 text-blue-400" /> Tổng Chi Phí Ads
          </span>
          <span className="text-xl font-extrabold tracking-tight text-slate-100 font-mono mt-1">{formatVND(kpis.ad_spend)}</span>
          <span className="text-[10px] text-slate-500 font-sans mt-auto">Đầu tư phân bổ ngân sách Q2</span>
        </Card>

        <Card glowColor="emerald">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
            <Activity className="h-3.5 w-3.5 text-emerald-400" /> Đơn Hàng (Leads)
          </span>
          <span className="text-xl font-extrabold tracking-tight text-slate-100 font-mono mt-1">{kpis.total_conversions} Leads</span>
          <span className="text-[10px] text-slate-500 font-sans mt-auto">CTR tốt của các Ads tự trị</span>
        </Card>

        <Card glowColor="indigo">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
            <TrendingUp className="h-3.5 w-3.5 text-indigo-400" /> Blended CAC
          </span>
          <span className="text-xl font-extrabold tracking-tight text-slate-100 font-mono mt-1">{formatVND(kpis.blended_cac)}</span>
          <div className="text-[10px] flex items-center gap-1 mt-auto font-mono">
            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${kpis.blended_cac <= anchor.target_cpa ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-rose-500/10 text-rose-400 border-rose-500/20"}`}>
              {kpis.blended_cac <= anchor.target_cpa ? "✓ Dưới target" : "⚠️ Vượt target"}
            </span>
          </div>
        </Card>

        <Card glowColor="amber">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
            <Cpu className="h-3.5 w-3.5 text-amber-400" /> LTV:CAC Health
          </span>
          <span className="text-xl font-extrabold tracking-tight text-slate-100 font-mono mt-1">{kpis.ltv_cac_ratio} x</span>
          <span className="text-[10px] font-sans mt-auto">
            Trạng thái:{" "}
            <span className={`font-bold ${kpis.ltv_cac_health === "healthy" ? "text-emerald-400" : kpis.ltv_cac_health === "warning" ? "text-amber-400" : "text-rose-400"}`}>
              {kpis.ltv_cac_health === "healthy" ? "Lành Mạnh 🟢" : kpis.ltv_cac_health === "warning" ? "Cảnh Báo 🟡" : "Nguy Hiểm 🔴"}
            </span>
          </span>
        </Card>

        <Card glowColor="purple">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-purple-400" /> Chu Kỳ Hòa Vốn
          </span>
          <span className="text-xl font-extrabold tracking-tight text-slate-100 font-mono mt-1">{kpis.cac_payback_period || 0} Tháng</span>
          <span className="text-[10px] text-slate-500 font-sans mt-auto">Thời gian ước tính thu hồi vốn</span>
        </Card>

        <Card glowColor="rose">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5 text-rose-400" /> Camp Hoạt Động
          </span>
          <span className="text-xl font-extrabold tracking-tight text-slate-100 font-mono mt-1">{kpis.active_campaigns} Camp</span>
          <span className="text-[10px] text-slate-500 font-sans mt-auto">Đang vận hành tự trị</span>
        </Card>
      </div>

      {/* Fatigue Alert Banner */}
      {fatigueAlerts.length > 0 && (
        <div className="bg-rose-950/20 border border-rose-500/15 rounded-xl p-5 relative overflow-hidden">
          <div className="absolute top-0 right-0 h-24 w-24 bg-rose-500/5 blur-2xl"></div>
          <div className="flex gap-3">
            <span className="text-xl leading-none">🚨</span>
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-rose-400 uppercase tracking-wider font-mono">Phát Hiện Sáng Tạo Mệt Mỏi Sớm (Early Creative Fatigue)</h3>
              <p className="text-xs text-slate-300 leading-relaxed font-sans">
                Hệ thống tự động phát hiện CPA tăng đột biến trong 3 ngày qua so với trung bình 7 ngày cũ. Khuyến cáo đổi Góc viết (Angle) sớm.
              </p>
              <div className="space-y-1.5 pt-1">
                {fatigueAlerts.map((item, idx) => (
                  <div key={idx} className="text-[11px] text-slate-400 font-mono flex items-start gap-2">
                    <span className="text-rose-500">👉</span>
                    <span>
                      <strong>[{item.platform}] Góc sáng tạo &quot;{item.angle_name}&quot;</strong>: CPA 3 ngày qua đạt <strong>{formatVND(item.cpa_3d)}</strong> tăng gấp <strong>{item.ratio} lần</strong> so với trung bình ({formatVND(item.cpa_7d)}).
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CHARTS ROW */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* CPA Trend Chart */}
        <div className="bg-slate-900/25 border border-slate-900 rounded-xl p-5 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-xs font-extrabold text-slate-200 uppercase tracking-widest font-mono">Biểu Đồ Tối Ưu CPA (Learning Curve)</h3>
              <p className="text-[11px] text-slate-500 font-sans">Tiến trình tối ưu Blended CPA hệ thống</p>
            </div>
            <div className="text-xs text-slate-500 font-mono">Cập nhật thời gian thực</div>
          </div>
          <div className="h-[250px] w-full bg-slate-950/20 border border-slate-900/50 rounded-lg p-2">
            {rechartsTrendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rechartsTrendData} margin={{ top: 10, right: 10, left: -10, bottom: 5 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} fontStyle="mono" tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={10} fontStyle="mono" tickLine={false} tickFormatter={value => formatVND(value).replace("đ", "")} />
                  <RechartsTooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f1f5f9", fontSize: "11px", fontFamily: "monospace" }} formatter={(value) => [formatVND(Number(value || 0)), "Blended CPA"]} />
                  <Line type="monotone" dataKey="CPA" stroke="#6366f1" strokeWidth={3} activeDot={{ r: 6 }} dot={{ fill: "#818cf8", strokeWidth: 1.5, r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-500">Chưa có dữ liệu xu hướng</div>
            )}
          </div>
        </div>

        {/* Channel Funnel Chart */}
        <div className="bg-slate-900/25 border border-slate-900 rounded-xl p-5 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-xs font-extrabold text-slate-200 uppercase tracking-widest font-mono">Hiệu Suất Chuyển Đổi Phễu Kênh (Views → Clicks → Leads)</h3>
              <p className="text-[11px] text-slate-500 font-sans">Chi tiết chuyển đổi quảng cáo phân tách theo kênh</p>
            </div>
            <div className="text-xs text-slate-500 font-mono">Quy mô: Clicks x10, Leads x100</div>
          </div>
          <div className="h-[250px] w-full bg-slate-950/20 border border-slate-900/50 rounded-lg p-2">
            {rechartsFunnelData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rechartsFunnelData} margin={{ top: 10, right: 10, left: -10, bottom: 5 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} fontStyle="mono" tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={10} fontStyle="mono" tickLine={false} />
                  <RechartsTooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f1f5f9", fontSize: "11px", fontFamily: "monospace" }} />
                  <Legend wrapperStyle={{ fontSize: "10px", color: "#9ca3af" }} />
                  <Bar dataKey="Lượt Xem (Views)" fill="rgba(99, 102, 241, 0.65)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Lượt Click (x10)" fill="rgba(245, 158, 11, 0.7)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Leads Đơn (x100)" fill="rgba(16, 185, 129, 0.75)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-500">Chưa có dữ liệu kênh</div>
            )}
          </div>
        </div>
      </div>

      {/* WHAT-IF SIMULATOR */}
      <div className="bg-slate-900/25 border border-slate-900 rounded-xl p-5 space-y-4">
        <div>
          <h3 className="text-xs font-extrabold text-slate-200 uppercase tracking-widest font-mono">🎛️ Bộ Giả Lập Quyết Định Kinh Doanh & Trợ Lý Phân Bổ Ngân Sách AI</h3>
          <p className="text-[11px] text-slate-500 font-sans">Client-side Reactive Simulation + Performance-Weighted Algorithm</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Sliders Input */}
          <div className="space-y-4 bg-slate-950/40 p-4 border border-slate-900/60 rounded-lg">
            <Slider
              label="Ngân Sách Thử Nghiệm (Budget)"
              tooltip="Tổng ngân sách dự kiến dùng để chạy các kịch bản quảng cáo thử nghiệm A/B trên các kênh Google, Facebook, TikTok."
              min={2000000}
              max={100000000}
              step={1000000}
              value={simBudget}
              onChange={setSimBudget}
              formatValue={formatVND}
              accentColor="blue"
            />

            <Slider
              label="Giá Bán Lẻ Sản Phẩm (Price)"
              tooltip="Giá bán sản phẩm đầu ra do CMO ấn định cho chiến dịch này."
              min={1000000}
              max={20000000}
              step={500000}
              value={simPrice}
              onChange={setSimPrice}
              formatValue={formatVND}
              accentColor="indigo"
            />

            <Slider
              label="Giá Vốn Sản Phẩm (Cost)"
              tooltip="Chi phí sản xuất hoặc nhập kho, làm cơ sở tính toán biên lợi nhuận."
              min={200000}
              max={10000000}
              step={100000}
              value={simCost}
              onChange={setSimCost}
              formatValue={formatVND}
              accentColor="amber"
            />
          </div>

          {/* Results & Advisor */}
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-950/60 border border-slate-900/80 rounded-lg p-3 text-center relative group/tooltip hover:border-slate-850 hover:bg-slate-950/80 transition-all cursor-default">
                <div className="text-[10px] font-mono text-slate-500 uppercase flex items-center justify-center gap-1.5">
                  Biên Lợi Nhuận
                  <HelpCircle className="h-3 w-3 text-slate-650" />
                </div>
                <div className="text-sm font-bold text-indigo-300 font-mono mt-1">{formatVND(simMargin)}</div>
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover/tooltip:block bg-slate-900 border border-slate-800 text-slate-200 text-[10px] p-2.5 rounded-lg shadow-2xl w-48 leading-relaxed z-50 font-sans backdrop-blur-md">
                  Giá bán - Giá vốn. Lượng lợi nhuận thô thu được trên mỗi sản phẩm bán ra.
                </div>
              </div>

              <div className="bg-slate-950/60 border border-slate-900/80 rounded-lg p-3 text-center relative group/tooltip hover:border-slate-850 hover:bg-slate-950/80 transition-all cursor-default">
                <div className="text-[10px] font-mono text-slate-500 uppercase flex items-center justify-center gap-1.5">
                  CPA Target An Toàn (30%)
                  <HelpCircle className="h-3 w-3 text-slate-650" />
                </div>
                <div className="text-sm font-bold text-blue-400 font-mono mt-1">{formatVND(simTargetCpa)}</div>
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover/tooltip:block bg-slate-900 border border-slate-800 text-slate-200 text-[10px] p-2.5 rounded-lg shadow-2xl w-48 leading-relaxed z-50 font-sans backdrop-blur-md">
                  Mức chi phí tối đa cho một Lead để đảm bảo biên lợi nhuận của bạn không giảm quá 30%.
                </div>
              </div>

              <div className="bg-slate-950/60 border border-slate-900/80 rounded-lg p-3 text-center relative group/tooltip hover:border-slate-850 hover:bg-slate-950/80 transition-all cursor-default">
                <div className="text-[10px] font-mono text-slate-500 uppercase flex items-center justify-center gap-1.5">
                  Đơn Để Hòa Vốn
                  <HelpCircle className="h-3 w-3 text-slate-650" />
                </div>
                <div className="text-sm font-bold text-amber-400 font-mono mt-1">{simBreakevenLeads.toFixed(1)} Leads</div>
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover/tooltip:block bg-slate-900 border border-slate-800 text-slate-200 text-[10px] p-2.5 rounded-lg shadow-2xl w-48 leading-relaxed z-50 font-sans backdrop-blur-md">
                  Số lượng đơn hàng cần bán ra để thu hồi toàn bộ ngân sách thử nghiệm đã đầu tư.
                </div>
              </div>

              <div className="bg-slate-950/60 border border-slate-900/80 rounded-lg p-3 text-center relative group/tooltip hover:border-slate-850 hover:bg-slate-950/80 transition-all cursor-default">
                <div className="text-[10px] font-mono text-slate-500 uppercase flex items-center justify-center gap-1.5">
                  ROAS Kỳ Vọng Tối Thiểu
                  <HelpCircle className="h-3 w-3 text-slate-650" />
                </div>
                <div className="text-sm font-bold text-emerald-400 font-mono mt-1">{expectedROAS.toFixed(2)} x</div>
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover/tooltip:block bg-slate-900 border border-slate-800 text-slate-200 text-[10px] p-2.5 rounded-lg shadow-2xl w-48 leading-relaxed z-50 font-sans backdrop-blur-md">
                  Tỉ suất doanh thu trên ngân sách quảng cáo mong muốn khi đạt điểm CPA Target.
                </div>
              </div>
            </div>

            {/* AI Advisor Allocations */}
            <div className="bg-slate-950/40 border border-slate-900/60 rounded-lg p-3.5 space-y-2">
              <div className="text-xs font-bold text-slate-350 font-mono">🧠 Cố Vấn Phân Bổ Ngân Sách AI (Performance-Weighted)</div>
              <div className="space-y-2 pt-1.5">
                {allocations.map((alloc, idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-[10px] font-mono">
                      <span className="text-slate-400">💻 Kênh <strong>{alloc.channel}</strong> (CPA Lịch Sử: {formatVND(alloc.cpa)})</span>
                      <span className="text-indigo-300 font-semibold">{alloc.percent.toFixed(1)}% | <strong>{formatVND(alloc.allocatedBudget)}</strong> (~{alloc.expectedConvs.toFixed(1)} Leads)</span>
                    </div>
                    <div className="w-full bg-slate-900/70 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${alloc.channel === "Google" ? "bg-blue-500" : alloc.channel === "Facebook" ? "bg-indigo-500" : "bg-emerald-500"}`}
                        style={{ width: `${alloc.percent}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* DOUBLE BOARDS (WINNING vs KILLED) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Winning Angles */}
        <div className="bg-slate-900/25 border border-emerald-500/15 rounded-xl p-5 space-y-4">
          <div>
            <h3 className="text-xs font-extrabold text-emerald-400 uppercase tracking-widest font-mono flex items-center gap-1.5">🏆 Góc Sáng Tạo Vinh Danh (Winning Angles)</h3>
            <p className="text-[11px] text-slate-500 font-sans">Chiến dịch hiệu suất cao: CPA &lt; CPA Target</p>
          </div>
          <div className="space-y-3 max-h-[350px] overflow-y-auto pr-1">
            {winningBoard.length > 0 ? (
              winningBoard.map((item, idx) => (
                <div key={idx} className="bg-gradient-to-br from-emerald-950/15 via-slate-900/35 to-slate-900/40 border border-emerald-500/20 hover:border-emerald-500/45 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-emerald-950/10 rounded-lg p-3.5 space-y-2 transition-all duration-300 font-mono text-xs">
                  <div className="flex justify-between items-center">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      item.platform.toLowerCase() === "facebook" ? "bg-indigo-500/10 text-indigo-400" : "bg-emerald-500/10 text-emerald-400"
                    }`}>{item.platform}</span>
                    <span className="text-emerald-400 font-bold bg-emerald-950/20 px-2 py-0.5 rounded border border-emerald-500/30">CPA: {formatVND(item.cpa)}</span>
                  </div>
                  <div className="text-[11px] text-slate-300 flex items-center gap-1.5">
                    <span>🏆</span>
                    <span>Góc: <strong className="text-slate-100 font-semibold">{item.angle_name}</strong></span>
                  </div>
                  <p className="text-[11px] text-slate-300 bg-slate-950/80 p-2.5 rounded font-sans italic border-l-2 border-l-emerald-500">&quot;{item.adapted_copy}&quot;</p>
                  <div className="flex justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-900/50 mt-1">
                    <span>👁️ {item.spend > 0 ? Math.round(item.spend / 1000) : 0}k views</span>
                    <span>💰 Đã tiêu: {formatVND(item.spend)}</span>
                    <span>🎯 {item.conversions} leads</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-xs text-slate-500">Chưa có kịch bản vinh danh nào.</div>
            )}
          </div>
        </div>

        {/* Killed Variants */}
        <div className="bg-slate-900/25 border border-rose-500/15 rounded-xl p-5 space-y-4">
          <div>
            <h3 className="text-xs font-extrabold text-rose-400 uppercase tracking-widest font-mono flex items-center gap-1.5">💀 Góc Kịch Bản Khai Tử (Killed Board)</h3>
            <p className="text-[11px] text-slate-500 font-sans">Chiến dịch bị Agent tự tắt: CPA &gt; CPA Target</p>
          </div>
          <div className="space-y-3 max-h-[350px] overflow-y-auto pr-1">
            {killedBoard.length > 0 ? (
              killedBoard.map((item, idx) => (
                <div key={idx} className="bg-gradient-to-br from-rose-950/15 via-slate-900/35 to-slate-900/40 border border-rose-500/20 hover:border-rose-500/45 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-rose-950/10 rounded-lg p-3.5 space-y-2 transition-all duration-300 font-mono text-xs">
                  <div className="flex justify-between items-center">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-450">{item.platform}</span>
                    <span className="text-rose-400 font-bold bg-rose-950/35 px-2 py-0.5 rounded border border-rose-500/30">Failed CPA: {formatVND(item.failed_cpa)}</span>
                  </div>
                  <div className="text-[11px] text-slate-300 flex items-center gap-1.5">
                    <span>💀</span>
                    <span>Góc: <strong className="text-slate-100 font-semibold">{item.angle_name}</strong></span>
                  </div>
                  <p className="text-[11px] text-slate-400 bg-slate-950/80 p-2.5 rounded font-sans italic border-l-2 border-l-rose-500/60">&quot;{item.adapted_copy}&quot;</p>
                  <div className="text-[10px] text-rose-400 bg-rose-950/20 p-2 rounded border border-rose-500/20 leading-normal">
                    🚨 <strong>Lý do tắt:</strong> {item.reason_killed}
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-900/50 mt-1">
                    <span>👁️ Views: {item.spend > 0 ? Math.round(item.spend / 2500) : 0}</span>
                    <span>💸 Lãng phí: {formatVND(item.spend)}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-xs text-slate-500">Chưa có kịch bản nào bị tắt.</div>
            )}
          </div>
        </div>
      </div>

      {/* RAG ANTI-PATTERNS */}
      <div className="bg-slate-900/25 border border-slate-900 rounded-xl p-5 space-y-4">
        <div>
          <h3 className="text-xs font-extrabold text-rose-400 uppercase tracking-widest font-mono">🛡️ Kỷ Luật Tri Thức (RAG Anti-Patterns Visualizer)</h3>
          <p className="text-[11px] text-slate-500 font-sans">Tri thức lỗi từ CSDL pgvector được Agent học để tránh lặp lại sai lầm</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[300px] overflow-y-auto pr-1">
          {antiPatterns.length > 0 ? (
            antiPatterns.map((item, idx) => (
              <div key={idx} className="flex gap-3 bg-gradient-to-br from-rose-950/15 via-slate-900/20 to-slate-900/30 border border-rose-500/20 hover:border-rose-500/35 hover:-translate-y-0.5 rounded-lg p-3.5 transition-all duration-300 font-mono text-xs shadow-sm hover:shadow-rose-950/5">
                <span className="text-rose-400 text-sm">⚠️</span>
                <div className="space-y-1">
                  <div className="text-slate-200 font-sans leading-relaxed font-bold">{item.content}</div>
                  <div className="text-[10px] text-slate-500">Nguồn: {item.source_name}</div>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-2 text-center py-8 text-xs text-slate-500">Không tìm thấy tri thức lỗi nào trong RAG.</div>
          )}
        </div>
      </div>

      {/* API BILLING & TOKEN MONITORING */}
      <div className="bg-slate-900/25 border border-emerald-500/10 rounded-xl p-5 space-y-4">
        <div className="flex justify-between items-center border-b border-slate-900 pb-3">
          <div>
            <h3 className="text-xs font-extrabold text-emerald-400 uppercase tracking-widest font-mono">📊 Giám Sát Token & Chi Phí API Thời Gian Thực</h3>
            <p className="text-[11px] text-slate-500 font-sans">Theo dõi tiêu thụ token & chi phí SiliconFlow từ Audit Logs</p>
          </div>
          <span className="text-[10px] font-bold bg-slate-900 border border-slate-800 px-3 py-1 rounded text-slate-400 uppercase font-mono">BILLING ACTIVE</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-slate-950/60 border border-slate-900 rounded-lg p-3 text-center">
            <span className="text-[9px] font-mono text-slate-500 uppercase">Tổng Prompt Tokens</span>
            <div className="text-base font-extrabold text-indigo-400 font-mono mt-1">{billingStats.totalPrompt.toLocaleString()}</div>
          </div>
          <div className="bg-slate-950/60 border border-slate-900 rounded-lg p-3 text-center">
            <span className="text-[9px] font-mono text-slate-500 uppercase">Tổng Completion Tokens</span>
            <div className="text-base font-extrabold text-purple-400 font-mono mt-1">{billingStats.totalCompletion.toLocaleString()}</div>
          </div>
          <div className="bg-slate-950/60 border border-slate-900 rounded-lg p-3 text-center">
            <span className="text-[9px] font-mono text-slate-500 uppercase">Tổng Chi Phí USD</span>
            <div className="text-base font-extrabold text-emerald-400 font-mono mt-1">${billingStats.totalCost.toFixed(6)}</div>
          </div>
          <div className="bg-slate-950/60 border border-slate-900 rounded-lg p-3 text-center">
            <span className="text-[9px] font-mono text-slate-500 uppercase">Lượt Gọi API</span>
            <div className="text-base font-extrabold text-amber-400 font-mono mt-1">{billingStats.callsCount.toLocaleString()}</div>
          </div>
          <div className="bg-slate-950/60 border border-slate-900 rounded-lg p-3 text-center">
            <span className="text-[9px] font-mono text-slate-500 uppercase">Chi Phí / Call</span>
            <div className="text-base font-extrabold text-blue-400 font-mono mt-1">
              ${billingStats.callsCount > 0 ? (billingStats.totalCost / billingStats.callsCount).toFixed(6) : "0.000000"}
            </div>
          </div>
        </div>

        {/* Stacked Recharts Bar Chart */}
        <div className="h-[250px] w-full bg-slate-950/20 border border-slate-900/50 rounded-lg p-2 mt-4">
          {billingStats.chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={billingStats.chartData} margin={{ top: 10, right: 10, left: -10, bottom: 5 }}>
                <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" stroke="#64748b" fontSize={10} fontStyle="mono" tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} fontStyle="mono" tickLine={false} tickFormatter={value => value.toLocaleString()} />
                <RechartsTooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f1f5f9", fontSize: "11px", fontFamily: "monospace" }}
                  formatter={(value, name) => {
                    if (name === "Prompt Tokens" || name === "Completion Tokens") {
                      return [Number(value || 0).toLocaleString(), name];
                    }
                    return [value || "", name];
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "10px" }} />
                <Bar dataKey="Prompt Tokens" stackId="a" fill="rgba(129, 140, 248, 0.6)" stroke="rgba(129, 140, 248, 1)" strokeWidth={1} radius={[2, 2, 0, 0]} />
                <Bar dataKey="Completion Tokens" stackId="a" fill="rgba(168, 85, 247, 0.65)" stroke="rgba(168, 85, 247, 1)" strokeWidth={1} radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-500">Chưa ghi nhận cuộc gọi LLM nào</div>
          )}
        </div>
      </div>
    </div>
  );
}
