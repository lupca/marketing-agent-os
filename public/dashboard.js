/**
 * G-Agent Marketing OS v2.0 - CMO Strategic BI Dashboard Core Interactivity Script
 * Structured under strict Clean Code Guidelines:
 * - Separation of Concerns: Scoped inside an IIFE to avoid global pollution.
 * - Single Responsibility: Core modules broken down into clear, small functions.
 * - DRY (Don't Repeat Yourself): Unified API wrapper with consistent error handling.
 * - Programmatic Event Handlers: Dynamically binds listeners instead of inline HTML hooks.
 */

(() => {
    "use strict";

    // =========================================================================
    // 1. STATE & GLOBAL CONFIGURATION
    // =========================================================================
    let cpaChart = null;
    let funnelChart = null;
    let tokenChart = null;
    let loadedModels = [];
    
    // Store channel CPAs to calculate budget simulator weighting on-the-fly
    const globalChannelCPA = {}; 

    // Active filters for the Models Library
    const activeFilters = {
        category: new Set(),
        tags: new Set(),
        series: new Set(),
        context: new Set(),
        size: new Set(),
        release: new Set()
    };

    // DOM Cache Object to avoid repeated document lookups
    const DOM = {
        // Dashboard Core
        kpisSection: null,
        fatigueContainer: null,
        fatigueList: null,
        winningBoard: null,
        killedBoard: null,
        antiPatternsList: null,
        btnRefreshMetrics: null,

        // Range Sliders for Simulator
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

        // Core AI Settings Inputs
        settingAiModel: null,
        customModelContainer: null,
        settingCustomAiModel: null,
        settingTemp: null,
        settingTempVal: null,
        settingContext: null,
        settingContextVal: null,
        settingRecursion: null,
        settingRecursionVal: null,
        settingRerankMode: null,
        settingApiKey: null,
        settingApiUrl: null,
        settingEnableThinking: null,
        btnSaveSettings: null,
        settingsStatus: null,

        // Token Usage Visualizers
        tokenTotalPrompt: null,
        tokenTotalCompletion: null,
        tokenTotalCost: null,
        tokenTotalCalls: null,

        // Models Library Layout
        modelsOverlay: null,
        modelsSidebar: null,
        modelsGrid: null,
        modelSearchQuery: null,
        btnOpenModels: null,
        btnCloseModels: null,
        btnToggleSidebar: null,
        toggleFilterText: null,

        // Model Form Modal
        modelFormModal: null,
        modalFormTitle: null,
        formModelUuid: null,
        formModelName: null,
        formModelId: null,
        formModelProvider: null,
        formModelCategory: null,
        formModelSeries: null,
        formModelContext: null,
        formModelSize: null,
        formModelBadge: null,
        formModelTags: null,
        formModelApiUrl: null,
        formModelApiKey: null,
        formModelDescription: null,
        btnNewModel: null,
        btnSaveForm: null,
        btnCloseForm: null
    };

    // =========================================================================
    // 2. DRY UTILITY FUNCTIONS & API WRAPPERS
    // =========================================================================

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
        DOM.btnRefreshMetrics = document.querySelector(".refresh-btn[onclick='fetchMetrics()']") || document.querySelector(".refresh-btn");

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

        DOM.settingAiModel = document.getElementById("setting-ai-model");
        DOM.customModelContainer = document.getElementById("custom-model-container");
        DOM.settingCustomAiModel = document.getElementById("setting-custom-ai-model");
        DOM.settingTemp = document.getElementById("setting-temp");
        DOM.settingTempVal = document.getElementById("setting-temp-val");
        DOM.settingContext = document.getElementById("setting-context");
        DOM.settingContextVal = document.getElementById("setting-context-val");
        DOM.settingRecursion = document.getElementById("setting-recursion");
        DOM.settingRecursionVal = document.getElementById("setting-recursion-val");
        DOM.settingRerankMode = document.getElementById("setting-rerank-mode");
        DOM.settingApiKey = document.getElementById("setting-api-key");
        DOM.settingApiUrl = document.getElementById("setting-api-url");
        DOM.settingEnableThinking = document.getElementById("setting-enable-thinking");
        DOM.btnSaveSettings = document.querySelector("button[onclick='saveAISettings()']");
        DOM.settingsStatus = document.getElementById("settings-status");

        DOM.tokenTotalPrompt = document.getElementById("token-total-prompt");
        DOM.tokenTotalCompletion = document.getElementById("token-total-completion");
        DOM.tokenTotalCost = document.getElementById("token-total-cost");
        DOM.tokenTotalCalls = document.getElementById("token-total-calls");

        DOM.modelsOverlay = document.getElementById("models-management-overlay");
        DOM.modelsSidebar = document.getElementById("models-sidebar");
        DOM.modelsGrid = document.getElementById("models-grid");
        DOM.modelSearchQuery = document.getElementById("model-search-query");
        DOM.btnOpenModels = document.querySelector("button[onclick='openModelsOverlay()']");
        DOM.btnCloseModels = document.querySelector("button[onclick='closeModelsOverlay()']");
        DOM.btnToggleSidebar = document.getElementById("toggle-filter-btn");
        DOM.toggleFilterText = document.getElementById("toggle-filter-text");

        DOM.modelFormModal = document.getElementById("model-form-modal");
        DOM.modalFormTitle = document.getElementById("modal-form-title");
        DOM.formModelUuid = document.getElementById("form-model-uuid");
        DOM.formModelName = document.getElementById("form-model-name");
        DOM.formModelId = document.getElementById("form-model-id");
        DOM.formModelProvider = document.getElementById("form-model-provider");
        DOM.formModelCategory = document.getElementById("form-model-category");
        DOM.formModelSeries = document.getElementById("form-model-series");
        DOM.formModelContext = document.getElementById("form-model-context");
        DOM.formModelSize = document.getElementById("form-model-size");
        DOM.formModelBadge = document.getElementById("form-model-badge");
        DOM.formModelTags = document.getElementById("form-model-tags");
        DOM.formModelApiUrl = document.getElementById("form-model-api-url");
        DOM.formModelApiKey = document.getElementById("form-model-api-key");
        DOM.formModelDescription = document.getElementById("form-model-description");
        DOM.btnNewModel = document.querySelector("button[onclick='openNewModelModal()']");
        DOM.btnSaveForm = document.querySelector("button[onclick='saveModelForm()']");
        DOM.btnCloseForm = document.querySelector("button[onclick='closeModelModal()']");
    }

    /**
     * Unified, robust API Request helper that enforces clean async error handling.
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
    // 3. CORE METRICS & ANALYTICS LOADING
    // =========================================================================

    /**
     * Main pipeline to retrieve and distribute metrics across the dashboard views.
     */
    async function fetchMetrics() {
        try {
            const data = await apiRequest("/api/dashboard/metrics");
            
            if (data.error) {
                showModalAlert("Lỗi tải báo cáo: " + data.error, "error");
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
        } catch (error) {
            showModalAlert("Không thể kết nối máy chủ để tải số liệu thời gian thực.", "error");
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
            DOM.killedBoard.innerHTML = '<div style="color: var(--text-muted); font-size: 0.9rem; text-align: center; padding: 2rem;">Chưa có kịch bản nào bị Agent khai tử. Hệ thống an toàn!</div>';
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
     * Renders flagged RAG failures (Anti-Patterns) pulled from postgres pgvector.
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
    // 4. CHART RENDERING CONFIGURATIONS (CHART.JS)
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
        const clicksData = channelData.map(ch => ch.clicks * 10); // Scale up clicks x10 for pleasant visual contrast
        const conversionsData = channelData.map(ch => ch.conversions * 100); // Scale leads x100 for visual stacking
        
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
    // 5. REACTIVE WHAT-IF SENSITIVITY CALCULATOR
    // =========================================================================

    /**
     * Sensitivity modeling calculator triggered reactively upon any range change.
     */
    function runLocalSimulation() {
        if (!DOM.simBudget || !DOM.simPrice || !DOM.simCost) return;

        const budget = parseFloat(DOM.simBudget.value);
        const price = parseFloat(DOM.simPrice.value);
        const cost = parseFloat(DOM.simCost.value);
        
        // Dynamic label sync
        DOM.budgetVal.innerText = formatVND(budget);
        DOM.priceVal.innerText = formatVND(price);
        DOM.costVal.innerText = formatVND(cost);
        
        // Sensitive parameters calculations
        const margin = price - cost;
        const targetCPATarget = margin * 0.3; // Safe CAC target capped at 30% margin
        const breakEvenLeads = margin > 0 ? (budget / margin) : 0;
        const expectedLeads = targetCPATarget > 0 ? (budget / targetCPATarget) : 0;
        const expectedRevenue = expectedLeads * price;
        const expectedROAS = budget > 0 ? (expectedRevenue / budget) : 0;
        
        // Update DOM values
        DOM.resMargin.innerText = formatVND(margin);
        DOM.resCpaTarget.innerText = formatVND(targetCPATarget);
        DOM.resBreakeven.innerText = `${breakEvenLeads.toFixed(1)} Leads`;
        DOM.resRoas.innerText = `${expectedROAS.toFixed(2)} x`;
        
        // Dynamically compute AI budgeting advisor metrics
        runBudgetAllocationAdvisor(budget);
    }

    /**
     * Inverse CPA-Weighted allocation modeling. Allocates more budget to channels
     * performing with lower CPA baselines.
     */
    function runBudgetAllocationAdvisor(totalBudget) {
        if (!DOM.advisorAllocations) return;

        // Retrieve latest channel metrics or configure fallbacks
        const cpas = {
            "Google": globalChannelCPA["Google"] || 680000.0,
            "Facebook": globalChannelCPA["Facebook"] || 720000.0,
            "TikTok": globalChannelCPA["TikTok"] || 880000.0
        };
        
        // Compute total inverse weighting sum
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
    // 6. SYSTEM AI CONFIGURATION MANAGEMENT
    // =========================================================================

    /**
     * Toggles optional custom input rendering depending on LLM Model drop-down selection.
     */
    function toggleCustomModelInput() {
        if (!DOM.settingAiModel || !DOM.customModelContainer || !DOM.settingCustomAiModel) return;

        const selection = DOM.settingAiModel.value;
        if (selection === "custom") {
            DOM.customModelContainer.style.display = "block";
            DOM.settingCustomAiModel.focus();
        } else {
            DOM.customModelContainer.style.display = "none";
        }
    }

    /**
     * Retrieve running LLM system configuration metrics dynamically from postgres API.
     */
    async function loadAISettings() {
        try {
            const settings = await apiRequest("/api/workspace/settings");
            
            if (settings.ai_model) {
                const predefined = [
                    "Qwen/Qwen3.6-35B-A3B",
                    "Qwen/Qwen3-32B",
                    "deepseek-ai/DeepSeek-V3",
                    "Qwen/Qwen2.5-7B-Instruct"
                ];
                
                if (predefined.includes(settings.ai_model)) {
                    DOM.settingAiModel.value = settings.ai_model;
                    DOM.customModelContainer.style.display = "none";
                } else {
                    DOM.settingAiModel.value = "custom";
                    DOM.customModelContainer.style.display = "block";
                    DOM.settingCustomAiModel.value = settings.ai_model;
                }
            }
            
            if (settings.temperature !== undefined) {
                DOM.settingTemp.value = settings.temperature;
                DOM.settingTempVal.innerText = parseFloat(settings.temperature).toFixed(2);
            }
            if (settings.max_tokens) {
                DOM.settingContext.value = settings.max_tokens;
                DOM.settingContextVal.innerText = Number(settings.max_tokens).toLocaleString();
            }
            if (settings.recursion_limit) {
                DOM.settingRecursion.value = settings.recursion_limit;
                DOM.settingRecursionVal.innerText = settings.recursion_limit;
            }
            if (settings.reranker_mode) {
                DOM.settingRerankMode.value = settings.reranker_mode;
            }
            if (settings.siliconflow_api_key) {
                DOM.settingApiKey.value = settings.siliconflow_api_key;
            }
            if (settings.ai_api_url) {
                DOM.settingApiUrl.value = settings.ai_api_url;
            }
            if (settings.enable_thinking !== undefined) {
                DOM.settingEnableThinking.checked = settings.enable_thinking;
            }
        } catch (error) {
            console.error("Failed to load global workspace settings:", error);
        }
    }

    /**
     * Validates and posts modified LLM settings parameters payload back to postgres.
     */
    async function saveAISettings() {
        if (!DOM.settingsStatus) return;

        const selection = DOM.settingAiModel.value;
        const modelId = selection === "custom" 
            ? DOM.settingCustomAiModel.value.trim() 
            : selection;
            
        if (!modelId) {
            updateSettingsStatus("❌ Lỗi: Vui lòng nhập hoặc chọn tên mô hình AI!", "error");
            return;
        }

        const payload = {
            ai_model: modelId,
            temperature: parseFloat(DOM.settingTemp.value),
            max_tokens: parseInt(DOM.settingContext.value),
            recursion_limit: parseInt(DOM.settingRecursion.value),
            reranker_mode: DOM.settingRerankMode.value,
            siliconflow_api_key: DOM.settingApiKey.value,
            ai_api_url: DOM.settingApiUrl.value.trim(),
            enable_thinking: DOM.settingEnableThinking.checked
        };

        updateSettingsStatus("⏳ Đang lưu cấu hình...", "info");

        try {
            const data = await apiRequest("/api/workspace/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (data.status === "success") {
                updateSettingsStatus("✅ Lưu thành công! Các Agent sẽ lập tức chạy trên cấu hình mới.", "success");
            } else {
                updateSettingsStatus("❌ Lỗi: " + (data.message || "Không rõ nguyên nhân"), "error");
            }
        } catch (error) {
            updateSettingsStatus("❌ Lỗi kết nối: " + error.message, "error");
        }
    }

    /**
     * Renders settings visual feedbacks.
     */
    function updateSettingsStatus(message, type) {
        if (!DOM.settingsStatus) return;

        DOM.settingsStatus.style.display = "block";
        DOM.settingsStatus.textContent = message;

        if (type === "success") {
            DOM.settingsStatus.style.background = "rgba(16,185,129,0.15)";
            DOM.settingsStatus.style.color = "var(--color-success)";
        } else if (type === "error") {
            DOM.settingsStatus.style.background = "rgba(239,68,68,0.15)";
            DOM.settingsStatus.style.color = "var(--color-danger)";
        } else {
            DOM.settingsStatus.style.background = "rgba(99,102,241,0.15)";
            DOM.settingsStatus.style.color = "#818cf8";
        }

        if (type !== "info") {
            setTimeout(() => { 
                DOM.settingsStatus.style.display = "none"; 
            }, 4000);
        }
    }

    // =========================================================================
    // 7. TOKEN USAGE & API AUDIT COSTING PLOTS
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
     * Configures high-end visual stacked token usage bars layout via Chart.js.
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

    // =========================================================================
    // 8. HIGH-END MODELS LIBRARY OVERLAY MANAGEMENT (CRUD & ADVANCED FILTERS)
    // =========================================================================

    /**
     * Triggers models library sliding display overlay.
     */
    function openModelsOverlay() {
        if (!DOM.modelsOverlay) return;
        DOM.modelsOverlay.classList.add("active");
        document.body.style.overflow = "hidden"; // Clip background scrolling
        fetchModelsList();
    }

    /**
     * Closes models library sliding display overlay.
     */
    function closeModelsOverlay() {
        if (!DOM.modelsOverlay) return;
        DOM.modelsOverlay.classList.remove("active");
        document.body.style.overflow = "auto";
    }

    /**
     * Toggle models filter left-sidebar layout.
     */
    function toggleSidebar() {
        if (!DOM.modelsSidebar || !DOM.toggleFilterText) return;

        DOM.modelsSidebar.classList.toggle("collapsed");
        if (DOM.modelsSidebar.classList.contains("collapsed")) {
            DOM.toggleFilterText.innerText = "Show Filters";
        } else {
            DOM.toggleFilterText.innerText = "Hide Filters";
        }
    }

    /**
     * Retrieve all available workspace models library.
     */
    async function fetchModelsList() {
        if (!DOM.modelsGrid) return;
        DOM.modelsGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 3rem; font-size: 1.1rem;">🔄 Đang tải thư viện mô hình từ cơ sở dữ liệu...</div>';
        
        try {
            const response = await apiRequest("/api/workspace/models");
            if (response.status === "success") {
                loadedModels = response.data;
                renderModelsGrid();
                setupFilterListeners();
            } else {
                DOM.modelsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--color-danger); padding: 3rem; font-size: 1.1rem;">❌ Lỗi khi tải mô hình: ${response.error || "Unknown"}</div>`;
            }
        } catch (error) {
            DOM.modelsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--color-danger); padding: 3rem; font-size: 1.1rem;">❌ Lỗi kết nối máy chủ.</div>`;
        }
    }

    /**
     * Configures interactive filter pill listeners.
     */
    function setupFilterListeners() {
        const pills = document.querySelectorAll(".models-sidebar .filter-pill");
        
        // Safely wipe old listeners via cloning
        pills.forEach(pill => {
            const freshPill = pill.cloneNode(true);
            pill.parentNode.replaceChild(freshPill, pill);
        });

        // Re-bind fresh click listener logic
        document.querySelectorAll(".models-sidebar .filter-pill").forEach(pill => {
            const filterGroup = pill.parentNode.id.replace("filter-", "");
            
            pill.addEventListener("click", () => {
                pill.classList.toggle("active");
                const value = pill.getAttribute("data-value");
                
                if (pill.classList.contains("active")) {
                    activeFilters[filterGroup].add(value);
                } else {
                    activeFilters[filterGroup].delete(value);
                }
                renderModelsGrid();
            });
        });
    }

    /**
     * Clears an active filter set. Expose to window.
     */
    function clearFilter(group) {
        if (!activeFilters[group]) return;

        activeFilters[group].clear();
        document.querySelectorAll(`#filter-${group} .filter-pill`).forEach(pill => {
            pill.classList.remove("active");
        });
        renderModelsGrid();
    }

    /**
     * Filter models collection and updates library grid UI dynamically.
     */
    function renderModelsGrid() {
        if (!DOM.modelsGrid) return;

        const searchQuery = DOM.modelSearchQuery ? DOM.modelSearchQuery.value.toLowerCase().trim() : "";
        const activeModel = DOM.settingAiModel ? DOM.settingAiModel.value : "";
        const activeCustomModel = DOM.settingCustomAiModel ? DOM.settingCustomAiModel.value.trim() : "";
        
        const currentActiveModelId = activeModel === "custom" ? activeCustomModel : activeModel;

        const filtered = loadedModels.filter(model => {
            // Apply Search Query matching
            if (searchQuery) {
                const matches = model.name.toLowerCase().includes(searchQuery) ||
                                model.model_id.toLowerCase().includes(searchQuery) ||
                                (model.description && model.description.toLowerCase().includes(searchQuery));
                if (!matches) return false;
            }
            
            // Apply Category matching
            if (activeFilters.category.size > 0 && !activeFilters.category.has(model.category)) {
                return false;
            }
            
            // Apply Tag list matching
            if (activeFilters.tags.size > 0) {
                const tagFound = model.tags.some(tag => activeFilters.tags.has(tag));
                if (!tagFound) return false;
            }
            
            // Apply Series matching
            if (activeFilters.series.size > 0 && !activeFilters.series.has(model.series)) {
                return false;
            }
            
            // Apply Context window matching
            if (activeFilters.context.size > 0 && !activeFilters.context.has(model.context_window)) {
                return false;
            }
            
            // Apply Size parameters matching
            if (activeFilters.size.size > 0 && !activeFilters.size.has(model.model_size)) {
                return false;
            }

            return true;
        });

        if (filtered.length === 0) {
            DOM.modelsGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 4rem; font-size: 1.1rem;">🔍 Không tìm thấy mô hình nào khớp với bộ lọc hiện tại.</div>';
            return;
        }

        DOM.modelsGrid.innerHTML = filtered.map(model => {
            const isModelActivated = (model.model_id === currentActiveModelId);
            
            const badgesHtml = model.tags.map((tag, idx) => {
                const classes = ["indigo", "purple", "pink", "teal", "amber", "emerald"];
                const selectClass = classes[idx % classes.length];
                return `<span class="model-badge ${selectClass}">${tag}</span>`;
            }).join(" ");

            const avatarChar = model.name.charAt(0);
            const activeCardClass = isModelActivated ? "active-model" : "";
            
            const activationAction = isModelActivated 
                ? '<span class="status-badge" style="background: rgba(16,185,129,0.15); border-color: rgba(16,185,129,0.3); color: var(--color-success); font-size: 0.75rem; text-transform: uppercase;">Activated</span>'
                : `<button class="chat-nav-btn" onclick="activateModel('${model.model_id}')" style="background: rgba(255,255,255,0.03); border-color: var(--border-glass); padding: 6px 12px; font-size: 0.75rem;">✅ Activate</button>`;

            const specialGlowBadge = model.special_badge 
                ? `<span class="glow-tag">${model.special_badge}</span>` 
                : (model.is_new ? '<span class="glow-tag">New</span>' : "");

            return `
                <div class="glass-panel model-card ${activeCardClass}" id="model-card-${model.id}">
                    ${specialGlowBadge}
                    <div>
                        <div class="model-card-header">
                            <div class="model-avatar">${avatarChar}</div>
                            <div class="model-identity">
                                <h3 class="model-card-title" title="${model.name}">${model.name}</h3>
                                <span class="model-card-provider">${model.provider}</span>
                            </div>
                        </div>
                        <p class="model-card-desc" style="margin-top: 10px;">${model.description || "Không có mô tả cho mô hình này."}</p>
                    </div>
                    
                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <div class="model-card-tags">${badgesHtml}</div>
                        <div class="model-card-actions">
                            <div class="card-left-actions">
                                <button class="refresh-btn" onclick="openEditModelModal('${model.id}')" style="background: rgba(255,255,255,0.03); border-color: var(--border-glass); padding: 6px 12px; font-size: 0.75rem; box-shadow: none;">✏️ Edit</button>
                                <button class="refresh-btn" onclick="deleteModel('${model.id}')" style="background: rgba(239,68,68,0.05); border-color: rgba(239,68,68,0.2); color: var(--color-danger); padding: 6px 12px; font-size: 0.75rem; box-shadow: none;" onmouseover="this.style.background='rgba(239,68,68,0.1)'" onmouseout="this.style.background='rgba(239,68,68,0.05)'">❌ Delete</button>
                            </div>
                            ${activationAction}
                        </div>
                    </div>
                </div>
            `;
        }).join("");
    }

    /**
     * Activates selected model configurations inside the workspace parameters.
     */
    function activateModel(modelId) {
        if (!DOM.settingAiModel || !DOM.settingCustomAiModel) return;

        const predefined = [
            "Qwen/Qwen3.6-35B-A3B", 
            "Qwen/Qwen3-32B", 
            "deepseek-ai/DeepSeek-V3", 
            "Qwen/Qwen2.5-7B-Instruct"
        ];
        
        if (predefined.includes(modelId)) {
            DOM.settingAiModel.value = modelId;
            DOM.customModelContainer.style.display = "none";
        } else {
            DOM.settingAiModel.value = "custom";
            DOM.customModelContainer.style.display = "block";
            DOM.settingCustomAiModel.value = modelId;
        }

        // Auto sync corresponding API Key and Base URL parameters
        const model = loadedModels.find(m => m.model_id === modelId);
        if (model) {
            DOM.settingApiUrl.value = model.api_url || "";
            DOM.settingApiKey.value = model.api_key || "";
        }
        
        showSettingsStatus("Kích hoạt mô hình " + modelId + " thành công! Cổng kết nối & API Key đã được đồng bộ, hãy lưu lại cấu hình.", "success");
        renderModelsGrid();
        
        // Graceful automatic overlay closing with smooth focusing scroll
        setTimeout(() => {
            closeModelsOverlay();
            
            DOM.settingAiModel.scrollIntoView({ behavior: "smooth" });
            
            // Neon Glow visual feedback highlight on parameters panel
            const panel = DOM.settingAiModel.closest(".glass-panel");
            if (panel) {
                panel.style.borderColor = "rgba(99,102,241,0.8)";
                panel.style.boxShadow = "0 0 30px rgba(99,102,241,0.2)";
                setTimeout(() => {
                    panel.style.borderColor = "rgba(129, 140, 248, 0.2)";
                    panel.style.boxShadow = "none";
                }, 2000);
            }
        }, 500);
    }

    /**
     * Visual status feedback message beneath main AI configuration cards.
     */
    function showSettingsStatus(message, type) {
        if (!DOM.settingsStatus) return;

        DOM.settingsStatus.style.display = "block";
        DOM.settingsStatus.innerText = message;

        if (type === "success") {
            DOM.settingsStatus.style.background = "rgba(16, 185, 129, 0.15)";
            DOM.settingsStatus.style.border = "1px solid rgba(16, 185, 129, 0.3)";
            DOM.settingsStatus.style.color = "var(--color-success)";
        } else {
            DOM.settingsStatus.style.background = "rgba(239, 68, 68, 0.15)";
            DOM.settingsStatus.style.border = "1px solid rgba(239, 68, 68, 0.3)";
            DOM.settingsStatus.style.color = "var(--color-danger)";
        }

        setTimeout(() => { 
            DOM.settingsStatus.style.display = "none"; 
        }, 5000);
    }

    // =========================================================================
    // 9. CRUD MODEL CREATING / EDITING FORMS
    // =========================================================================

    /**
     * Initializes blank Add New Model modal parameters.
     */
    function openNewModelModal() {
        if (!DOM.modelFormModal || !DOM.modalFormTitle) return;

        DOM.modalFormTitle.innerText = "➕ Thêm Mô Hình Mới";
        DOM.formModelUuid.value = "";
        DOM.formModelName.value = "";
        DOM.formModelId.value = "";
        DOM.formModelProvider.value = "";
        DOM.formModelCategory.value = "Chat";
        DOM.formModelSeries.value = "";
        DOM.formModelContext.value = ">= 128K";
        DOM.formModelSize.value = "10 ~ 50B";
        DOM.formModelBadge.value = "";
        DOM.formModelTags.value = "";
        DOM.formModelApiUrl.value = "";
        DOM.formModelApiKey.value = "";
        DOM.formModelDescription.value = "";
        
        DOM.modelFormModal.classList.add("active");
    }

    /**
     * Retrieves specific model parameters to populate Edit Config Modal.
     */
    function openEditModelModal(uuid) {
        if (!DOM.modelFormModal || !DOM.modalFormTitle) return;

        const model = loadedModels.find(m => m.id === uuid);
        if (!model) return;
        
        DOM.modalFormTitle.innerText = "✏️ Chỉnh Sửa Cấu Hình Mô Hình";
        DOM.formModelUuid.value = model.id;
        DOM.formModelName.value = model.name;
        DOM.formModelId.value = model.model_id;
        DOM.formModelProvider.value = model.provider;
        DOM.formModelCategory.value = model.category;
        DOM.formModelSeries.value = model.series || "";
        DOM.formModelContext.value = model.context_window || ">= 128K";
        DOM.formModelSize.value = model.model_size || "10 ~ 50B";
        DOM.formModelBadge.value = model.special_badge || "";
        DOM.formModelTags.value = model.tags ? model.tags.join(", ") : "";
        DOM.formModelApiUrl.value = model.api_url || "";
        DOM.formModelApiKey.value = model.api_key || "";
        DOM.formModelDescription.value = model.description || "";
        
        DOM.modelFormModal.classList.add("active");
    }

    /**
     * Closes current modal.
     */
    function closeModelModal() {
        if (DOM.modelFormModal) {
            DOM.modelFormModal.classList.remove("active");
        }
    }

    /**
     * Closes modal upon dark-blurred area clicks.
     */
    function closeModelModalOnOuterClick(event) {
        if (event.target.id === "model-form-modal") {
            closeModelModal();
        }
    }

    /**
     * Form validation & payload submission back to postgres workspace.
     */
    async function saveModelForm() {
        const uuid = DOM.formModelUuid.value;
        const name = DOM.formModelName.value.trim();
        const modelId = DOM.formModelId.value.trim();
        const provider = DOM.formModelProvider.value.trim();
        const category = DOM.formModelCategory.value;
        const series = DOM.formModelSeries.value.trim();
        const contextWindow = DOM.formModelContext.value;
        const modelSize = DOM.formModelSize.value;
        const specialBadge = DOM.formModelBadge.value.trim();
        const tagsText = DOM.formModelTags.value.trim();
        const apiUrl = DOM.formModelApiUrl.value.trim();
        const apiKey = DOM.formModelApiKey.value.trim();
        const description = DOM.formModelDescription.value.trim();

        if (!name || !modelId || !provider || !category) {
            showModalAlert("Vui lòng điền đầy đủ các trường bắt buộc (Tên, Model ID, Nhà cung cấp, Loại mô hình)!", "error");
            return;
        }

        const tags = tagsText 
            ? tagsText.split(",").map(tag => tag.trim()).filter(tag => tag.length > 0) 
            : [];
            
        const payload = {
            name, 
            model_id: modelId, 
            provider, 
            category, 
            series: series || provider, 
            context_window: contextWindow, 
            model_size: modelSize,
            special_badge: specialBadge || null,
            is_new: !!specialBadge,
            tags, 
            description,
            api_url: apiUrl || null,
            api_key: apiKey || null
        };

        const targetUrl = uuid ? `/api/workspace/models/${uuid}` : "/api/workspace/models";
        const targetMethod = uuid ? "PUT" : "POST";

        try {
            const response = await apiRequest(targetUrl, {
                method: targetMethod,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (response.status === "success") {
                closeModelModal();
                fetchModelsList();
            } else {
                showModalAlert("Lỗi khi lưu cấu hình: " + (response.error || "Unknown"), "error");
            }
        } catch (error) {
            showModalAlert("Lỗi kết nối máy chủ khi lưu.", "error");
        }
    }

    /**
     * Completely drops specific custom model configuration from DB.
     */
    async function deleteModel(uuid) {
        if (!confirm("Bạn có chắc chắn muốn xóa mô hình này khỏi thư viện cấu hình không?")) {
            return;
        }

        try {
            const response = await apiRequest(`/api/workspace/models/${uuid}`, { 
                method: "DELETE" 
            });

            if (response.status === "success") {
                const card = document.getElementById(`model-card-${uuid}`);
                if (card) {
                    // Trigger custom cards fade-out animation first
                    card.style.opacity = "0";
                    card.style.transform = "scale(0.9)";
                    setTimeout(() => { 
                        fetchModelsList(); 
                    }, 300);
                } else {
                    fetchModelsList();
                }
            } else {
                showModalAlert("Lỗi khi xóa mô hình: " + (response.error || "Unknown"), "error");
            }
        } catch (error) {
            showModalAlert("Lỗi kết nối máy chủ.", "error");
        }
    }

    /**
     * Renders standard fallback alert UI.
     */
    function showModalAlert(message, type) {
        // Fallback to standard alerts, but log beautifully
        console.warn(`[${type.toUpperCase()}] Dashboard Alert: ${message}`);
        alert(message);
    }

    // =========================================================================
    // 10. INITIALIZATION & DYNAMIC EVENT REGISTRATION
    // =========================================================================

    /**
     * Standard DOMContentLoaded routing setup.
     */
    function init() {
        cacheDOM();
        
        // Fetch baseline data
        fetchMetrics();
        loadAISettings();

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
            // Remove old inline handler to prevent multiple executions
            DOM.btnRefreshMetrics.removeAttribute("onclick");
            DOM.btnRefreshMetrics.addEventListener("click", fetchMetrics);
        }

        if (DOM.btnOpenModels) {
            DOM.btnOpenModels.removeAttribute("onclick");
            DOM.btnOpenModels.addEventListener("click", openModelsOverlay);
        }

        // 3. System AI settings parameter sliders and triggers binding
        if (DOM.settingAiModel) {
            DOM.settingAiModel.removeAttribute("onchange");
            DOM.settingAiModel.addEventListener("change", toggleCustomModelInput);
        }

        if (DOM.settingTemp) {
            DOM.settingTemp.removeAttribute("oninput");
            DOM.settingTemp.addEventListener("input", event => {
                if (DOM.settingTempVal) {
                    DOM.settingTempVal.innerText = parseFloat(event.target.value).toFixed(2);
                }
            });
        }

        if (DOM.settingContext) {
            DOM.settingContext.removeAttribute("oninput");
            DOM.settingContext.addEventListener("input", event => {
                if (DOM.settingContextVal) {
                    DOM.settingContextVal.innerText = Number(event.target.value).toLocaleString();
                }
            });
        }

        if (DOM.settingRecursion) {
            DOM.settingRecursion.removeAttribute("oninput");
            DOM.settingRecursion.addEventListener("input", event => {
                if (DOM.settingRecursionVal) {
                    DOM.settingRecursionVal.innerText = event.target.value;
                }
            });
        }

        if (DOM.btnSaveSettings) {
            DOM.btnSaveSettings.removeAttribute("onclick");
            DOM.btnSaveSettings.addEventListener("click", saveAISettings);
        }

        // 4. Models library overlay controls binding
        if (DOM.btnCloseModels) {
            DOM.btnCloseModels.removeAttribute("onclick");
            DOM.btnCloseModels.addEventListener("click", closeModelsOverlay);
        }

        if (DOM.btnToggleSidebar) {
            DOM.btnToggleSidebar.removeAttribute("onclick");
            DOM.btnToggleSidebar.addEventListener("click", toggleSidebar);
        }

        if (DOM.modelSearchQuery) {
            DOM.modelSearchQuery.removeAttribute("oninput");
            DOM.modelSearchQuery.addEventListener("input", renderModelsGrid);
        }

        // 5. Models CRUD Modal form bindings
        if (DOM.btnNewModel) {
            DOM.btnNewModel.removeAttribute("onclick");
            DOM.btnNewModel.addEventListener("click", openNewModelModal);
        }

        if (DOM.modelFormModal) {
            DOM.modelFormModal.removeAttribute("onclick");
            DOM.modelFormModal.addEventListener("click", closeModelModalOnOuterClick);
        }

        if (DOM.btnSaveForm) {
            DOM.btnSaveForm.removeAttribute("onclick");
            DOM.btnSaveForm.addEventListener("click", saveModelForm);
        }

        if (DOM.btnCloseForm) {
            DOM.btnCloseForm.removeAttribute("onclick");
            DOM.btnCloseForm.addEventListener("click", closeModelModal);
        }
    }

    // Register Initialization
    window.addEventListener("DOMContentLoaded", init);

    // =========================================================================
    // 11. EXPOSE CLEAN SYSTEM INTERFACES (ONLY MINIMUM REQUIRED HANDLERS)
    // =========================================================================
    window.fetchMetrics = fetchMetrics;
    window.openNewModelModal = openNewModelModal;
    window.openEditModelModal = openEditModelModal;
    window.closeModelModal = closeModelModal;
    window.saveModelForm = saveModelForm;
    window.deleteModel = deleteModel;
    window.activateModel = activateModel;
    window.clearFilter = clearFilter;
    window.openModelsOverlay = openModelsOverlay;
    window.closeModelsOverlay = closeModelsOverlay;
    window.toggleSidebar = toggleSidebar;
    window.saveAISettings = saveAISettings;
    window.toggleCustomModelInput = toggleCustomModelInput;

})();
