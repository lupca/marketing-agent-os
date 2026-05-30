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

        const btnKB = document.createElement('a');
        btnKB.href = '/knowledge-base';
        btnKB.className = 'custom-nav-link custom-nav-kb';
        btnKB.innerHTML = '📁 Tài liệu RAG';

        const btnDash = document.createElement('a');
        btnDash.href = '/dashboard';
        btnDash.className = 'custom-nav-link custom-nav-dash';
        btnDash.innerHTML = '📊 Dashboard';

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
