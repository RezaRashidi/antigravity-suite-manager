// Antigravity Multi-Account UI: Target Detection and Cascade Identification
(function initMountModule() {
    window.__antigravityDetectCascadeId = function() {
        const cv = document.querySelector('[data-testid="conversation-view"][data-cascade-id]');
        const cvId = cv?.getAttribute('data-cascade-id');
        if (cvId) return cvId;

        const sel = document.querySelector('[data-testid="conversation-row-sidebar"][data-selected="true"], [data-testid="conversation-row-sidebar"].bg-sidebar-secondary');
        const selId = sel?.getAttribute('data-cascade-id');
        if (selId) return selId;

        const pm = window.location.pathname.match(/[a-f0-9-]{16,}/i);
        if (pm) return pm[0];
        const hm = window.location.hash.match(/[a-f0-9-]{16,}/i);
        if (hm) return hm[0];
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
