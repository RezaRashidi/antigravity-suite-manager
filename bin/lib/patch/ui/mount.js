// Antigravity Multi-Account UI: Target Detection and Cascade Identification
(function initMountModule() {
    try {
        if (typeof window !== 'undefined') {
            if (window.__APP_CONFIG__) window.__APP_CONFIG__.devMode = true;
            const k = 'jetski.developer.customFlagOverrides';
            let f = {};
            try { f = JSON.parse(window.localStorage.getItem(k) || '{}'); } catch (_) {}
            if (!f['enable-conversation-forking'] || !f['enable-fork-in-new-worktree']) {
                f['enable-conversation-forking'] = true;
                f['enable-fork-in-new-worktree'] = true;
                window.localStorage.setItem(k, JSON.stringify(f));
            }
        }
    } catch (_) {}
    window.__antigravityDetectCascadeId = function(targetEl) {
        try {
            const ref = targetEl || document.getElementById('antigravity-account-pill') || document.querySelector('[data-testid="model-selector-trigger"]');
            const cv = ref?.closest('[data-testid="conversation-view"]') ||
                Array.from(document.querySelectorAll('[data-testid="conversation-view"]')).find(el => el.offsetParent !== null || el.getBoundingClientRect().height > 0) ||
                document.querySelector('[data-testid="conversation-view"]');
            const cvId = cv?.getAttribute('data-cascade-id');

            const sel = document.querySelector(
                '[data-testid*="conversation-row"][data-selected="true"], ' +
                '[data-testid="conversation-row-sidebar"][data-selected="true"], ' +
                '[data-testid="conversation-row-tab"][data-selected="true"], ' +
                '[data-testid="conversation-row-sidebar"].bg-sidebar-secondary'
            );
            const selId = sel?.getAttribute('data-cascade-id');

            if (selId && selId !== 'conversation' && selId !== 'default' && selId.length >= 8) {
                if (cv?.dataset?.agyDraftId) delete cv.dataset.agyDraftId;
                if (cv?.dataset?.agySessionId) delete cv.dataset.agySessionId;
                return selId;
            }

            if (cvId && cvId !== 'conversation' && cvId !== 'default' && cvId.length >= 8) {
                if (cv?.dataset?.agyDraftId) delete cv.dataset.agyDraftId;
                if (cv?.dataset?.agySessionId) delete cv.dataset.agySessionId;
                return cvId;
            }

            const pm = (window.location.pathname + window.location.hash).match(/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i) ||
                       (window.location.pathname + window.location.hash).match(/[a-f0-9-]{16,}/i);
            if (pm) {
                if (cv?.dataset?.agyDraftId) delete cv.dataset.agyDraftId;
                if (cv?.dataset?.agySessionId) delete cv.dataset.agySessionId;
                return pm[1] || pm[0];
            }

            if (cv) {
                if (!cv.dataset.agyDraftId) cv.dataset.agyDraftId = 'draft_' + Math.random().toString(36).slice(2, 10);
                return cv.dataset.agyDraftId;
            }
        } catch (_) {}
        return 'default';
    };

    window.__antigravityFindTarget = function() {
        try {
            const triggers = Array.from(document.querySelectorAll('[data-testid="model-selector-trigger"]'));
            const visible = triggers.filter(el => el.offsetParent !== null || el.getBoundingClientRect().width > 0);
            const trigger = visible.find(el => el.closest('[data-testid="conversation-view"]')) || visible[visible.length - 1] || triggers[triggers.length - 1];
            if (trigger) {
                const parent = trigger.parentElement?.closest('.flex.items-center') || trigger.parentElement;
                if (parent && parent !== trigger) {
                    let ref = trigger;
                    while (ref && ref.parentElement && ref.parentElement !== parent) ref = ref.parentElement;
                    return { target: parent, insertAfter: ref, floating: false };
                }
            }
            const tb = document.querySelector('[data-testid="conversation-view"] [data-testid="input-box-bottom-toolbar"], [data-testid="input-box-bottom-toolbar"]');
            if (tb) {
                const row = tb.querySelector('.flex.items-center') || tb;
                return { target: row, insertAfter: row.firstElementChild, floating: false };
            }
            const ft = document.querySelector('[data-testid="conversation-view"] [class*="input-footer"], [class*="input-footer"]');
            if (ft) {
                const row = ft.querySelector('.flex.items-center') || ft;
                return { target: row, floating: false };
            }
            const sb = document.querySelector('.items-container.right-items, .part.statusbar .right-items, [id="workbench.parts.statusbar"] .right-items, .part.statusbar');
            if (sb) return { target: sb, insertAfter: sb.firstElementChild, floating: false };
        } catch (_) {}
        return null;
    };
})();
