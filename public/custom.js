// public/custom.js
(function() {
    console.log("Marketing Agent OS Custom JS Loaded.");

    // Style injection to hide any buttons with "rewind-" text and add custom styles
    const css = `
        button.cl-action-button {
            transition: all 0.2s ease;
        }
        /* Visual styles for aborted messages */
        .aborted-message-wrapper {
            opacity: 0.45 !important;
            text-decoration: line-through !important;
            pointer-events: none !important;
            border-left: 3px solid #ff4d4f !important;
            padding-left: 10px !important;
            background-color: rgba(0, 0, 0, 0.02) !important;
        }
        
        /* Sleek custom nav bar styles */
        .custom-nav-wrapper {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-left: auto;
            margin-right: 16px;
            z-index: 999;
        }
        .custom-nav-link {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            user-select: none;
        }
        .custom-nav-kb {
            background: rgba(99, 102, 241, 0.12) !important;
            border: 1px solid rgba(99, 102, 241, 0.3) !important;
            color: #a5b4fc !important;
        }
        .custom-nav-kb:hover {
            background: rgba(99, 102, 241, 0.22) !important;
            border-color: #818cf8 !important;
            color: #c7d2fe !important;
            transform: translateY(-1px);
        }
        .custom-nav-dash {
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            color: #d1d5db !important;
        }
        .custom-nav-dash:hover {
            background: rgba(255, 255, 255, 0.08) !important;
            border-color: rgba(255, 255, 255, 0.15) !important;
            color: #fff !important;
            transform: translateY(-1px);
        }
        .custom-nav-new {
            background: rgba(16, 185, 129, 0.12) !important;
            border: 1px solid rgba(16, 185, 129, 0.3) !important;
            color: #34d399 !important;
            cursor: pointer;
        }
        .custom-nav-new:hover {
            background: rgba(16, 185, 129, 0.22) !important;
            border-color: #10b981 !important;
            color: #6ee7b7 !important;
            transform: translateY(-1px);
        }
        .custom-nav-hist {
            background: rgba(245, 158, 11, 0.12) !important;
            border: 1px solid rgba(245, 158, 11, 0.3) !important;
            color: #fbbf24 !important;
            cursor: pointer;
        }
        .custom-nav-hist:hover {
            background: rgba(245, 158, 11, 0.22) !important;
            border-color: #f59e0b !important;
            color: #fcd34d !important;
            transform: translateY(-1px);
        }
    `;
    const style = document.createElement('style');
    style.appendChild(document.createTextNode(css));
    document.head.appendChild(style);

    // Periodically hide the rewind action buttons
    setInterval(() => {
        const buttons = document.querySelectorAll('button');
        buttons.forEach(btn => {
            const text = btn.textContent.trim();
            if (text.startsWith('rewind-')) {
                btn.style.setProperty('display', 'none', 'important');
            }
        });
    }, 150);

    // Expose rewind trigger to window for the dropdown select's onchange event
    window.triggerRewind = function(checkpointId) {
        if (!checkpointId) return;
        console.log("Time Travel: Rewinding to checkpoint:", checkpointId);
        
        // Find the hidden button in the current document or parent document
        const allButtons = Array.from(document.querySelectorAll('button'))
            .concat(Array.from(window.parent.document.querySelectorAll('button')));
            
        const targetBtn = allButtons.find(btn => btn.textContent.trim() === 'rewind-' + checkpointId);
        if (targetBtn) {
            console.log("Clicking hidden rewind button:", targetBtn);
            targetBtn.click();
        } else {
            console.warn("Could not find rewind action button for checkpoint ID:", checkpointId);
        }
    };

    window.createNewChat = function() {
        console.log("Creating new campaign thread...");
        document.cookie = "chat_thread_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        document.cookie = "chat_page_reloaded=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        window.location.reload();
    };

    window.switchThread = function(threadId) {
        if (!threadId) return;
        console.log("Switching to campaign thread:", threadId);
        document.cookie = "chat_thread_id=" + threadId + "; max-age=" + (3600*24*30) + "; path=/;";
        document.cookie = "chat_page_reloaded=1; max-age=10; path=/;";
        window.location.reload();
    };

    window.triggerHistoryCommand = function() {
        // Find textarea and insert /history command
        const textarea = document.querySelector('textarea');
        if (textarea) {
            textarea.value = "/history";
            const event = new Event('input', { bubbles: true });
            textarea.dispatchEvent(event);
            
            setTimeout(() => {
                const sendButton = document.querySelector('button[type="submit"]') || document.querySelector('button[aria-label="Send message"]');
                if (sendButton) {
                    sendButton.click();
                }
            }, 100);
        }
    };

    // ============================================================
    // DYNAMIC HEADER NAV INJECTION (Dashboard & Knowledge Base links)
    // ============================================================
    function injectHeaderLinks() {
        // Find Chainlit's header or toolbar
        // Try searching inside iframe or parent document
        const header = document.querySelector('header');
        if (!header) return;

        // Check if already injected
        if (document.getElementById('custom-header-nav')) return;

        // Create the navigation elements
        const nav = document.createElement('div');
        nav.id = 'custom-header-nav';
        nav.className = 'custom-nav-wrapper';

        const btnNew = document.createElement('a');
        btnNew.className = 'custom-nav-link custom-nav-new';
        btnNew.innerHTML = '➕ Tạo Chiến dịch Mới';
        btnNew.onclick = window.createNewChat;

        const btnHist = document.createElement('a');
        btnHist.className = 'custom-nav-link custom-nav-hist';
        btnHist.innerHTML = '🗂️ Lịch sử Chiến dịch';
        btnHist.onclick = window.triggerHistoryCommand;

        const btnKB = document.createElement('a');
        btnKB.href = '/knowledge-base';
        btnKB.className = 'custom-nav-link custom-nav-kb';
        btnKB.innerHTML = '📁 Tài liệu RAG';

        const btnDash = document.createElement('a');
        btnDash.href = '/dashboard';
        btnDash.className = 'custom-nav-link custom-nav-dash';
        btnDash.innerHTML = '📊 Dashboard';

        nav.appendChild(btnNew);
        nav.appendChild(btnHist);
        nav.appendChild(btnKB);
        nav.appendChild(btnDash);

        // Find standard Chainlit header elements like settings button or logo wrapper to insert next to
        // Chainlit usually has a MuiToolbar containing the logo and control buttons
        const toolbar = header.querySelector('.MuiToolbar-root') || header.firstElementChild || header;
        
        // We append it before the settings/github button container (which is usually the last child)
        if (toolbar) {
            // Find if there is an existing button area on the right (often flexed)
            const rightControls = toolbar.querySelector('div[style*="flex-grow"], div:last-child');
            if (rightControls && rightControls !== toolbar) {
                // Insert right before the rightmost controls
                toolbar.insertBefore(nav, rightControls);
            } else {
                toolbar.appendChild(nav);
            }
        }
    }

    // Keep checking to ensure the links stay injected when React re-renders views
    setInterval(injectHeaderLinks, 300);
})();
