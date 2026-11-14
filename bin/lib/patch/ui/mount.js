// Antigravity Multi-Account UI: Target Detection and Cascade Identification
(function initMountModule() {
    try {
        if (typeof window !== 'undefined') {
            const envKey = 'jetski.developer.featureEnvironmentOverride';
            try { window.localStorage.removeItem(envKey); } catch (_) {}

            const k = 'jetski.developer.customFlagOverrides';
            let f = {};
            try { f = JSON.parse(window.localStorage.getItem(k) || '{}'); } catch (_) {}
            f['enable-conversation-forking'] = true;
            f['enable-fork-in-new-worktree'] = true;
            f['enable-fork-at-historical-step'] = true;
            delete f['enable-aux-pane-redesign'];
            delete f['enable-thought-editing'];
            delete f['enable-thought-steering-from-selection'];
            delete f['enable-battle-mode'];
            delete f['enable-battle-contrib-variants'];
            delete f['enable-battle-mode-custom-agents'];
            delete f['jetski-autonomous-mode'];
            delete f['labs-autonomous-mode'];
            try { window.localStorage.setItem(k, JSON.stringify(f)); } catch (_) {}
        }
    } catch (_) {}
    window.__antigravityDetectCascadeId = function(targetEl) {
        try {
            const ref = targetEl || document.getElementById('antigravity-account-pill') || document.querySelector('[data-testid="model-selector-trigger"]');
            const cv = ref?.closest?.('[data-testid="conversation-view"]') ||
                document.querySelector('[data-testid="conversation-view"]:not([hidden])') ||
                document.querySelector('[data-testid="conversation-view"]');
            const cvId = cv?.getAttribute?.('data-cascade-id');

            const sel = document.querySelector(
                '[data-testid*="conversation-row"][data-selected="true"], ' +
                '[data-testid="conversation-row-sidebar"][data-selected="true"], ' +
                '[data-testid="conversation-row-tab"][data-selected="true"], ' +
                '[data-testid="conversation-row-sidebar"].bg-sidebar-secondary'
            );
            const selId = sel?.getAttribute?.('data-cascade-id');

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
            const triggers = document.querySelectorAll('[data-testid="model-selector-trigger"]');
            if (triggers.length > 0) {
                let trigger = null;
                for (let i = 0; i < triggers.length; i++) {
                    const tr = triggers[i];
                    if (tr.closest('[data-testid="conversation-view"]')) {
                        trigger = tr;
                        break;
                    }
                }
                if (!trigger) trigger = triggers[triggers.length - 1];
                if (trigger) {
                    const parent = trigger.parentElement?.closest('.flex.items-center') || trigger.parentElement;
                    if (parent && parent !== trigger) {
                        let ref = trigger;
                        while (ref && ref.parentElement && ref.parentElement !== parent) ref = ref.parentElement;
                        return { target: parent, insertAfter: ref, floating: false };
                    }
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

    let footerHidden = false;
    let footerMo = null;
    function hideDevFooter() {
        if (footerHidden) return;
        try {
            const btns = document.querySelectorAll('button[title="Reset State"], button[title*="Reset"]');
            if (!btns.length) return;
            for (const btn of btns) {
                const bar = btn.closest('.shrink-0') || btn.closest('[data-screenshot-volatile]') || btn.closest('.border-t') || btn.parentElement;
                if (bar) {
                    bar.style.setProperty('display', 'none', 'important');
                    bar.style.setProperty('height', '0px', 'important');
                    bar.style.setProperty('visibility', 'hidden', 'important');
                    footerHidden = true;
                    if (footerMo) { footerMo.disconnect(); footerMo = null; }
                }
            }
        } catch (_) {}
    }
    window.__antigravityHideDevFooter = hideDevFooter;
    hideDevFooter();

    async function triggerDynamicModelRefresh() {
        if (typeof window.__customModelsRefreshChatSelector === 'function') {
            try { await window.__customModelsRefreshChatSelector(); } catch (_) {}
        }
        const csrfToken = window.__APP_CONFIG__?.csrfToken || window.__CODEIUM_CSRF__;
        if (csrfToken) {
            try {
                await fetch('/exa.language_server_pb.LanguageServerService/GetAvailableModels', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Connect-Protocol-Version': '1',
                        'x-codeium-csrf-token': csrfToken,
                    },
                    body: JSON.stringify({ forceRefresh: true }),
                });
            } catch (_) {}
        }

        try {
            const root = document.getElementById('root') || document.body.firstElementChild;
            if (!root) return;
            const keys = Object.keys(root);
            const fiberKey = keys.find(k => k.startsWith('__reactFiber$') || k.startsWith('__reactContainer$') || k.startsWith('__reactInternalInstance$'))
                || (root.firstElementChild && Object.keys(root.firstElementChild).find(k => k.startsWith('__reactFiber$') || k.startsWith('__reactContainer$') || k.startsWith('__reactInternalInstance$')));
            if (!fiberKey) return;
            const startNode = root[fiberKey] || (root.firstElementChild && root.firstElementChild[fiberKey]);
            if (!startNode) return;
            const rootNode = startNode.current || startNode;

            const queue = [rootNode];
            let client = null, store = null, visited = 0;
            while (queue.length > 0 && visited < 1000) {
                const node = queue.shift();
                visited++;
                if (!node) continue;
                if (!store) {
                    if (node.memoizedProps?.store?.dispatch) store = node.memoizedProps.store;
                    else if (node.stateNode?.store?.dispatch) store = node.stateNode.store;
                }
                if (!client) {
                    if (node.memoizedProps?.value && typeof node.memoizedProps.value.getUserStatus === 'function') {
                        client = node.memoizedProps.value;
                    } else if (node.memoizedProps?.client && typeof node.memoizedProps.client.getUserStatus === 'function') {
                        client = node.memoizedProps.client;
                    }
                }
                if (store && client) break;
                if (node.child) queue.push(node.child);
                if (node.sibling) queue.push(node.sibling);
            }

            if (store) {
                let statusObj = null;
                if (client && typeof client.getUserStatus === 'function') {
                    try {
                        const statusRes = await client.getUserStatus();
                        if (statusRes?.userStatus?.cascadeModelConfigData?.clientModelConfigs) {
                            statusObj = statusRes.userStatus;
                        }
                    } catch (_) {}
                }
                if (!statusObj && typeof store.getState === 'function') {
                    statusObj = store.getState()?.userStatus;
                }
                if (statusObj && statusObj.cascadeModelConfigData) {
                    store.dispatch({ type: 'userStatus/setUserStatus', payload: { ...statusObj } });
                }
            }
        } catch (err) {
            console.warn('[MultiAccount] Dynamic model refresh error:', err);
        }
    }

    window.__antigravityRefreshModels = triggerDynamicModelRefresh;
    window.addEventListener('antigravity:account-switched', () => {
        void triggerDynamicModelRefresh();
    });

    if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', hideDevFooter);
        }
        try {
            footerMo = new MutationObserver((mutations) => {
                if (footerHidden) {
                    if (footerMo) { footerMo.disconnect(); footerMo = null; }
                    return;
                }
                for (let i = 0; i < mutations.length; i++) {
                    const target = mutations[i].target;
                    // Ignore typing/input mutations completely
                    const el = target?.nodeType === 1 ? target : target?.parentElement;
                    if (el?.closest?.('textarea, input, [contenteditable], .monaco-editor, [data-lexical-editor], [data-testid*="input"], [role="textbox"]')) {
                        continue;
                    }
                    hideDevFooter();
                    break;
                }
            });
            if (document.body) footerMo.observe(document.body, { childList: true, subtree: true });
            else document.addEventListener('DOMContentLoaded', () => { if (document.body && !footerHidden && footerMo) footerMo.observe(document.body, { childList: true, subtree: true }); });
        } catch (_) {}

        // Optimize RTL Direction Engine if loaded: prevent full-chat BLOCKS re-scan while typing
        const optimizeRtl = () => {
            if (window.__antigravityRtlCore && !window.__antigravityRtlCore._agyWrapped && typeof window.__antigravityRtlCore.updateDir === 'function') {
                const origUpdateDir = window.__antigravityRtlCore.updateDir;
                window.__antigravityRtlCore._agyWrapped = true;
                window.__antigravityRtlCore.updateDir = function(forceRTL) {
                    const active = document.activeElement;
                    const isTyping = active && (active.tagName === 'TEXTAREA' || active.tagName === 'INPUT' || active.isContentEditable || active.closest?.('[contenteditable], .monaco-editor, [data-lexical-editor], [role="textbox"]'));
                    if (isTyping) {
                        const el = active.closest?.('[contenteditable="true"], textarea') || active;
                        const raw = el.tagName === 'TEXTAREA' ? el.value : el.textContent;
                        const text = (raw || '').replace(/[​-‏﻿]/g, '').trim();
                        if (text.length > 0) {
                            const dir = /^[^a-zA-Z]*[֑-߿יִ-﷽ﹰ-ﻼ]/.test(text) ? 'rtl' : 'ltr';
                            if (el.getAttribute('dir') !== dir) el.setAttribute('dir', dir);
                        } else if (el.hasAttribute('dir')) {
                            el.removeAttribute('dir');
                        }
                        return;
                    }
                    return origUpdateDir(forceRTL);
                };
            }
        };
        optimizeRtl();
        setTimeout(optimizeRtl, 1000);
        setTimeout(optimizeRtl, 3000);
    }
})();

