/* Decoupled Integrations Settings Controller */

(function() {
    // State Stores
    let integrationsData = [];
    let visibleKeys = new Set(); // Stores IDs of integrations which have visibility unmasked

    // DOM Cache
    const DOM = {
        integrationsList: document.getElementById("integrations-list-container"),
        formIntPlatform: document.getElementById("form-int-platform"),
        formIntKey: document.getElementById("form-int-key"),
        formIntValue: document.getElementById("form-int-value"),
        formIntActive: document.getElementById("form-int-active"),
        btnSaveIntegration: document.getElementById("btn-save-integration"),
        integrationStatus: document.getElementById("integration-status"),
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
    // WORKSPACE INTEGRATIONS MANAGEMENT
    // =========================================================================
    async function fetchIntegrations() {
        if (!DOM.integrationsList) return;
        DOM.integrationsList.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 2rem;">🔄 Đang tải các khóa tích hợp bên thứ ba...</div>';

        try {
            const res = await apiRequest("/api/workspace/integrations");
            if (res.status === "success") {
                integrationsData = res.data || [];
                renderIntegrations();
            } else {
                DOM.integrationsList.innerHTML = `<div style="text-align: center; color: var(--color-danger); padding: 2rem;">❌ Không tải được tích hợp: ${res.error || "Unknown"}</div>`;
            }
        } catch (e) {
            DOM.integrationsList.innerHTML = `<div style="text-align: center; color: var(--color-danger); padding: 2rem;">❌ Lỗi kết nối API Tích hợp: ${e.message}</div>`;
        }
    }

    let editingIntegrationId = null;

    function renderIntegrations() {
        if (!DOM.integrationsList) return;
        
        if (integrationsData.length === 0) {
            DOM.integrationsList.innerHTML = `
                <div class="glass-panel">
                    <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
                        <span style="font-size: 3rem; display: block; margin-bottom: 12px;">🔌</span>
                        <h3 style="color: #fff; margin-bottom: 8px;">Chưa có tích hợp bên thứ ba nào hoạt động</h3>
                        <p style="font-size: 0.85rem; max-width: 480px; margin: 0 auto;">Hãy sử dụng form kế bên để tự do đăng ký khóa bảo mật tích hợp cho các dịch vụ.</p>
                    </div>
                </div>
            `;
            return;
        }

        // Group integration records by platform_name
        const grouped = {};
        integrationsData.forEach(item => {
            const plat = item.platform_name || "unknown";
            if (!grouped[plat]) {
                grouped[plat] = [];
            }
            grouped[plat].push(item);
        });

        // Clear list
        DOM.integrationsList.innerHTML = "";

        // For each group, render a gorgeous panel
        Object.keys(grouped).forEach(platform => {
            const records = grouped[platform];
            const activeCount = records.filter(r => r.is_active).length;
            
            const card = document.createElement("div");
            card.className = "glass-panel";
            card.style.borderColor = activeCount > 0 ? "rgba(16, 185, 129, 0.2)" : "rgba(255,255,255,0.06)";
            card.style.marginBottom = "12px";
            
            let icon = "🔌";
            let friendlyName = platform.toUpperCase();
            if (platform === "upload-post") {
                icon = "📱";
                friendlyName = "Upload-Post API";
            } else if (platform === "serpapi") {
                icon = "🔍";
                friendlyName = "SerpAPI";
            }

            const badgeHtml = activeCount > 0 
                ? `<span class="badge-active" style="cursor: default;">🟢 Active (${activeCount})</span>`
                : `<span class="badge-inactive" style="cursor: default;">⚪ Inactive</span>`;

            let tableRows = records.map(record => {
                const isMasked = !visibleKeys.has(record.id);
                
                let displayValue = record.config_value;
                if (isMasked && record.config_value) {
                    if (record.config_value.length > 10) {
                        displayValue = record.config_value.substring(0, 7) + "••••••••••••";
                    } else {
                        displayValue = "••••••••••••";
                    }
                }

                const statusBadge = record.is_active 
                    ? `<span class="badge-active" title="Bấm để Tắt hoạt động" onclick="toggleIntegrationStatus('${record.id}')">Active</span>`
                    : `<span class="badge-inactive" title="Bấm để Bật hoạt động" onclick="toggleIntegrationStatus('${record.id}')">Inactive</span>`;

                const eyeIcon = isMasked ? "👁️" : "🙈";

                return `
                    <tr id="int-row-${record.id}">
                        <td style="font-weight: 600; color: #a78bfa;">${record.config_key}</td>
                        <td>
                            <div class="value-cell-wrapper">
                                <span class="${isMasked ? 'masked-value' : 'unmasked-value'}">${displayValue}</span>
                                <button class="btn-icon" title="Ẩn/Hiện Giá trị" onclick="toggleKeyVisibility('${record.id}')">
                                    ${eyeIcon}
                                </button>
                            </div>
                        </td>
                        <td>${statusBadge}</td>
                        <td style="text-align: right; white-space: nowrap;">
                            <button class="btn-icon" title="Chỉnh sửa Biến" onclick="startEditIntegration('${record.id}')" style="margin-right: 4px;">
                                ✏️
                            </button>
                            <button class="btn-icon btn-icon-delete" title="Xóa Biến Tích Hợp" onclick="deleteIntegrationRecord('${record.id}')">
                                ❌
                            </button>
                        </td>
                    </tr>
                `;
            }).join("");

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 10px; margin-bottom: 12px;">
                    <h4 style="font-size: 1rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px;">
                        <span style="font-size:1.2rem;">${icon}</span> ${friendlyName}
                    </h4>
                    ${badgeHtml}
                </div>
                <table class="integration-table">
                    <thead>
                        <tr>
                            <th>Cấu Hình Key</th>
                            <th>Cấu Hình Giá Trị</th>
                            <th>Trạng Thái</th>
                            <th style="text-align: right;">Hành Động</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tableRows}
                    </tbody>
                </table>
            `;

            DOM.integrationsList.appendChild(card);
        });
    }

    // Expose visibility toggle to global context
    window.toggleKeyVisibility = function(id) {
        if (visibleKeys.has(id)) {
            visibleKeys.delete(id);
        } else {
            visibleKeys.add(id);
        }
        renderIntegrations();
    };

    window.selectSuggestedPlatform = function(val) {
        if (!DOM.formIntPlatform) return;
        DOM.formIntPlatform.value = val;
        DOM.formIntPlatform.focus();
    };

    window.selectSuggestedKey = function(val) {
        if (!DOM.formIntKey) return;
        DOM.formIntKey.value = val;
        DOM.formIntKey.focus();
    };

    // Instant status toggle directly in the table
    window.toggleIntegrationStatus = async function(id) {
        const record = integrationsData.find(r => r.id === id);
        if (!record) return;

        const payload = {
            id: record.id,
            platform_name: record.platform_name,
            config_key: record.config_key,
            config_value: record.config_value,
            is_active: !record.is_active
        };

        try {
            const res = await apiRequest("/api/workspace/integrations", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (res.status === "success") {
                showIntStatus("✅ Đã cập nhật trạng thái tích hợp!", "success");
                
                // Sync with editing form active checkbox if currently editing this record
                if (editingIntegrationId === id) {
                    DOM.formIntActive.checked = !record.is_active;
                }
                
                fetchIntegrations();
            } else {
                showIntStatus("❌ Lỗi: " + (res.message || "Không rõ nguyên nhân"), "error");
            }
        } catch (e) {
            showIntStatus("❌ Lỗi kết nối API: " + e.message, "error");
        }
    };

    // Edit record: Populates form and switches visual state
    window.startEditIntegration = function(id) {
        const record = integrationsData.find(r => r.id === id);
        if (!record) return;

        editingIntegrationId = id;
        DOM.formIntPlatform.value = record.platform_name;
        DOM.formIntKey.value = record.config_key;
        DOM.formIntValue.value = record.config_value;
        DOM.formIntActive.checked = record.is_active;

        // Highlight the form panel container with nice Indigo glow
        const formCard = document.querySelector(".integration-form").parentElement;
        formCard.style.borderColor = "rgba(129, 140, 248, 0.8)";
        formCard.style.boxShadow = "0 0 25px rgba(129, 140, 248, 0.25)";
        
        // Change title and button text
        const titleEl = formCard.querySelector("h3");
        titleEl.innerHTML = `✏️ Chỉnh Sửa Khóa Tích Hợp`;
        
        DOM.btnSaveIntegration.innerHTML = `💾 Cập Nhật Khóa Tích Hợp`;

        // Add or show a cancel button dynamically
        let cancelBtn = document.getElementById("btn-cancel-edit-integration");
        if (!cancelBtn) {
            cancelBtn = document.createElement("button");
            cancelBtn.id = "btn-cancel-edit-integration";
            cancelBtn.className = "refresh-btn";
            cancelBtn.style.width = "100%";
            cancelBtn.style.marginTop = "8px";
            cancelBtn.style.background = "rgba(255,255,255,0.05)";
            cancelBtn.style.borderColor = "var(--border-glass)";
            cancelBtn.style.boxShadow = "none";
            cancelBtn.style.padding = "10px";
            cancelBtn.style.fontSize = "0.9rem";
            cancelBtn.innerText = "❌ Hủy Chỉnh Sửa";
            cancelBtn.onclick = cancelEditIntegration;
            DOM.btnSaveIntegration.parentElement.appendChild(cancelBtn);
        } else {
            cancelBtn.style.display = "block";
        }

        DOM.formIntPlatform.focus();
    };

    window.cancelEditIntegration = function() {
        editingIntegrationId = null;
        DOM.formIntPlatform.value = "";
        DOM.formIntKey.value = "";
        DOM.formIntValue.value = "";
        DOM.formIntActive.checked = true;

        const formCard = document.querySelector(".integration-form").parentElement;
        formCard.style.borderColor = "var(--border-glass)";
        formCard.style.boxShadow = "none";

        const titleEl = formCard.querySelector("h3");
        titleEl.innerHTML = `📝 Thêm / Cập Nhật Khóa Tích Hợp`;

        DOM.btnSaveIntegration.innerHTML = `💾 Lưu Khóa Tích Hợp`;

        const cancelBtn = document.getElementById("btn-cancel-edit-integration");
        if (cancelBtn) {
            cancelBtn.style.display = "none";
        }
    };

    async function saveIntegrationRecord() {
        const platformName = DOM.formIntPlatform.value.trim().toLowerCase();
        const configKey = DOM.formIntKey.value.trim().toLowerCase();
        const configValue = DOM.formIntValue.value.trim();
        const isActive = DOM.formIntActive.checked;

        if (!platformName || !configKey || configValue === "") {
            showIntStatus("❌ Thất bại: Vui lòng điền đầy đủ tất cả các trường!", "error");
            return;
        }

        showIntStatus("⏳ Đang lưu khóa tích hợp...", "info");

        const payload = {
            platform_name: platformName,
            config_key: configKey,
            config_value: configValue,
            is_active: isActive
        };
        if (editingIntegrationId) {
            payload.id = editingIntegrationId;
        }

        try {
            const res = await apiRequest("/api/workspace/integrations", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (res.status === "success") {
                showIntStatus("✅ Đồng bộ thành công khóa cấu hình!", "success");
                cancelEditIntegration();
                fetchIntegrations();
            } else {
                showIntStatus("❌ Lỗi: " + (res.message || "Không rõ nguyên nhân"), "error");
            }
        } catch (e) {
            showIntStatus("❌ Lỗi kết nối API: " + e.message, "error");
        }
    }

    window.deleteIntegrationRecord = async function(id) {
        if (!confirm("Bạn có chắc chắn muốn xóa vĩnh viễn khóa cấu hình tích hợp này khỏi hệ thống không?")) {
            return;
        }

        try {
            const res = await apiRequest("/api/workspace/integrations/delete", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: id })
            });

            if (res.status === "success") {
                showIntStatus("✅ Xóa khóa tích hợp thành công!", "success");
                if (editingIntegrationId === id) {
                    cancelEditIntegration();
                }
                fetchIntegrations();
            } else {
                alert("❌ Thất bại khi xóa: " + (res.error || "Unknown"));
            }
        } catch (e) {
            alert("❌ Lỗi kết nối API xóa khóa.");
        }
    };

    function showIntStatus(message, type) {
        if (!DOM.integrationStatus) return;
        DOM.integrationStatus.style.display = "block";
        DOM.integrationStatus.textContent = message;

        if (type === "success") {
            DOM.integrationStatus.style.background = "rgba(16,185,129,0.15)";
            DOM.integrationStatus.style.color = "var(--color-success)";
        } else if (type === "error") {
            DOM.integrationStatus.style.background = "rgba(239,68,68,0.15)";
            DOM.integrationStatus.style.color = "var(--color-danger)";
        } else {
            DOM.integrationStatus.style.background = "rgba(99,102,241,0.15)";
            DOM.integrationStatus.style.color = "#818cf8";
        }

        if (type !== "info") {
            setTimeout(() => {
                DOM.integrationStatus.style.display = "none";
            }, 4000);
        }
    }

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

        if (DOM.btnSaveIntegration) {
            DOM.btnSaveIntegration.addEventListener("click", saveIntegrationRecord);
        }

        fetchIntegrations();
    }

    window.addEventListener("DOMContentLoaded", init);
})();
