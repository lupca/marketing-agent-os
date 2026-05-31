/* Decoupled Models and Parameters Settings Controller */

(function() {
    // State Stores
    let loadedModels = [];
    const activeFilters = {
        category: new Set(),
        tags: new Set(),
        series: new Set(),
        context: new Set(),
        size: new Set()
    };

    // DOM Cache
    const DOM = {
        // LLM Settings Selectors
        llmFormPanel: document.getElementById("llm-form-panel"),
        settingAiModel: document.getElementById("setting-ai-model"),
        customModelContainer: document.getElementById("custom-model-container"),
        settingCustomAiModel: document.getElementById("setting-custom-ai-model"),
        settingTemp: document.getElementById("setting-temp"),
        settingTempVal: document.getElementById("setting-temp-val"),
        settingContext: document.getElementById("setting-context"),
        settingContextVal: document.getElementById("setting-context-val"),
        settingRecursion: document.getElementById("setting-recursion"),
        settingRecursionVal: document.getElementById("setting-recursion-val"),
        settingRerankMode: document.getElementById("setting-rerank-mode"),
        settingApiKey: document.getElementById("setting-api-key"),
        settingApiUrl: document.getElementById("setting-api-url"),
        settingEnableThinking: document.getElementById("setting-enable-thinking"),
        btnSaveSettings: document.getElementById("btn-save-settings"),
        settingsStatus: document.getElementById("settings-status"),

        // Models Library Selectors
        modelsGrid: document.getElementById("models-grid"),
        modelsSidebar: document.getElementById("models-sidebar"),
        modelSearchQuery: document.getElementById("model-search-query"),
        btnNewModel: document.getElementById("btn-new-model"),
        
        // Models Modals Form
        modelFormModal: document.getElementById("model-form-modal"),
        modalFormTitle: document.getElementById("modal-form-title"),
        formModelUuid: document.getElementById("form-model-uuid"),
        formModelName: document.getElementById("form-model-name"),
        formModelId: document.getElementById("form-model-id"),
        formModelProvider: document.getElementById("form-model-provider"),
        formModelCategory: document.getElementById("form-model-category"),
        formModelSeries: document.getElementById("form-model-series"),
        formModelContext: document.getElementById("form-model-context"),
        formModelSize: document.getElementById("form-model-size"),
        formModelBadge: document.getElementById("form-model-badge"),
        formModelTags: document.getElementById("form-model-tags"),
        formModelApiUrl: document.getElementById("form-model-api-url"),
        formModelApiKey: document.getElementById("form-model-api-key"),
        formModelDescription: document.getElementById("form-model-description"),
        btnSaveForm: document.getElementById("btn-save-form"),
        btnCloseForm: document.getElementById("btn-close-form")
    };

    // Generic API Client Wrapper
    async function apiRequest(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                const errText = await response.text();
                throw new Error(errText || `HTTP ${response.status}`);
            }
            return await response.json();
        } catch (e) {
            console.error(`API Error on ${url}:`, e);
            throw e;
        }
    }

    // =========================================================================
    // LLM SYSTEM CONFIGURATION
    // =========================================================================
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

    async function saveAISettings(showToastAlert = true) {
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
                updateSettingsStatus("✅ Cấu hình hệ thống đã đồng bộ thành công vào CSDL!", "success");
                if (showToastAlert) {
                    alert("Lưu cấu hình mô hình thành công! Các Agent sẽ lập tức chạy trên tham số mới.");
                }
            } else {
                updateSettingsStatus("❌ Lỗi: " + (data.message || "Không rõ nguyên nhân"), "error");
            }
        } catch (error) {
            updateSettingsStatus("❌ Lỗi kết nối: " + error.message, "error");
        }
    }

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
    // AI MODELS LIBRARY
    // =========================================================================
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
                DOM.modelsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--color-danger); padding: 3rem;">❌ Lỗi khi tải mô hình: ${response.error || "Unknown"}</div>`;
            }
        } catch (error) {
            DOM.modelsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--color-danger); padding: 3rem;">❌ Lỗi kết nối máy chủ.</div>`;
        }
    }

    function setupFilterListeners() {
        const pills = document.querySelectorAll(".models-sidebar .filter-pill");
        pills.forEach(pill => {
            const freshPill = pill.cloneNode(true);
            pill.parentNode.replaceChild(freshPill, pill);
        });

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

    window.clearFilter = function(group) {
        if (!activeFilters[group]) return;
        activeFilters[group].clear();
        document.querySelectorAll(`#filter-${group} .filter-pill`).forEach(pill => {
            pill.classList.remove("active");
        });
        renderModelsGrid();
    };

    function renderModelsGrid() {
        if (!DOM.modelsGrid) return;

        const searchQuery = DOM.modelSearchQuery ? DOM.modelSearchQuery.value.toLowerCase().trim() : "";
        const activeModel = DOM.settingAiModel ? DOM.settingAiModel.value : "";
        const activeCustomModel = DOM.settingCustomAiModel ? DOM.settingCustomAiModel.value.trim() : "";
        
        const currentActiveModelId = activeModel === "custom" ? activeCustomModel : activeModel;

        const filtered = loadedModels.filter(model => {
            if (searchQuery) {
                const matches = model.name.toLowerCase().includes(searchQuery) ||
                                model.model_id.toLowerCase().includes(searchQuery) ||
                                (model.description && model.description.toLowerCase().includes(searchQuery));
                if (!matches) return false;
            }
            if (activeFilters.category.size > 0 && !activeFilters.category.has(model.category)) return false;
            if (activeFilters.tags.size > 0) {
                const tagFound = model.tags.some(tag => activeFilters.tags.has(tag));
                if (!tagFound) return false;
            }
            if (activeFilters.series.size > 0 && !activeFilters.series.has(model.series)) return false;
            if (activeFilters.context.size > 0 && !activeFilters.context.has(model.context_window)) return false;
            if (activeFilters.size.size > 0 && !activeFilters.size.has(model.model_size)) return false;
            return true;
        });

        if (filtered.length === 0) {
            DOM.modelsGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 4rem; font-size: 1.1rem;">🔍 Không tìm thấy mô hình nào khớp với bộ lọc hiện tại.</div>';
            return;
        }

        DOM.modelsGrid.innerHTML = filtered.map(model => {
            const isModelActivated = (model.model_id === currentActiveModelId);
            
            const badgesHtml = model.tags.map((tag, idx) => {
                const classes = ["indigo", "purple", "pink", "teal", "emerald"];
                const selectClass = classes[idx % classes.length];
                return `<span class="model-badge ${selectClass}">${tag}</span>`;
            }).join(" ");

            const avatarChar = model.name.charAt(0);
            const activeCardClass = isModelActivated ? "active-model" : "";
            
            const activationAction = isModelActivated 
                ? '<span class="status-badge" style="background: rgba(16,185,129,0.15); border-color: rgba(16,185,129,0.3); color: var(--color-success); font-size: 0.75rem; text-transform: uppercase;">Activated</span>'
                : `<button class="chat-nav-btn" onclick="activateModelAndSave('${model.model_id}')" style="background: rgba(255,255,255,0.03); border-color: var(--border-glass); padding: 6px 12px; font-size: 0.75rem;">✅ Activate</button>`;

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
                        <p class="model-card-desc">${model.description || "Không có mô tả cho mô hình này."}</p>
                    </div>
                    
                    <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 12px;">
                        <div class="model-card-tags">${badgesHtml}</div>
                        <div class="model-card-actions">
                            <div class="card-left-actions">
                                <button class="refresh-btn" onclick="openEditModelModal('${model.id}')" style="background: rgba(255,255,255,0.03); border-color: var(--border-glass); padding: 6px 12px; font-size: 0.75rem; box-shadow: none;">✏️ Edit</button>
                                <button class="refresh-btn" onclick="deleteModelRecord('${model.id}')" style="background: rgba(239,68,68,0.05); border-color: rgba(239,68,68,0.2); color: var(--color-danger); padding: 6px 12px; font-size: 0.75rem; box-shadow: none;">❌ Delete</button>
                            </div>
                            ${activationAction}
                        </div>
                    </div>
                </div>
            `;
        }).join("");
    }

    // INSTANT SYNC & AUTOSAVE ON ACTIVATION
    window.activateModelAndSave = async function(modelId) {
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

        // Sync API URL and API Key override if custom model
        const model = loadedModels.find(m => m.model_id === modelId);
        if (model) {
            DOM.settingApiUrl.value = model.api_url || "";
            DOM.settingApiKey.value = model.api_key || "";
        }
        
        // Automatically open Right Configurations Sidebar if collapsed
        if (DOM.llmFormPanel && DOM.llmFormPanel.classList.contains("collapsed")) {
            DOM.llmFormPanel.classList.remove("collapsed");
            const btnToggleConfigSidebar = document.getElementById("btn-toggle-config-sidebar");
            if (btnToggleConfigSidebar) {
                btnToggleConfigSidebar.style.background = "rgba(99, 102, 241, 0.15)";
                btnToggleConfigSidebar.style.borderColor = "rgba(99, 102, 241, 0.4)";
            }
        }

        // Glow Neon outline feedback during sync
        if (DOM.llmFormPanel) {
            DOM.llmFormPanel.style.borderColor = "rgba(129, 140, 248, 0.8)";
            DOM.llmFormPanel.style.boxShadow = "0 0 30px rgba(129, 140, 248, 0.35)";
            setTimeout(() => {
                DOM.llmFormPanel.style.borderColor = DOM.llmFormPanel.classList.contains("collapsed") ? "transparent" : "rgba(129, 140, 248, 0.25)";
                DOM.llmFormPanel.style.boxShadow = "none";
            }, 2500);
        }

        renderModelsGrid();
        
        // TRIGGER INSTANT DB AUTOSAVE
        await saveAISettings(false);
        
        alert(`[Auto-Save Active] Đã kích hoạt và lưu cấu hình mô hình: ${modelId}`);
    };

    function openNewModelModal() {
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

    window.openEditModelModal = function(uuid) {
        const model = loadedModels.find(m => m.id === uuid);
        if (!model) return;
        
        DOM.modalFormTitle.innerText = "✏ /> Chỉnh Sửa Cấu Hình Mô Hình";
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
    };

    function closeModelModal() {
        DOM.modelFormModal.classList.remove("active");
    }

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
            alert("Vui lòng điền đầy đủ các trường bắt buộc (Tên, Model ID, Nhà cung cấp, Loại mô hình)!");
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
                alert("Lỗi khi lưu cấu hình: " + (response.error || "Unknown"));
            }
        } catch (error) {
            alert("Lỗi kết nối máy chủ khi lưu.");
        }
    }

    window.deleteModelRecord = async function(uuid) {
        if (!confirm("Bạn có chắc chắn muốn xóa mô hình này khỏi thư viện cấu hình không?")) {
            return;
        }

        try {
            const response = await apiRequest(`/api/workspace/models/${uuid}`, { 
                method: "DELETE" 
            });

            if (response.status === "success") {
                fetchModelsList();
            } else {
                alert("Lỗi khi xóa mô hình: " + (response.error || "Unknown"));
            }
        } catch (error) {
            alert("Lỗi kết nối máy chủ.");
        }
    };

    // Page Initialization Entrypoint
    function init() {
        // Toggle Main Sidebar navigation (left)
        const btnToggleMainSidebar = document.getElementById("btn-toggle-main-sidebar");
        const mainSettingsSidebar = document.getElementById("main-settings-sidebar");
        if (btnToggleMainSidebar && mainSettingsSidebar) {
            btnToggleMainSidebar.addEventListener("click", () => {
                mainSettingsSidebar.classList.toggle("collapsed");
                if (mainSettingsSidebar.classList.contains("collapsed")) {
                    btnToggleMainSidebar.style.background = "rgba(255,255,255,0.03)";
                    btnToggleMainSidebar.style.borderColor = "var(--border-glass)";
                } else {
                    btnToggleMainSidebar.style.background = "rgba(99, 102, 241, 0.15)";
                    btnToggleMainSidebar.style.borderColor = "rgba(99, 102, 241, 0.4)";
                }
            });
        }

        // Toggle Config parameters sidebar (right)
        const btnToggleConfigSidebar = document.getElementById("btn-toggle-config-sidebar");
        const llmFormPanel = document.getElementById("llm-form-panel");
        if (btnToggleConfigSidebar && llmFormPanel) {
            btnToggleConfigSidebar.addEventListener("click", () => {
                llmFormPanel.classList.toggle("collapsed");
                if (llmFormPanel.classList.contains("collapsed")) {
                    btnToggleConfigSidebar.style.background = "rgba(255,255,255,0.03)";
                    btnToggleConfigSidebar.style.borderColor = "var(--border-glass)";
                } else {
                    btnToggleConfigSidebar.style.background = "rgba(99, 102, 241, 0.15)";
                    btnToggleConfigSidebar.style.borderColor = "rgba(99, 102, 241, 0.4)";
                }
            });
        }

        // Setup input sliders events
        if (DOM.settingAiModel) {
            DOM.settingAiModel.addEventListener("change", toggleCustomModelInput);
        }
        if (DOM.settingTemp) {
            DOM.settingTemp.addEventListener("input", e => {
                DOM.settingTempVal.innerText = parseFloat(e.target.value).toFixed(2);
            });
        }
        if (DOM.settingContext) {
            DOM.settingContext.addEventListener("input", e => {
                DOM.settingContextVal.innerText = Number(e.target.value).toLocaleString();
            });
        }
        if (DOM.settingRecursion) {
            DOM.settingRecursion.addEventListener("input", e => {
                DOM.settingRecursionVal.innerText = e.target.value;
            });
        }
        if (DOM.btnSaveSettings) {
            DOM.btnSaveSettings.addEventListener("click", () => saveAISettings(true));
        }

        // Register Models bindings
        if (DOM.btnNewModel) DOM.btnNewModel.addEventListener("click", openNewModelModal);
        if (DOM.btnCloseForm) DOM.btnCloseForm.addEventListener("click", closeModelModal);
        if (DOM.btnSaveForm) DOM.btnSaveForm.addEventListener("click", saveModelForm);
        
        if (DOM.modelFormModal) {
            DOM.modelFormModal.addEventListener("click", e => {
                if (e.target.id === "model-form-modal") closeModelModal();
            });
        }

        if (DOM.modelSearchQuery) {
            DOM.modelSearchQuery.addEventListener("input", renderModelsGrid);
        }

        loadAISettings();
        fetchModelsList();
    }

    window.addEventListener("DOMContentLoaded", init);
})();
