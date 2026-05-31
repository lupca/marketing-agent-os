/**
 * G-Agent Marketing OS v2.0 - CMO Strategic BI Dashboard Client Script
 * Focuses exclusively on business analytics, simulation metrics, and billing visual charts.
 * All system settings and third-party integrations are decoupled and managed inside /settings.
 */
(function() {
    // Shared Chart Variables
    let cpaChart = null;
    let funnelChart = null;
    let tokenChart = null;
    
    // Loaded Cache Metrics
    const globalChannelCPA = {};

    // DOM Elements Cache Store
    const DOM = {
        // Business Intelligence Panels
        kpisSection: null,
        fatigueContainer: null,
        fatigueList: null,
        winningBoard: null,
        killedBoard: null,
        antiPatternsList: null,
        btnRefreshMetrics: null,

        // What-If Simulation Controls
        simBudget: null,
        simPrice: null,
        simCost: null,
        budgetVal: null,
        priceVal: null,
        costVal: null,
        resMargin: null,
        resCpaTarget: null,
        resBreakeven: null,
        resRoas: null,
        advisorAllocations: null,

        // Token Usage Visualizers
        tokenTotalPrompt: null,
        tokenTotalCompletion: null,
        tokenTotalCost: null,
        tokenTotalCalls: null
    };

    /**
     * Cache all critical DOM elements.
     */
    function cacheDOM() {
        DOM.kpisSection = document.getElementById("kpis-section");
        DOM.fatigueContainer = document.getElementById("fatigue-container");
        DOM.fatigueList = document.getElementById("fatigue-list");
        DOM.winningBoard = document.getElementById("winning-board");
        DOM.killedBoard = document.getElementById("killed-board");
        DOM.antiPatternsList = document.getElementById("anti-patterns-list");
        DOM.btnRefreshMetrics = document.getElementById("btn-refresh-metrics");
        DOM.btnSyncMetrics = document.getElementById("btn-sync-metrics");

        DOM.simBudget = document.getElementById("sim-budget");
        DOM.simPrice = document.getElementById("sim-price");
        DOM.simCost = document.getElementById("sim-cost");
        DOM.budgetVal = document.getElementById("budget-val");
        DOM.priceVal = document.getElementById("price-val");
        DOM.costVal = document.getElementById("cost-val");
        DOM.resMargin = document.getElementById("res-margin");
        DOM.resCpaTarget = document.getElementById("res-cpa-target");
        DOM.resBreakeven = document.getElementById("res-breakeven");
        DOM.resRoas = document.getElementById("res-roas");
        DOM.advisorAllocations = document.getElementById("advisor-allocations");

        DOM.tokenTotalPrompt = document.getElementById("token-total-prompt");
        DOM.tokenTotalCompletion = document.getElementById("token-total-completion");
        DOM.tokenTotalCost = document.getElementById("token-total-cost");
        DOM.tokenTotalCalls = document.getElementById("token-total-calls");
    }

    /**
     * Unified API Request helper that enforces clean async error handling.
     */
    async function apiRequest(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Request to ${url} failed:`, error);
            throw error;
        }
    }

    /**
     * Formats numbers to local Vietnamese currency (VND).
     */
    function formatVND(value) {
        return new Intl.NumberFormat("vi-VN", { 
            style: "currency", 
            currency: "VND" 
        }).format(value).replace(",00 ₫", "đ");
    }

    // =========================================================================
    // A. CORE METRICS & ANALYTICS LOADING
    // =========================================================================

    /**
     * Main pipeline to retrieve and distribute metrics across the dashboard views.
     */
    async function fetchMetrics() {
        const btn = DOM.btnRefreshMetrics;
        let originalHTML = "";
        if (btn) {
            originalHTML = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = `<span class="spin" style="display:inline-block; margin-right:6px;">🔄</span> Đang cập nhật...`;
            btn.style.opacity = "0.7";
        }
        try {
            const data = await apiRequest("/api/dashboard/metrics");
            
            if (data.error) {
                alert("Lỗi tải báo cáo: " + data.error);
                return;
            }

            populateKPIs(data.kpis, data.anchor);
            populateFatigue(data.fatigue);
            populateBoards(data.winning_board, data.killed_board);
            populateAntiPatterns(data.anti_patterns);
            
            renderCPATrendChart(data.trend_chart);
            renderChannelFunnelChart(data.channel_data);
            loadTokenUsage(data.audit_logs);
            
            // Map loaded channel CPAs for budgeting sensitivity logic
            data.channel_data.forEach(channel => {
                globalChannelCPA[channel.name] = channel.cpa;
            });
            
            // Sync what-if defaults with server baseline config
            if (DOM.simPrice && DOM.simCost) {
                DOM.simPrice.value = data.anchor.price;
                DOM.simCost.value = data.anchor.cost;
            }
            
            runLocalSimulation();

            // Flash KPI grid and charts with a subtle glow for visual feedback
            const flashTargets = [DOM.kpisSection, document.getElementById("cpaTrendChart"), document.getElementById("channelFunnelChart")];
            flashTargets.forEach(el => {
                if (el) {
                    el.style.transition = "filter 0.2s ease, transform 0.2s ease";
                    el.style.filter = "brightness(1.2) contrast(1.05)";
                    el.style.transform = "scale(1.005)";
                    setTimeout(() => {
                        el.style.filter = "none";
                        el.style.transform = "none";
                    }, 300);
                }
            });

            showToast("Đã đồng bộ số liệu thời gian thực thành công!", "success");
        } catch (error) {
            alert("Không thể kết nối máy chủ để tải số liệu thời gian thực.");
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalHTML;
                btn.style.opacity = "";
            }
        }
    }

    /**
     * Populates primary KPI Cards with computed trend calculations.
     */
    function populateKPIs(kpis, anchor) {
        if (!DOM.kpisSection) return;

        const difference = kpis.blended_cac - anchor.target_cpa;
        const ratioPercent = Math.round((Math.abs(difference) / anchor.target_cpa) * 100);
        
        const targetCPAPercent = difference < 0 
            ? `-${ratioPercent}% so với target`
            : `+${ratioPercent}% so với target`;
        
        const trendClass = difference < 0 ? "up" : "down";
        const paybackMonths = kpis.cac_payback_period || 0;
        
        const healthColor = kpis.ltv_cac_health === "healthy" 
            ? "var(--color-success)" 
            : (kpis.ltv_cac_health === "warning" ? "var(--color-warning)" : "var(--color-danger)");

        const healthText = kpis.ltv_cac_health === "healthy" 
            ? "Lành Mạnh 🟢" 
            : (kpis.ltv_cac_health === "warning" ? "Cảnh Báo 🟡" : "Nguy Hiểm 🔴");

        DOM.kpisSection.innerHTML = `
            <div class="glass-panel kpi-card purple">
                <span class="kpi-title">Tổng Chi Phí Quảng Cáo</span>
                <span class="kpi-value">${formatVND(kpis.ad_spend)}</span>
                <div class="kpi-subtext">Đầu tư phân bổ ngân sách Q2</div>
            </div>
            <div class="glass-panel kpi-card teal">
                <span class="kpi-title">Đơn Hàng Thu Về (Leads)</span>
                <span class="kpi-value">${kpis.total_conversions} Leads</span>
                <div class="kpi-subtext">
                    <span class="trend-pill up">CTR tốt</span> của các Ads tự trị
                </div>
            </div>
            <div class="glass-panel kpi-card amber">
                <span class="kpi-title">Blended CAC (Chi phí/Lead)</span>
                <span class="kpi-value">${formatVND(kpis.blended_cac)}</span>
                <div class="kpi-subtext">
                    <span class="trend-pill ${trendClass}">${targetCPAPercent}</span>
                </div>
            </div>
            <div class="glass-panel kpi-card teal">
                <span class="kpi-title">LTV:CAC Health</span>
                <span class="kpi-value">${kpis.ltv_cac_ratio} x</span>
                <div class="kpi-subtext">
                    Trạng thái: 
                    <span style="font-weight: 800; color: ${healthColor}; text-transform: uppercase; letter-spacing: 0.5px;">
                        ${healthText}
                    </span>
                </div>
            </div>
            <div class="glass-panel kpi-card purple">
                <span class="kpi-title">Chu Kỳ Hòa Vốn (Payback)</span>
                <span class="kpi-value">${paybackMonths} tháng</span>
                <div class="kpi-subtext">Ước tính thời gian thu hồi vốn</div>
            </div>
            <div class="glass-panel kpi-card amber">
                <span class="kpi-title">Camp Hoạt Động (Active)</span>
                <span class="kpi-value">${kpis.active_campaigns} Chiến Dịch</span>
                <div class="kpi-subtext">Vận hành tự trị hoàn toàn</div>
            </div>
        `;
    }

    /**
     * Renders reactive Ad Creative Fatigue alert banner.
     */
    function populateFatigue(fatigueList) {
        if (!DOM.fatigueContainer || !DOM.fatigueList) return;

        if (!fatigueList || fatigueList.length === 0) {
            DOM.fatigueContainer.style.display = "none";
            return;
        }

        DOM.fatigueContainer.style.display = "block";
        DOM.fatigueList.innerHTML = "";

        fatigueList.forEach(item => {
            DOM.fatigueList.innerHTML += `
                <div class="fatigue-item">
                    👉 <strong>[${item.platform}] Góc sáng tạo "${item.angle_name}"</strong>: CPA 3 ngày qua đạt <strong>${formatVND(item.cpa_3d)}</strong> tăng gấp <strong>${item.ratio} lần</strong> so với CPA 7 ngày trung bình (${formatVND(item.cpa_7d)}). <em>Cần chuẩn bị đổi Angle sáng tạo mới!</em>
                </div>
            `;
        });
    }

    /**
     * Populates dynamic Double Boards (Winning creative variants vs Killed variants).
     */
    function populateBoards(winning, killed) {
        if (!DOM.winningBoard || !DOM.killedBoard) return;

        // Render Winning Creative Board
        if (!winning || winning.length === 0) {
            DOM.winningBoard.innerHTML = '<div style="color: var(--text-muted); font-size: 0.9rem; text-align: center; padding: 2rem;">Chưa có Angle nào được xếp hạng vinh danh.</div>';
        } else {
            DOM.winningBoard.innerHTML = winning.map(variant => `
                <div class="variant-card">
                    <div class="variant-meta">
                        <span class="platform-tag ${variant.platform.toLowerCase()}">${variant.platform}</span>
                        <span class="cpa-pill">CPA: ${formatVND(variant.cpa)}</span>
                    </div>
                    <div class="variant-angle">🧠 Góc: ${variant.angle_name}</div>
                    <div class="variant-copy">"${variant.adapted_copy}"</div>
                    <div class="variant-stats-row">
                        <span>👁️ ${variant.spend > 0 ? Math.round(variant.spend / 1000) : 0}k views</span>
                        <span>💰 Ngân sách tiêu: ${formatVND(variant.spend)}</span>
                        <span>🎯 Chuyển đổi: ${variant.conversions} leads</span>
                    </div>
                </div>
            `).join("");
        }

        // Render Defunct (Killed) Script Board
        if (!killed || killed.length === 0) {
            DOM.killedBoard.innerHTML = '<div style="color: var(--text-muted); font-size: 0.9rem; text-align: center; padding: 2rem;">Chưa có kịch bản nào bị Agent khai tử. Kênh ổn định!</div>';
        } else {
            DOM.killedBoard.innerHTML = killed.map(variant => `
                <div class="variant-card" style="border-color: rgba(239, 68, 68, 0.15)">
                    <div class="variant-meta">
                        <span class="platform-tag ${variant.platform.toLowerCase()}">${variant.platform}</span>
                        <span class="cpa-pill">Failed CPA: ${formatVND(variant.failed_cpa)}</span>
                    </div>
                    <div class="variant-angle">💔 Góc: ${variant.angle_name}</div>
                    <div class="variant-copy">"${variant.adapted_copy}"</div>
                    <div class="variant-reason">🚨 <strong>Lý do tắt:</strong> ${variant.reason_killed}</div>
                    <div class="variant-stats-row">
                        <span>👁️ Views: ${variant.spend > 0 ? Math.round(variant.spend / 2500) : 0}</span>
                        <span>💸 Ngân sách lãng phí: ${formatVND(variant.spend)}</span>
                    </div>
                </div>
            `).join("");
        }
    }

    /**
     * Renders flagged RAG failures (Anti-Patterns) pulled from RAG.
     */
    function populateAntiPatterns(ragList) {
        if (!DOM.antiPatternsList) return;

        if (!ragList || ragList.length === 0) {
            DOM.antiPatternsList.innerHTML = '<div style="color: var(--text-muted); font-size: 0.9rem; text-align: center; padding: 2rem;">Không tìm thấy tri thức lỗi nào trong RAG.</div>';
            return;
        }

        DOM.antiPatternsList.innerHTML = ragList.map((item, index) => `
            <div class="anti-pattern-item">
                <div class="anti-pattern-num">${index + 1}</div>
                <div>
                    <div class="anti-pattern-text">${item.content}</div>
                    <div class="anti-pattern-source">Nguồn tri thức: ${item.source_name}</div>
                </div>
            </div>
        `).join("");
    }

    // =========================================================================
    // B. CHART RENDERING CONFIGURATIONS (CHART.JS)
    // =========================================================================

    /**
     * Draws real-time learning curve (Blended CPA optimization progress) on line chart.
     */
    function renderCPATrendChart(trendData) {
        const canvas = document.getElementById("cpaTrendChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        
        if (cpaChart) {
            cpaChart.destroy();
        }
        
        cpaChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: trendData.labels,
                datasets: [{
                    label: "Blended CPA (VND)",
                    data: trendData.values,
                    borderColor: "#6366f1",
                    backgroundColor: "rgba(99, 102, 241, 0.05)",
                    borderWidth: 3,
                    pointBackgroundColor: "#818cf8",
                    pointBorderColor: "#ffffff",
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    fill: true,
                    tension: 0.25
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: {
                            color: "#9ca3af",
                            callback: value => formatVND(value).replace("đ", "")
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: "#9ca3af" }
                    }
                }
            }
        });
    }

    /**
     * Draws grouped channel conversion ratios on a grouped vertical bar chart.
     */
    function renderChannelFunnelChart(channelData) {
        const canvas = document.getElementById("channelFunnelChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        
        if (funnelChart) {
            funnelChart.destroy();
        }
        
        const labels = channelData.map(ch => ch.name);
        const viewsData = channelData.map(ch => ch.views);
        const clicksData = channelData.map(ch => ch.clicks * 10); // Scale clicks x10 for pleasing contrast
        const conversionsData = channelData.map(ch => ch.conversions * 100); // Scale conversions x100
        
        funnelChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Lượt Xem (Views)",
                        data: viewsData,
                        backgroundColor: "rgba(99, 102, 241, 0.65)",
                        borderRadius: 6
                    },
                    {
                        label: "Lượt Clicks (x10)",
                        data: clicksData,
                        backgroundColor: "rgba(245, 158, 11, 0.7)",
                        borderRadius: 6
                    },
                    {
                        label: " Leads Đơn (x100)",
                        data: conversionsData,
                        backgroundColor: "rgba(16, 185, 129, 0.75)",
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: "#f3f4f6", font: { family: "Outfit" } } }
                },
                scales: {
                    y: {
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: { color: "#9ca3af" }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: "#9ca3af" }
                    }
                }
            }
        });
    }

    // =========================================================================
    // C. REACTIVE WHAT-IF SENSITIVITY CALCULATOR
    // =========================================================================

    /**
     * Sensitivity modeling calculator triggered reactively upon any range change.
     */
    function runLocalSimulation() {
        if (!DOM.simBudget || !DOM.simPrice || !DOM.simCost) return;

        const budget = parseFloat(DOM.simBudget.value);
        const price = parseFloat(DOM.simPrice.value);
        const cost = parseFloat(DOM.simCost.value);
        
        DOM.budgetVal.innerText = formatVND(budget);
        DOM.priceVal.innerText = formatVND(price);
        DOM.costVal.innerText = formatVND(cost);
        
        const margin = price - cost;
        const targetCPATarget = margin * 0.3; // Safe CAC target capped at 30% margin
        const breakEvenLeads = margin > 0 ? (budget / margin) : 0;
        const expectedLeads = targetCPATarget > 0 ? (budget / targetCPATarget) : 0;
        const expectedRevenue = expectedLeads * price;
        const expectedROAS = budget > 0 ? (expectedRevenue / budget) : 0;
        
        DOM.resMargin.innerText = formatVND(margin);
        DOM.resCpaTarget.innerText = formatVND(targetCPATarget);
        DOM.resBreakeven.innerText = `${breakEvenLeads.toFixed(1)} Leads`;
        DOM.resRoas.innerText = `${expectedROAS.toFixed(2)} x`;
        
        runBudgetAllocationAdvisor(budget);
    }

    /**
     * Inverse CPA-Weighted allocation modeling. Allocates more budget to channels
     * performing with lower CPA baselines.
     */
    function runBudgetAllocationAdvisor(totalBudget) {
        if (!DOM.advisorAllocations) return;

        const cpas = {
            "Google": globalChannelCPA["Google"] || 680000.0,
            "Facebook": globalChannelCPA["Facebook"] || 720000.0,
            "TikTok": globalChannelCPA["TikTok"] || 880000.0
        };
        
        let sumInverse = 0.0;
        const weights = {};
        for (const channel in cpas) {
            const cpa = cpas[channel];
            if (cpa > 0) {
                const inverseWeight = 1.0 / cpa;
                weights[channel] = inverseWeight;
                sumInverse += inverseWeight;
            } else {
                weights[channel] = 0.0;
            }
        }
        
        DOM.advisorAllocations.innerHTML = "";
        
        for (const channel in cpas) {
            const percent = sumInverse > 0 ? (weights[channel] / sumInverse) : 0.33;
            const allocatedBudget = Math.round(totalBudget * percent);
            const expectedConversions = cpas[channel] > 0 ? (allocatedBudget / cpas[channel]) : 0;
            const progressClass = channel.toLowerCase();
            
            DOM.advisorAllocations.innerHTML += `
                <div class="allocation-bar-row">
                    <div class="alloc-label-row">
                        <span>💻 Kênh <strong>${channel}</strong> (CPA Lịch Sử: ${formatVND(cpas[channel])})</span>
                        <span style="color: #a5b4fc;">${(percent * 100).toFixed(1)}% | <strong>${formatVND(allocatedBudget)}</strong> (~${expectedConversions.toFixed(1)} Leads)</span>
                    </div>
                    <div class="alloc-progress-container">
                        <div class="alloc-progress-fill ${progressClass}" style="width: ${percent * 100}%"></div>
                    </div>
                </div>
            `;
        }
    }

    // =========================================================================
    // D. TOKEN USAGE & API AUDIT COSTING PLOTS
    // =========================================================================

    /**
     * Aggregates prompt/completion ratios and draws dynamic tokens audit chart.
     */
    function loadTokenUsage(rawLogs) {
        try {
            const auditLogs = (rawLogs || []).filter(
                log => log.action === "Execution Billing Audit" && log.metadata
            );
            
            if (auditLogs.length === 0) {
                DOM.tokenTotalPrompt.textContent = "0";
                DOM.tokenTotalCompletion.textContent = "0";
                DOM.tokenTotalCost.textContent = "$0.000000";
                DOM.tokenTotalCalls.textContent = "0";
                renderTokenChart([], [], []);
                return;
            }
            
            let totalPrompt = 0;
            let totalCompletion = 0;
            let totalCost = 0;
            
            const chartLabels = [];
            const chartPromptData = [];
            const chartCompletionData = [];
            
            auditLogs.forEach((log, index) => {
                const metadata = typeof log.metadata === "string" ? JSON.parse(log.metadata) : log.metadata;
                const promptTokens = metadata.prompt_tokens || 0;
                const completionTokens = metadata.completion_tokens || 0;
                const cost = metadata.total_cost_usd || 0;
                
                totalPrompt += promptTokens;
                totalCompletion += completionTokens;
                totalCost += cost;
                
                chartLabels.push(`#${index + 1}`);
                chartPromptData.push(promptTokens);
                chartCompletionData.push(completionTokens);
            });
            
            DOM.tokenTotalPrompt.textContent = totalPrompt.toLocaleString();
            DOM.tokenTotalCompletion.textContent = totalCompletion.toLocaleString();
            DOM.tokenTotalCost.textContent = "$" + totalCost.toFixed(6);
            DOM.tokenTotalCalls.textContent = auditLogs.length.toLocaleString();
            
            renderTokenChart(chartLabels, chartPromptData, chartCompletionData);
        } catch (error) {
            console.error("Error loading token usage visual logs:", error);
            DOM.tokenTotalPrompt.textContent = "N/A";
            DOM.tokenTotalCompletion.textContent = "N/A";
            DOM.tokenTotalCost.textContent = "N/A";
            DOM.tokenTotalCalls.textContent = "N/A";
        }
    }

    /**
     * Configures stacked token usage bars layout via Chart.js.
     */
    function renderTokenChart(labels, promptData, completionData) {
        const canvas = document.getElementById("tokenUsageChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        
        if (tokenChart) {
            tokenChart.destroy();
        }
        
        tokenChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels.length > 0 ? labels : ["Chưa có dữ liệu"],
                datasets: [
                    {
                        label: "Prompt Tokens",
                        data: promptData.length > 0 ? promptData : [0],
                        backgroundColor: "rgba(129, 140, 248, 0.6)",
                        borderColor: "rgba(129, 140, 248, 1)",
                        borderWidth: 1,
                        borderRadius: 4
                    },
                    {
                        label: "Completion Tokens",
                        data: completionData.length > 0 ? completionData : [0],
                        backgroundColor: "rgba(167, 139, 250, 0.6)",
                        borderColor: "rgba(167, 139, 250, 1)",
                        borderWidth: 1,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: "#9ca3af",
                            font: { family: "Outfit", size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: "rgba(18, 18, 29, 0.95)",
                        titleFont: { family: "Outfit", size: 13 },
                        bodyFont: { family: "Outfit", size: 12 },
                        borderColor: "rgba(129, 140, 248, 0.3)",
                        borderWidth: 1,
                        callbacks: {
                            afterBody: context => {
                                const index = context[0].dataIndex;
                                const prompt = promptData[index] || 0;
                                const completion = completionData[index] || 0;
                                const estimatedCost = (prompt * 0.00020 / 1000) + (completion * 0.00160 / 1000);
                                return "💰 Chi phí: $" + estimatedCost.toFixed(6);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        ticks: { color: "#9ca3af", font: { family: "Outfit", size: 11 } },
                        grid: { color: "rgba(255,255,255,0.04)" }
                    },
                    y: {
                        stacked: true,
                        ticks: {
                            color: "#9ca3af",
                            font: { family: "Outfit", size: 11 },
                            callback: value => value.toLocaleString()
                        },
                        grid: { color: "rgba(255,255,255,0.04)" }
                    }
                }
            }
        });
    }

    /**
     * Renders standard floating toast notification.
     */
    function showToast(message, type = "success") {
        let container = document.getElementById("toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "toast-container";
            container.style.position = "fixed";
            container.style.bottom = "24px";
            container.style.right = "24px";
            container.style.zIndex = "9999";
            container.style.display = "flex";
            container.style.flexDirection = "column";
            container.style.gap = "8px";
            document.body.appendChild(container);
        }
        
        const toast = document.createElement("div");
        toast.className = `toast-item toast-${type}`;
        toast.style.background = "rgba(18, 18, 29, 0.9)";
        toast.style.backdropFilter = "blur(12px)";
        toast.style.webkitBackdropFilter = "blur(12px)";
        toast.style.border = "1px solid rgba(255, 255, 255, 0.08)";
        toast.style.boxShadow = "0 8px 32px rgba(0, 0, 0, 0.5)";
        toast.style.padding = "12px 20px";
        toast.style.borderRadius = "10px";
        toast.style.color = "#fff";
        toast.style.fontFamily = "var(--font-family, 'Outfit', sans-serif)";
        toast.style.fontSize = "0.85rem";
        toast.style.fontWeight = "500";
        toast.style.minWidth = "280px";
        toast.style.display = "flex";
        toast.style.alignItems = "center";
        toast.style.gap = "10px";
        toast.style.opacity = "0";
        toast.style.transform = "translateY(20px)";
        toast.style.transition = "all 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275)";
        
        let icon = "🔔";
        if (type === "success") {
            icon = "✅";
            toast.style.borderLeft = "4px solid var(--color-success, #10b981)";
        } else if (type === "error") {
            icon = "❌";
            toast.style.borderLeft = "4px solid var(--color-danger, #ef4444)";
        }
        
        toast.innerHTML = `<span style="font-size:1.1rem;">${icon}</span> <span>${message}</span>`;
        container.appendChild(toast);
        
        // Force reflow
        toast.offsetHeight;
        
        toast.style.opacity = "1";
        toast.style.transform = "translateY(0)";
        
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(-20px)";
            setTimeout(() => {
                toast.remove();
            }, 350);
        }, 4000);
    }

    // =========================================================================
    // E. INITIALIZATION & METRICS BOOTSTRAP
    // =========================================================================

    /**
     * Standard DOMContentLoaded routing setup.
     */
    function init() {
        cacheDOM();
        
        // Fetch baseline data
        fetchMetrics();

        // 1. Programmatic What-If range sliders event binding
        const sliders = ["sim-budget", "sim-price", "sim-cost"];
        sliders.forEach(id => {
            const slider = document.getElementById(id);
            if (slider) {
                slider.addEventListener("input", runLocalSimulation);
            }
        });

        // 2. Main Dashboard panel header buttons binding
        if (DOM.btnRefreshMetrics) {
            DOM.btnRefreshMetrics.removeAttribute("onclick");
            DOM.btnRefreshMetrics.addEventListener("click", fetchMetrics);
        }

        if (DOM.btnSyncMetrics) {
            DOM.btnSyncMetrics.addEventListener("click", handleSyncMetrics);
        }
    }

    /**
     * Handlers for Sync Metrics
     */
    async function handleSyncMetrics() {
        if (!DOM.btnSyncMetrics) return;
        
        const originalText = DOM.btnSyncMetrics.innerHTML;
        DOM.btnSyncMetrics.innerHTML = "⏳ Đang đồng bộ...";
        DOM.btnSyncMetrics.disabled = true;
        
        try {
            const data = await apiRequest("/api/dashboard/sync-metrics", "POST");
            if (data) {
                alert(data.message || "Đã gửi yêu cầu đồng bộ thành công!");
            }
        } finally {
            DOM.btnSyncMetrics.innerHTML = originalText;
            DOM.btnSyncMetrics.disabled = false;
        }
    }

    // Register Initialization
    window.addEventListener("DOMContentLoaded", init);

    // Expose minimum required handlers globally
    window.fetchMetrics = fetchMetrics;
})();
