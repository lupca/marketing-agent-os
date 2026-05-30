// public/custom.js
(function() {
    console.log("Marketing Agent OS Custom JS Loaded.");

    // Style injection to hide any buttons with "rewind-" text
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
            // Fallback: alert user or handle fallback
        }
    };
})();
