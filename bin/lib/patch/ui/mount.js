// Antigravity Multi-Account UI: Target Detection and Cascade Identification
(function initMountModule() {
    window.__antigravityDetectCascadeId = function() {
        const hashMatch = window.location.hash.match(/[a-f0-9-]{16,}/i);
        if (hashMatch) return hashMatch[0];
        const pathMatch = window.location.pathname.match(/[a-f0-9-]{16,}/i);
        if (pathMatch) return pathMatch[0];

        const dataEl = document.querySelector('[data-cascade-id], [data-conversation-id], [data-session-id], [data-chat-id]');
        if (dataEl) {
            const id = dataEl.getAttribute('data-cascade-id') || dataEl.getAttribute('data-conversation-id') ||
                       dataEl.getAttribute('data-session-id') || dataEl.getAttribute('data-chat-id');
            if (id) return id;
        }

        const activeItem = document.querySelector('[class*="conversation"][class*="active"], [class*="cascade"][class*="active"], [class*="chat"][class*="selected"], [aria-selected="true"]');
        if (activeItem) {
            const match = (activeItem.id + ' ' + activeItem.className + ' ' + (activeItem.getAttribute('data-id') || '')).match(/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/i);
            if (match) return match[0];
            const titleEl = activeItem.querySelector('[class*="title"], span');
            if (titleEl && titleEl.textContent) return 'chat-' + titleEl.textContent.trim().slice(0, 30);
        }
        return 'default';
    };

    window.__antigravityFindTarget = function() {
        const buttons = Array.from(document.querySelectorAll('button'));
        for (const btn of buttons) {
            const txt = (btn.textContent || '').trim();
            if (
                txt.includes('Flash') || txt.includes('Pro') || txt.includes('Claude') ||
                txt.includes('Gemini') || txt.includes('Sonnet') || txt.includes('GPT') ||
                txt.includes('Auto') || txt.includes('DeepSeek') || txt.includes('Thinking') ||
                btn.getAttribute('data-testid') === 'model-selector'
            ) {
                if (btn.parentElement) return { target: btn.parentElement, insertAfter: btn, floating: false };
            }
        }
        const prompt = document.querySelector('textarea, [contenteditable="true"], [role="textbox"]');
        if (prompt) {
            const box = prompt.closest('form, [class*="prompt"], [class*="input"], [class*="cascade"]') || prompt.parentElement;
            if (box) {
                const footer = box.querySelector('[class*="input-footer"], [class*="footer"], div[class*="items-center"][class*="min-w-0"]') ||
                               box.querySelector('div[class*="items-center"]');
                if (footer) return { target: footer, floating: false };
            }
        }
        const footers = document.querySelectorAll('div[class*="input-footer"]');
        for (const f of footers) {
            const group = f.querySelector('div[class*="items-center"]') || f.querySelector('div[class*="flex-1"]') || f;
            if (group) return { target: group, floating: false };
        }
        return null;
    };
})();
