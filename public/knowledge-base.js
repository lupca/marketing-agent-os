(function () {
    /* ============================================================
       STATE & GLOBAL VARIABLES
    ============================================================ */
    let allTags = [];
    let selectedUploadTags = ["global"];
    let selectedPlaygroundTags = ["global"];
    let loadedDocuments = [];
    let pollIntervals = {};
    let activeLimit = 5;
    let activeStatusFilter = "all";
    let activeTagFilter = "all";
    
    const WORKSPACE_ID = null; // null = auto-detect workspace

    /* ============================================================
       UTIL LOGS & METRIC FORMATTERS
    ============================================================ */
    function toast(message, type = "info", duration = 3500) {
      const container = document.getElementById("toast-container");
      if (!container) return;

      const el = document.createElement("div");
      const icons = { success: "✅", error: "❌", info: "ℹ️" };
      el.className = `toast ${type}`;
      el.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${message}</span>`;
      container.appendChild(el);

      setTimeout(() => { 
        el.style.opacity = "0"; 
        setTimeout(() => el.remove(), 300); 
      }, duration);
    }

    function formatBytes(bytes) {
      if (!bytes || bytes === 0) return "—";
      const sizes = ["B", "KB", "MB", "GB"];
      const i = Math.floor(Math.log(bytes) / Math.log(1024));
      return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
    }

    function buildQS(url, params) {
      const u = new URL(url, window.location.origin);
      if (params) {
        Object.entries(params).forEach(([k, v]) => u.searchParams.set(k, v));
      }
      return u.toString();
    }

    /**
     * Map filename to corresponding modern notebook visual icon representation
     */
    function getFileIcon(filename) {
      const ext = filename.split('.').pop().toLowerCase();
      switch(ext) {
        case 'pdf': return '📕';
        case 'mp3':
        case 'wav':
        case 'm4a': return '🎧';
        case 'xlsx':
        case 'xls':
        case 'csv': return '📊';
        case 'docx':
        case 'doc':
        case 'md': return '📝';
        case 'pptx':
        case 'ppt': return '🗂️';
        default: return '📄';
      }
    }

    function adjustInputHeight(el) {
      el.style.height = "24px";
      el.style.height = (el.scrollHeight - 4) + "px";
    }

    function toggleLimitParameter() {
      const limits = [3, 5, 8, 10];
      const idx = limits.indexOf(activeLimit);
      activeLimit = limits[(idx + 1) % limits.length];
      document.getElementById("lbl-pg-limit").textContent = activeLimit;
      toast(`🎯 Đã cấu hình tối đa RAG retrieval: ${activeLimit} chunks`, "info");
    }

    // ============================================================
    // DYNAMIC ACCESS TAGS MANAGEMENT
    // ============================================================
    async function loadTags() {
      try {
        const params = WORKSPACE_ID ? { workspace_id: WORKSPACE_ID } : {};
        const response = await fetch(buildQS("/api/rag/tags", params));
        const data = await response.json();
        
        allTags = data.tags || [];
        renderUploadTagGrid();
        renderPlaygroundTagGrid();
        renderModalTagGrid();
        renderFilterTagsRow();
      } catch (error) {
        console.error("Failed to load RAG access tags:", error);
        document.getElementById("tags-grid").innerHTML = `<span class="text-muted">Lỗi tải tags</span>`;
      }
    }

    function getAgentAccessExplanation(tagName) {
      switch (tagName) {
        case "global": return "Tất cả các Agents";
        case "marketing": return "Creative Agent (Lên ý tưởng)";
        case "anti_patterns": return "Analyst (Phân tích) & Creative (Sáng tạo)";
        case "policies": return "Researcher (Tra cứu) & Brand Guardian (Kiểm duyệt)";
        case "manager_feedback": return "Tất cả Agents (Học từ feedback của CMO)";
        case "psychology": return "Creative Agent (Tối ưu tâm lý người dùng)";
        case "economics": return "Analyst Agent (Nghiên cứu thị trường)";
        default: return "Agents được phân quyền trong Workspace";
      }
    }

    function renderTagGrid(containerId, selected, toggleHandler) {
      const el = document.getElementById(containerId);
      if (!el) return;
      
      if (!allTags.length) { 
        el.innerHTML = `<span class="text-muted">Chưa có tags</span>`; 
        return; 
      }
      
      el.innerHTML = allTags.map(t => {
        const isSelected = selected.includes(t.tag_name);
        const style = isSelected ? `color:${t.color};border-color:${t.color}` : "";
        return `
          <div class="tag-chip ${isSelected ? "selected" : ""}" style="${style}"
               onclick="${toggleHandler}('${t.tag_name}')">
            <span class="tag-dot" style="background:${t.color}"></span>
            ${t.tag_name}
            <div class="tag-tooltip">
              <div class="tag-tooltip-header">
                <span class="tag-tooltip-dot" style="background:${t.color}"></span>
                <span class="tag-tooltip-name" style="color:${t.color};font-weight:700">${t.tag_name}</span>
              </div>
              <div class="tag-tooltip-desc">${t.description || "Không có mô tả chi tiết."}</div>
              <div class="tag-tooltip-footer">
                🔑 Quyền: ${getAgentAccessExplanation(t.tag_name)}
              </div>
            </div>
          </div>`;
      }).join("");
    }

    function renderUploadTagGrid() { renderTagGrid("tags-grid", selectedUploadTags, "toggleUploadTag"); }
    function renderPlaygroundTagGrid() { renderTagGrid("pg-tags-grid", selectedPlaygroundTags, "togglePlaygroundTag"); }
    function renderModalTagGrid() { renderTagGrid("modal-tags-grid", modalSelectedTags, "toggleModalTag"); }

    function renderFilterTagsRow() {
      const select = document.getElementById("tag-filter-select");
      if (!select) return;
      
      select.innerHTML = `
        <option value="all" style="background:#0f1015; color:#fff;">🏷️ Tất cả Access Tags</option>
      ` + allTags.map(t => {
        return `<option value="${t.tag_name}" style="background:#0f1015; color:${t.color};">${t.tag_name} (${getAgentAccessExplanation(t.tag_name)})</option>`;
      }).join("");
    }

    window.toggleUploadTag = function(tagName) {
      if (selectedUploadTags.includes(tagName)) {
        if (selectedUploadTags.length === 1) return; // Must have at least one access tag
        selectedUploadTags = selectedUploadTags.filter(t => t !== tagName);
      } else {
        selectedUploadTags.push(tagName);
      }
      renderUploadTagGrid();
    };

    window.togglePlaygroundTag = function(tagName) {
      if (selectedPlaygroundTags.includes(tagName)) {
        if (selectedPlaygroundTags.length === 1) return;
        selectedPlaygroundTags = selectedPlaygroundTags.filter(t => t !== tagName);
      } else {
        selectedPlaygroundTags.push(tagName);
      }
      renderPlaygroundTagGrid();
    };

    let modalSelectedTags = [];
    window.toggleModalTag = function(tagName) {
      if (modalSelectedTags.includes(tagName)) {
        if (modalSelectedTags.length === 1) return;
        modalSelectedTags = modalSelectedTags.filter(t => t !== tagName);
      } else {
        modalSelectedTags.push(tagName);
      }
      renderTagGrid("modal-tags-grid", modalSelectedTags, "toggleModalTag");
    };

    // ============================================================
    // PROGRAMMATIC SMART UPLOADER DROPZONE LIFE-CYCLE
    // ============================================================
    Dropzone.autoDiscover = false;
    const dz = new Dropzone("#upload-dropzone", {
      url: "/api/rag/upload",
      paramName: "file",
      maxFilesize: 50,
      acceptedFiles: ".pdf,.txt,.docx,.xlsx,.pptx,.csv,.mp3,.md",
      addRemoveLinks: true,
      dictDefaultMessage: "",
      autoProcessQueue: false,
      parallelUploads: 5,

      init: function () {
        this.on("addedfile", (file) => {
          document.getElementById("upload-status-hint").innerHTML = `📂 1 file hàng đợi &middot; <span style='color:#a5b4fc;font-weight:700;'>Sẵn sàng</span>`;
        });

        this.on("removedfile", (file) => {
          document.getElementById("upload-status-hint").textContent = "Chọn file & tags để upload";
        });

        this.on("sending", (file, xhr, formData) => {
          formData.append("access_tags", JSON.stringify(selectedUploadTags));
          if (WORKSPACE_ID) formData.append("workspace_id", WORKSPACE_ID);
        });

        this.on("success", (file, response) => {
          toast(`✅ File "${file.name}" đã tải lên thành công! HĐH đang băm vector...`, "success", 5000);
          this.removeFile(file);
          
          if (response.document_id) {
            startPollingDocument(response.document_id);
          }
          
          if (this.getQueuedFiles().length > 0) {
            this.processQueue();
          } else {
            document.getElementById("upload-status-hint").textContent = "Chọn file & tags để upload";
            setTimeout(loadDocuments, 1500);
          }
        });

        this.on("error", (file, errorMsg) => {
          const detail = typeof errorMsg === "object" ? errorMsg.detail : errorMsg;
          toast(`❌ Upload thất bại: ${detail}`, "error");
        });
      }
    });

    // Connect custom programmatic uploader click event
    document.getElementById("btn-trigger-upload").addEventListener("click", () => {
      if (dz.getQueuedFiles().length === 0) {
        toast("❌ Bạn chưa chọn tập tin nào để upload!", "error");
        return;
      }
      dz.processQueue();
    });

    // ============================================================
    // SOURCES METRICS & LIST RENDER
    // ============================================================
    async function loadDocuments() {
      try {
        const params = { page: 1, limit: 100 }; // Fetch a large batch for smooth NotebookLM scrolling
        if (WORKSPACE_ID) params.workspace_id = WORKSPACE_ID;
        
        const response = await fetch(buildQS("/api/rag/documents", params));
        const data = await response.json();

        const docs = data.documents || [];
        loadedDocuments = docs;

        // Sync count indicators
        document.getElementById("source-count-lbl").textContent = `${docs.length} nguồn`;
        
        // Auto sync first document title as Middle column subtitle if loaded
        if (docs.length > 0) {
          document.getElementById("notebook-main-title").textContent = `📚 Tri Thức Thư Viện (${docs.length} nguồn active)`;
        }

        renderSourcesList(docs);

        // Auto poll processing docs
        docs.filter(d => d.upload_status === "processing" || d.sync_status === "syncing")
            .forEach(d => startPollingDocument(d.document_id));
      } catch (error) {
        console.error("Failed to load documents catalog:", error);
        document.getElementById("sources-list-body").innerHTML = `<div style="color: var(--color-danger); text-align: center; padding: 2rem;">⚠️ Lỗi tải danh sách tài liệu.</div>`;
      }
    }

    function renderSourcesList(docs) {
      const container = document.getElementById("sources-list-body");
      if (!container) return;

      if (!docs.length) {
        container.innerHTML = `
          <div style="text-align: center; color: var(--text-muted); padding: 3rem 1rem;">
            <div style="font-size:2rem; margin-bottom:10px;">📭</div>
            <div>Thư mục trống. Hãy kéo thả file vào ô bên dưới để nạp nguồn RAG!</div>
          </div>
        `;
        return;
      }

      container.innerHTML = docs.map(d => {
        const icon = getFileIcon(d.file_name);
        const tags = (d.access_tags || ["global"]).map(t => {
          const matchingTag = allTags.find(at => at.tag_name === t);
          const color = matchingTag?.color || "#6366f1";
          return `<span style="display:inline-block; width:5px; height:5px; border-radius:50%; background:${color}; margin-right:3px;" title="Tag: ${t}"></span>`;
        }).join("");

        const sizeLabel = formatBytes(d.file_size_bytes);
        
        // Status indicator visual
        const isProcessing = d.upload_status === "processing";
        const statusColor = d.upload_status === "ready" ? "var(--color-success)" : (isProcessing ? "var(--color-warning)" : "var(--color-danger)");
        const statusLabel = d.upload_status === "ready" ? "Sẵn sàng" : (isProcessing ? "Băm vector..." : "Lỗi băm");

        return `
          <div class="source-card" id="source-item-${d.document_id}" onclick="openDocReader('${d.document_id}')">
            <div class="source-icon">${icon}</div>
            <div class="source-info">
              <div class="source-title" title="${d.file_name}">${d.file_name}</div>
              <div class="source-meta">
                <span style="color:${statusColor}; font-weight:700;">${statusLabel}</span>
                <span>&bull;</span>
                <span>${sizeLabel}</span>
                <span>&bull;</span>
                <span style="display:flex; align-items:center;">${tags}</span>
              </div>
            </div>
            
            <div class="source-actions" onclick="event.stopPropagation()">
              <button class="source-btn" onclick="openEditTagsClick('${d.document_id}')" title="Sửa thông tin RAG">✏️</button>
              <button class="source-btn delete-btn" onclick="deleteDocument('${d.document_id}', '${d.file_name.replace(/'/g, "\\'")}')" title="Xóa mềm nguồn">🗑️</button>
            </div>
          </div>
        `;
      }).join("");
    }

    // Status polling check
    function startPollingDocument(docId) {
      if (pollIntervals[docId]) return;
      
      let attempts = 0;
      pollIntervals[docId] = setInterval(async () => {
        attempts++;
        if (attempts > 60) { 
          clearInterval(pollIntervals[docId]); 
          delete pollIntervals[docId]; 
          return; 
        }
        
        try {
          const res = await fetch(`/api/rag/documents/${docId}/status`);
          const d = await res.json();
          
          if (d.upload_status === "ready" && d.sync_status === "synced") {
            clearInterval(pollIntervals[docId]); 
            delete pollIntervals[docId];
            toast(`✅ Nguồn "${d.file_name}" đã băm thành công ${d.chunk_count} chunks!`, "success");
            loadDocuments();
          } else if (d.upload_status === "failed") {
            clearInterval(pollIntervals[docId]); 
            delete pollIntervals[docId];
            toast(`❌ Băm vector thất bại cho file: "${d.file_name}"`, "error");
            loadDocuments();
          }
        } catch (_) {}
      }, 3000);
    }

    // ============================================================
    // ADVANCED LIVE SEARCH & STATUS FILTER LIFE-CYCLES
    // ============================================================
    window.applyStatusFilter = function(status, pillElement) {
      activeStatusFilter = status;
      
      // Update pills styles
      document.querySelectorAll("#filter-pills-row .filter-pill").forEach(p => {
        p.classList.remove("active");
      });
      pillElement.classList.add("active");
      
      filterSourcesList();
    };

    window.applyTagSelectFilter = function(tagName) {
      activeTagFilter = tagName;
      filterSourcesList();
    };

    window.filterSourcesList = function() {
      const searchQuery = document.getElementById("source-search-query").value.toLowerCase().trim();
      
      const filtered = loadedDocuments.filter(doc => {
        // Search by filename match
        const matchesSearch = doc.file_name.toLowerCase().includes(searchQuery);
        
        // Filter by active status pill
        let matchesStatus = true;
        if (activeStatusFilter !== "all") {
          matchesStatus = doc.upload_status === activeStatusFilter;
        }

        // Filter by active tag pill
        let matchesTag = true;
        if (activeTagFilter !== "all") {
          matchesTag = doc.access_tags && doc.access_tags.includes(activeTagFilter);
        }
        
        return matchesSearch && matchesStatus && matchesTag;
      });
      
      renderSourcesList(filtered);
    };

    // ============================================================
    // GORGEOUS SYSTEM DOCUMENT READER RETRIEVAL PIXEL
    // ============================================================
    window.openDocReader = async function(docId) {
      const doc = loadedDocuments.find(d => d.document_id === docId);
      if (!doc) return;

      const overlay = document.getElementById("doc-reader-overlay");
      const titleEl = document.getElementById("reader-doc-title");
      const metaEl = document.getElementById("reader-doc-meta");
      const bodyEl = document.getElementById("reader-doc-body");
      const iconEl = document.getElementById("reader-doc-icon");

      // Reset values
      iconEl.textContent = getFileIcon(doc.file_name);
      titleEl.textContent = doc.file_name;
      metaEl.textContent = `Kích thước: ${formatBytes(doc.file_size_bytes)} | Chunks: ${doc.chunk_count || 0}`;
      
      bodyEl.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 5rem 0;">
          <span class="spin" style="font-size: 2rem;">⟳</span>
          <div style="margin-top: 12px; font-size:0.85rem;">Đang trích xuất nội dung thô từ CSDL pgvector...</div>
        </div>
      `;

      overlay.classList.add("open");
      document.body.style.overflow = "hidden"; // Clip page scroll

      try {
        // Query vector database for chunks using filename as semantic focus key
        const payload = {
          query: doc.file_name,
          access_tags: doc.access_tags || ["global"],
          limit: 10 // Pull a large set of chunks
        };

        const response = await fetch("/api/rag/test-retrieval", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();

        // Filter chunks matching ONLY this specific document ID (Zero-JOIN extraction)
        const matchedChunks = (data.results || []).filter(r => r.document_id === docId);

        if (matchedChunks.length === 0) {
          bodyEl.innerHTML = `
            <div style="text-align:center; color:var(--text-muted); padding:4rem 0;">
              <div style="font-size:2rem; margin-bottom:10px;">📄</div>
              <p style="font-size:0.9rem;">Tài liệu đã được tải lên thành công, tuy nhiên Celery chưa hoàn tất băm vector hoặc không tìm thấy chunks.</p>
              <button class="btn-studio-add" style="width:auto; margin-top:12px;" onclick="triggerSuggestedPrompt('Tóm tắt tài liệu ${doc.file_name}')">📖 Yêu cầu AI tóm tắt nhanh</button>
            </div>
          `;
          return;
        }

        bodyEl.innerHTML = matchedChunks.map((chunk, idx) => `
          <div class="doc-chunk-item">
            <div class="doc-chunk-num">Phân đoạn chunks #${idx + 1} &middot; Score matching: ${Math.round(chunk.similarity_score * 100)}%</div>
            <div>"${chunk.content_full}"</div>
          </div>
        `).join("");

      } catch (error) {
        console.error("Failed to load raw text from vector engine:", error);
        bodyEl.innerHTML = `
          <div style="text-align:center; color:var(--color-danger); padding:4rem 0;">
            <p>⚠️ Lỗi kết nối: Không thể kết nối với HNSW vector engine để trích xuất chunks.</p>
            <p style="font-size:0.8rem; color:var(--text-muted); margin-top:6px;">Chi tiết: ${error.message}</p>
          </div>
        `;
      }
    };

    window.closeDocReader = function() {
      document.getElementById("doc-reader-overlay").classList.remove("open");
      document.body.style.overflow = "auto";
    };

    // Close reader modal on outer click
    document.getElementById("doc-reader-overlay").addEventListener("click", function(e) {
      if (e.target === this) closeDocReader();
    });

    // ============================================================
    // RAG CHAT PLAYGROUND Retrieval Pipeline
    // ============================================================
    async function runTestRetrieval() {
      const textarea = document.getElementById("pg-query");
      const query = textarea.value.trim();
      
      if (query.length < 3) { 
        toast("❌ Câu hỏi của bạn phải có ít nhất 3 ký tự!", "error"); 
        return; 
      }

      const sendBtn = document.getElementById("btn-run-retrieval");
      sendBtn.disabled = true;
      sendBtn.innerHTML = `<span class="spin">⟳</span>`;

      // Hide default Hello block if showing
      const greetingView = document.getElementById("greeting-view");
      if (greetingView) {
        greetingView.remove();
      }

      const feed = document.getElementById("chat-scroll-feed");
      
      // Append User message bubble
      const userBubble = document.createElement("div");
      userBubble.className = "chat-bubble user";
      userBubble.innerHTML = `
        <div class="chat-bubble-sender">CMO Quyết Định</div>
        <div class="chat-bubble-text">${query}</div>
      `;
      feed.appendChild(userBubble);
      feed.scrollTop = feed.scrollHeight;
      
      // Clear input
      textarea.value = "";
      textarea.style.height = "24px";

      // Append temporary AI Typing/retrieving loader bubble
      const tempAIBubble = document.createElement("div");
      tempAIBubble.className = "chat-bubble ai";
      tempAIBubble.id = "temp-typing-bubble";
      tempAIBubble.innerHTML = `
        <div class="chat-bubble-sender">🤖 Trí tuệ Marketing OS</div>
        <div class="chat-bubble-text"><span class="spin">⟳</span> Đang tìm kiếm các khối vector RAG liên quan từ CSDL pgvector...</div>
      `;
      feed.appendChild(tempAIBubble);
      feed.scrollTop = feed.scrollHeight;

      try {
        const payload = {
          query,
          access_tags: selectedPlaygroundTags,
          limit: activeLimit
        };
        
        if (WORKSPACE_ID) {
          payload.workspace_id = WORKSPACE_ID;
        } else {
          // Dynamic workspace resolve
          const dataTags = await apiRequest("/api/rag/tags");
          payload.workspace_id = dataTags.workspace_id;
        }

        const response = await fetch("/api/rag/test-retrieval", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();

        // Remove typing indicator
        document.getElementById("temp-typing-bubble").remove();

        document.getElementById("pg-elapsed").textContent = `⚡ Truy vấn: ${data.elapsed_ms}ms | Lấy được: ${data.result_count} chunks`;

        // Render AI bubble with scores & citations
        const aiBubble = document.createElement("div");
        aiBubble.className = "chat-bubble ai";
        
        if (!data.results || data.results.length === 0) {
          aiBubble.innerHTML = `
            <div class="chat-bubble-sender">🤖 Trí tuệ Marketing OS</div>
            <div class="chat-bubble-text">Chưa tìm thấy tri thức hoặc kết quả phù hợp nào khớp với bộ tags [${payload.access_tags.join(", ")}] trong HNSW Index. Bạn vui lòng thay đổi tags lọc hoặc nạp thêm tài liệu.</div>
          `;
        } else {
          // Construct summarized response template
          const topResult = data.results[0];
          
          // Generate citation grid score blocks
          const citationsHtml = data.results.map((r, idx) => {
            const pct = Math.round(r.similarity_score * 100);
            const tagsHtml = (r.access_tags || []).map(t => {
              const tag = allTags.find(at => at.tag_name === t);
              return `<span style="font-size:0.6rem; color:${tag?.color||'#a5b4fc'}; font-weight:700; border:1px solid ${tag?.color||'#a5b4fc'}; padding:1px 4px; border-radius:4px;">${t}</span>`;
            }).join(" ");

            return `
              <div class="variant-card" style="padding:8px 12px; border-radius:8px; background:rgba(0,0,0,0.2); gap:4px;" onclick="openDocReader('${r.document_id}')" title="Click để mở trình đọc phân đoạn của document này">
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.7rem;">
                  <span style="font-weight:700; color:var(--text-secondary);">Citations #${idx + 1}</span>
                  <span style="color:var(--color-success); font-weight:800;">🎯 ${pct}%</span>
                </div>
                <p style="font-size:0.75rem; line-height:1.4; color:var(--text-muted); display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">"${r.content_preview}"</p>
                <div style="display:flex; gap:4px; margin-top:2px;">${tagsHtml}</div>
              </div>
            `;
          }).join("");

          // Highlight some keywords dynamically inside text
          let formattedContent = topResult.content_full || topResult.content_preview;
          
          const replacements = [
            { word: "Facebook", cls: "blue" },
            { word: "Facebook Pixel", cls: "blue" },
            { word: "hướng dẫn toàn diện", cls: "purple" },
            { word: "phân tích đối thủ", cls: "green" },
            { word: "Creative Node", cls: "purple" },
            { word: "Learning Curve", cls: "green" },
            { word: "CPA", cls: "purple" }
          ];

          replacements.forEach(r => {
            const regex = new RegExp(`\\b${r.word}\\b`, 'gi');
            formattedContent = formattedContent.replace(regex, `<span class="highlight-keyword ${r.cls}">${r.word}</span>`);
          });

          aiBubble.innerHTML = `
            <div class="chat-bubble-sender">🤖 Trí tuệ Marketing OS (Agent RAG)</div>
            <div class="chat-bubble-text" style="margin-top:4px;">
              <p>${formattedContent}</p>
              
              <div class="citations-section">
                <span class="citations-title">Citations Trích xuất (${data.results.length} chunks)</span>
                <div class="citations-grid">${citationsHtml}</div>
              </div>
            </div>
          `;
        }

        feed.appendChild(aiBubble);
        feed.scrollTop = feed.scrollHeight;

      } catch (error) {
        console.error("RAG Retrieval pipeline broke:", error);
        // Clean typing indicator if exists
        const indicator = document.getElementById("temp-typing-bubble");
        if (indicator) indicator.remove();

        const errBubble = document.createElement("div");
        errBubble.className = "chat-bubble ai";
        errBubble.innerHTML = `
          <div class="chat-bubble-sender">🤖 Trí tuệ Marketing OS</div>
          <div class="chat-bubble-text" style="color:var(--color-danger);">Lỗi hệ thống: Không thể kết nối với cổng nhúng vector RAG. Vui lòng kiểm tra Docker containers hoặc CSDL pgvector.</div>
        `;
        feed.appendChild(errBubble);
        feed.scrollTop = feed.scrollHeight;
        toast("❌ Lỗi khi gọi test retrieval", "error");
      }

      sendBtn.disabled = false;
      sendBtn.innerHTML = `<span style="font-size:1.15rem; font-weight:bold;">→</span>`;
    }

    /**
     * Strategic tools action triggers
     */
    window.triggerSuggestedPrompt = function(promptText) {
      document.getElementById("pg-query").value = promptText;
      runTestRetrieval();
    };

    // ============================================================
    // EDIT DOCUMENTS METADATA
    // ============================================================
    window.openEditTagsClick = function(docId) {
      const doc = loadedDocuments.find(d => d.document_id === docId);
      if (!doc) return;
      
      document.getElementById("modal-doc-id").value = doc.document_id;
      document.getElementById("modal-doc-name").value = doc.file_name;
      modalSelectedTags = [...(doc.access_tags || [])];
      
      renderTagGrid("modal-tags-grid", modalSelectedTags, "toggleModalTag");
      document.getElementById("modal-edit-tags").classList.add("open");
    };

    window.closeModal = function() {
      document.getElementById("modal-edit-tags").classList.remove("open");
    };

    window.saveDocumentTags = async function() {
      const docId = document.getElementById("modal-doc-id").value;
      const fileName = document.getElementById("modal-doc-name").value.trim();
      
      if (!fileName) {
        toast("❌ Tên tài liệu không được để trống!", "error");
        return;
      }

      try {
        const response = await fetch(`/api/rag/documents/${docId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file_name: fileName, access_tags: modalSelectedTags })
        });
        
        if (!response.ok) { 
          const err = await response.json(); 
          toast(`❌ ${err.detail}`, "error"); 
          return; 
        }
        
        toast("🔄 Đã ghi nhận thay đổi! Hệ thống đang tái băm ngầm...", "info");
        closeModal();
        
        setTimeout(loadDocuments, 1000);
      } catch (e) { 
        toast("❌ Lỗi kết nối máy chủ", "error"); 
      }
    };

    // ============================================================
    // DELETE SOURCE DOCUMENTS
    // ============================================================
    window.deleteDocument = async function(docId, fileName) {
      if (!confirm(`Xóa tài liệu "${fileName}"?\n\nDữ liệu sẽ bị xóa mềm và biến mất khỏi tất cả retrieval.`)) {
        return;
      }

      try {
        const response = await fetch(`/api/rag/documents/${docId}`, { 
          method: "DELETE" 
        });
        
        if (!response.ok) { 
          const err = await response.json(); 
          toast(`❌ ${err.detail}`, "error"); 
          return; 
        }
        
        toast(`🗑️ "${fileName}" đang được xóa ngầm...`, "info");
        
        const card = document.getElementById(`source-item-${docId}`);
        if (card) {
          card.style.opacity = "0.3";
          card.style.pointerEvents = "none";
        }
        
        setTimeout(loadDocuments, 1500);
      } catch (e) { 
        toast("❌ Lỗi kết nối", "error"); 
      }
    };

    // DRY request wrapper helper
    async function apiRequest(url, options = {}) {
      const response = await fetch(url, options);
      if (!response.ok) throw new Error("HTTP error " + response.status);
      return await response.json();
    }

    // Modal click out listener
    document.getElementById("modal-edit-tags").addEventListener("click", function(e) {
      if (e.target === this) closeModal();
    });

    /* ============================================================
       INIT PIPELINE
    ============================================================ */
    (async function init() {
      await loadTags();
      await loadDocuments();
      
      // Auto expand query box height on enter
      const textarea = document.getElementById("pg-query");
      textarea.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          runTestRetrieval();
        }
      });
    })();
})();
