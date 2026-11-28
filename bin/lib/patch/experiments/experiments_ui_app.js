/**
 * Antigravity App (Standalone) Experiment Flags UI, Artifact Width & Fail-Open Context/Cost Pill.
 * Zero innerHTML (Trusted Types safe), styled identically to rtl_ui_app.js.
 */
(function (root) {
    'use strict';

    function mountAppExperiments(catalog, initialPayload, bootFlags, headless) {
        if (window.__ANTIGRAVITY_SUITE_EXPERIMENTS_LOADED__) return;
        window.__ANTIGRAVITY_SUITE_EXPERIMENTS_LOADED__ = true;

        const LIST = Array.isArray(catalog) ? catalog : [];
        const WIDTH_CSS = {
            default: '56rem',
            wide: '80rem',
            full: 'none',
        };

        const state = {
            flags: Object.assign({}, initialPayload?.flags || {}),
            config: Object.assign({ artifactWidth: 'default', sidebarChatLimit: 0, contextTarget: 0 }, initialPayload?.config || {}),
            uiSeen: Boolean(initialPayload?.uiSeen),
        };
        const boot = Object.assign({}, bootFlags || state.flags);
        const feat = root?.__antigravitySuiteFeatures || null;

        function el(tag, props, children) {
            const node = document.createElement(tag);
            if (props) {
                for (const [k, v] of Object.entries(props)) {
                    if (k === 'className') node.className = v;
                    else if (k === 'text') node.textContent = v;
                    else if (k === 'style') node.style.cssText = v;
                    else if (k === 'dataset') Object.assign(node.dataset, v);
                    else node.setAttribute(k, String(v));
                }
            }
            if (Array.isArray(children)) {
                for (const c of children) if (c) node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
            }
            return node;
        }

        function hasPendingRestart() {
            return LIST.some((item) => item.requiresRestart && Boolean(state.flags[item.id]) !== Boolean(boot[item.id]));
        }

        function syncLocalStorage() {
            try {
                const k = 'jetski.developer.customFlagOverrides';
                let cur = {};
                try { cur = JSON.parse(window.localStorage.getItem(k) || '{}'); } catch (_) {}
                if (!cur || typeof cur !== 'object' || Array.isArray(cur)) cur = {};
                for (const item of LIST) {
                    cur[item.id] = Boolean(state.flags[item.id]);
                }
                window.localStorage.setItem(k, JSON.stringify(cur));
                if ('enable-context-usage-indicator' in state.flags) {
                    window.localStorage.setItem('contextUsageIndicatorEnabled', state.flags['enable-context-usage-indicator'] ? 'true' : 'false');
                }
                globalThis.__SUITE_SIDEBAR_LIMIT = Number(state.config.sidebarChatLimit || 0);
                globalThis.__SUITE_CONTEXT_TARGET = Number(state.config.contextTarget || 0);
            } catch (_) {}
        }

        function applyArtifactWidthStyle() {
            let st = document.getElementById('suite-artifact-width-style');
            if (!st) {
                st = document.createElement('style');
                st.id = 'suite-artifact-width-style';
                (document.head || document.documentElement).appendChild(st);
            }
            const enabled = state.flags['configure-artifact-width'] !== false;
            const mode = enabled ? (state.config.artifactWidth || 'default') : 'default';
            const w = WIDTH_CSS[mode] || '';
            if (!enabled || mode === 'default' || !w) {
                try { document.documentElement.style.removeProperty('--max-artifact-width'); } catch (_) {}
                st.textContent = '';
                return;
            }
            try { document.documentElement.style.setProperty('--max-artifact-width', w, 'important'); } catch (_) {}
            st.textContent = `
                :root, html, body {
                    --max-artifact-width: ${w} !important;
                }
                .max-w-\\[var\\(--max-artifact-width\\,56rem\\)\\],
                [data-testid="artifact-view"] .max-w-3xl,
                [data-testid="artifact-view"] .prose,
                [data-testid="artifact-view"] .markdown-body {
                    max-width: ${w} !important;
                }
            `;
        }

        let saveTimer = null;
        function saveConfig(immediate) {
            syncLocalStorage();
            applyArtifactWidthStyle();
            if (feat) feat.applyCompactLayout(Boolean(state.flags['enable-compact-layout']));
            const flush = () => {
                saveTimer = null;
                const payload = { flags: state.flags, config: state.config, uiSeen: state.uiSeen };
                try { console.log('SAVE_EXPERIMENTS_CONFIG|' + JSON.stringify(payload)); } catch (_) {}
                try {
                    fetch('http://127.0.0.1:41999/api/experiments', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    }).catch(() => {});
                } catch (_) {}
            };
            if (saveTimer) clearTimeout(saveTimer);
            if (immediate) flush();
            else saveTimer = setTimeout(flush, 180);
        }

        function triggerRestart() {
            saveConfig(true);
            if (window.antigravityMultiAccount && typeof window.antigravityMultiAccount.relaunchApp === 'function') {
                Promise.resolve(window.antigravityMultiAccount.relaunchApp()).catch(() => {
                    try { console.log('SUITE_RELAUNCH_APP'); } catch (_) {}
                });
                return;
            }
            try { console.log('SUITE_RELAUNCH_APP'); } catch (_) {}
        }

        syncLocalStorage();
        applyArtifactWidthStyle();
        if (feat) {
            feat.applyCompactLayout(Boolean(state.flags['enable-compact-layout']));
            feat.mountFileContextMenu(() => state.flags['enable-file-context-menu'] !== false);
            feat.mountFullTextSearch(() => state.flags['enable-fulltext-search'] !== false);
            feat.mountSpeedTelemetry(() => state.flags['enable-speed-telemetry'] !== false);
        }
        if (headless) return;

        function ensureStyles() {
            if (document.getElementById('suite-flags-widget-style')) return;
            const st = document.createElement('style');
            st.id = 'suite-flags-widget-style';
            st.textContent = `
                #suite-flags-topbar-btn {
                    font-family: ui-sans-serif, system-ui, -apple-system, sans-serif !important;
                    line-height: 1 !important;
                }
                #suite-flags-dropdown-panel {
                    position: fixed;
                    z-index: 999999;
                    width: 344px;
                    max-height: min(540px, calc(100vh - 56px));
                    overflow-y: auto;
                    padding: 12px;
                    border-radius: 10px;
                    direction: ltr;
                    app-region: no-drag;
                    -webkit-app-region: no-drag;
                    font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
                    font-size: 12.5px;
                    background-color: var(--popover, var(--card, #18181b));
                    color: var(--popover-foreground, var(--foreground, #f4f4f5));
                    border: 1px solid var(--border, rgba(255, 255, 255, 0.14));
                    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
                    box-sizing: border-box;
                    transition: transform 0.14s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.14s ease;
                    transform-origin: top right;
                }
                #suite-flags-dropdown-panel * {
                    app-region: no-drag;
                    -webkit-app-region: no-drag;
                }
                #suite-flags-dropdown-panel.ag-exp-hidden {
                    transform: scale(0.95);
                    opacity: 0;
                    pointer-events: none;
                    visibility: hidden;
                }
                #suite-flags-dropdown-panel.ag-exp-visible {
                    transform: scale(1);
                    opacity: 1;
                    pointer-events: auto;
                    visibility: visible;
                }
                .ag-exp-sep { height: 1px; background: var(--border, rgba(255,255,255,0.1)); margin: 8px -12px; }
                .ag-exp-grp { font-size: 10.5px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; opacity: 0.6; margin: 6px 0 4px; }
                .ag-exp-item { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 4px 0; }
                .ag-exp-meta { display: flex; flex-direction: column; min-width: 0; }
                .ag-exp-name { font-size: 12px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
                .ag-exp-desc { font-size: 10.5px; opacity: 0.65; line-height: 1.25; }
                .ag-exp-badge { font-size: 9.5px; padding: 0 5px; border-radius: 999px; background: rgba(245, 158, 11, 0.16); color: #f59e0b; margin-left: 5px; }
                .ag-exp-switch { position: relative; width: 32px; height: 18px; border-radius: 999px; border: none; padding: 0; cursor: pointer; flex-shrink: 0; transition: background-color 0.15s ease; background: #52525b; }
                .ag-exp-switch[aria-checked="true"] { background: #3b82f6; }
                .ag-exp-knob { position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%; background: #fff; transition: transform 0.15s ease; pointer-events: none; }
                .ag-exp-switch[aria-checked="true"] .ag-exp-knob { transform: translateX(14px); }
                .ag-exp-btn { border: 1px solid var(--border, rgba(255,255,255,0.16)); background: transparent; color: inherit; border-radius: 6px; padding: 4px 8px; font-size: 11px; cursor: pointer; }
                .ag-exp-btn:hover { background: var(--muted, rgba(255,255,255,0.08)); }
                .ag-exp-restart { background: #f59e0b; color: #18181b; border: none; border-radius: 6px; padding: 5px 10px; font-size: 11.5px; font-weight: 600; cursor: pointer; }
                .ag-exp-restart:hover { filter: brightness(1.06); }
                .ag-exp-dot { width: 6px; height: 6px; border-radius: 50%; background: #f59e0b; display: none; }
            `;
            (document.head || document.documentElement).appendChild(st);
        }

        function initPanel() {
            ensureStyles();

            const dot = el('span', { className: 'ag-exp-dot' });
            const btnLabel = el('span', { text: 'Flags', style: 'opacity:0.9;' });
            const topBtn = el('button', {
                id: 'suite-flags-topbar-btn',
                type: 'button',
                title: 'Experiment Flags & Context/Cost Settings',
                className: 'focus-visible:outline-hidden relative inline-flex cursor-pointer items-center justify-center gap-1 whitespace-nowrap rounded-md px-2 py-1 text-xs transition-colors hover:bg-muted/60',
                style: 'app-region:no-drag;-webkit-app-region:no-drag;height:26px;',
            }, [btnLabel, dot]);

            const usageBtn = el('button', {
                id: 'suite-usage-topbar-btn',
                type: 'button',
                title: 'Multi-Account Usage & Spend Dashboard',
                className: 'focus-visible:outline-hidden relative inline-flex cursor-pointer items-center justify-center gap-1 whitespace-nowrap rounded-md px-2 py-1 text-xs transition-colors hover:bg-muted/60',
                style: 'app-region:no-drag;-webkit-app-region:no-drag;height:26px;',
            }, [el('span', { text: 'Usage', style: 'opacity:0.88;' })]);
            usageBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (feat) feat.openUsageDashboardModal('all');
            });

            const wrapper = el('div', {
                id: 'suite-flags-topbar-wrapper',
                className: 'relative flex items-center gap-1',
                style: 'app-region:no-drag;-webkit-app-region:no-drag;',
            }, [usageBtn, topBtn]);

            const switchRefs = new Map();
            const widthBtns = new Map();
            const sbLimitBtns = new Map();
            const ctxTargetBtns = new Map();
            let widthRow = null;
            let restartBanner = null;

            const panelBody = el('div', {});
            const groups = [
                { key: 'ui', title: 'Editor & UI (Live)' },
                { key: 'fork', title: 'Conversation Forking' },
                { key: 'agent', title: 'Agent & Telemetry (Restart Required)' },
            ];

            for (const g of groups) {
                const items = LIST.filter((it) => it.group === g.key);
                if (!items.length) continue;
                panelBody.appendChild(el('div', { className: 'ag-exp-grp', text: g.title }));
                for (const it of items) {
                    const checked = Boolean(state.flags[it.id]);
                    const sw = el('button', {
                        type: 'button',
                        role: 'switch',
                        'aria-checked': checked ? 'true' : 'false',
                        className: 'ag-exp-switch',
                    }, [el('span', { className: 'ag-exp-knob' })]);
                    sw.addEventListener('click', () => {
                        state.flags[it.id] = !state.flags[it.id];
                        saveConfig(false);
                        refreshUi();
                    });
                    switchRefs.set(it.id, sw);

                    const nameEl = el('div', { className: 'ag-exp-name' }, [el('span', { text: it.label })]);
                    if (it.requiresRestart) nameEl.appendChild(el('span', { className: 'ag-exp-badge', text: 'Restart' }));
                    const row = el('div', { className: 'ag-exp-item' }, [
                        el('div', { className: 'ag-exp-meta' }, [nameEl, el('div', { className: 'ag-exp-desc', text: it.description })]),
                        sw,
                    ]);
                    panelBody.appendChild(row);

                    if (it.hasWidthOption) {
                        const segWrap = el('div', { style: 'display:flex;gap:4px;' });
                        for (const opt of [
                            { id: 'default', label: 'Default' },
                            { id: 'wide', label: 'Wide' },
                            { id: 'full', label: 'Full' },
                        ]) {
                            const wb = el('button', { type: 'button', className: 'ag-exp-btn', text: opt.label });
                            wb.addEventListener('click', () => {
                                state.config.artifactWidth = opt.id;
                                saveConfig(false);
                                refreshUi();
                            });
                            widthBtns.set(opt.id, wb);
                            segWrap.appendChild(wb);
                        }
                        widthRow = el('div', { style: 'display:flex;align-items:center;justify-content:space-between;padding:2px 0 6px;' }, [
                            el('span', { style: 'font-size:11px;opacity:0.75;', text: 'Artifact Pane Width' }),
                            segWrap,
                        ]);
                        panelBody.appendChild(widthRow);
                    }
                }
            }

            // Sidebar Chats / Project selector & Experimental Context Target selector
            const sbWrap = el('div', { style: 'display:flex;gap:4px;' });
            for (const opt of [
                { v: 0, l: 'Default (6)' },
                { v: 10, l: '10' },
                { v: 20, l: '20' },
                { v: -1, l: 'All' },
            ]) {
                const b = el('button', { type: 'button', className: 'ag-exp-btn', text: opt.l });
                b.addEventListener('click', () => { state.config.sidebarChatLimit = opt.v; saveConfig(false); refreshUi(); });
                sbLimitBtns.set(opt.v, b);
                sbWrap.appendChild(b);
            }
            panelBody.appendChild(el('div', { className: 'ag-exp-grp', text: 'Sidebar & Context Caps' }));
            panelBody.appendChild(el('div', { style: 'display:flex;align-items:center;justify-content:space-between;padding:2px 0 4px;' }, [
                el('span', { style: 'font-size:11px;opacity:0.78;', text: 'Chats / Project' }),
                sbWrap,
            ]));

            const ctWrap = el('div', { style: 'display:flex;gap:4px;' });
            for (const opt of [
                { v: 0, l: 'Default' },
                { v: 256000, l: '256K' },
                { v: 500000, l: '500K' },
                { v: 1000000, l: '1M' },
            ]) {
                const b = el('button', { type: 'button', className: 'ag-exp-btn', text: opt.l });
                b.addEventListener('click', () => { state.config.contextTarget = opt.v; saveConfig(false); refreshUi(); });
                ctxTargetBtns.set(opt.v, b);
                ctWrap.appendChild(b);
            }
            panelBody.appendChild(el('div', { style: 'display:flex;align-items:center;justify-content:space-between;padding:2px 0 6px;' }, [
                el('span', { style: 'font-size:11px;opacity:0.78;', text: 'Context Target' }),
                ctWrap,
            ]));

            const restartBtn = el('button', { type: 'button', className: 'ag-exp-restart', text: 'Restart App' });
            restartBtn.addEventListener('click', triggerRestart);
            restartBanner = el('div', {
                style: 'display:none;align-items:center;justify-content:space-between;gap:8px;padding:8px;border-radius:8px;background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);margin-top:8px;',
            }, [
                el('span', { style: 'font-size:11px;color:#fbbf24;', text: 'Server/boot flag changed — restart to apply' }),
                restartBtn,
            ]);

            const enableAllBtn = el('button', { type: 'button', className: 'ag-exp-btn', text: 'Enable All Safe' });
            enableAllBtn.addEventListener('click', () => {
                for (const it of LIST) state.flags[it.id] = true;
                saveConfig(true);
                refreshUi();
            });
            const quickRestartBtn = el('button', { type: 'button', className: 'ag-exp-btn', text: 'Restart App' });
            quickRestartBtn.addEventListener('click', triggerRestart);

            const panel = el('div', {
                id: 'suite-flags-dropdown-panel',
                className: 'ag-exp-hidden',
            }, [
                el('div', { style: 'display:flex;align-items:center;justify-content:space-between;' }, [
                    el('span', { style: 'font-size:11px;font-weight:700;letter-spacing:0.04em;', text: 'ANTIGRAVITY EXPERIMENTS' }),
                    el('span', { style: 'font-size:10.5px;opacity:0.6;', text: `${LIST.length} Flags` }),
                ]),
                el('div', { className: 'ag-exp-sep' }),
                panelBody,
                restartBanner,
                el('div', { className: 'ag-exp-sep' }),
                el('div', { style: 'display:flex;align-items:center;justify-content:space-between;gap:6px;' }, [
                    enableAllBtn,
                    quickRestartBtn,
                ]),
            ]);

            function refreshUi() {
                for (const [id, sw] of switchRefs.entries()) {
                    sw.setAttribute('aria-checked', state.flags[id] ? 'true' : 'false');
                }
                if (widthRow) {
                    const enabled = state.flags['configure-artifact-width'] !== false;
                    widthRow.style.opacity = enabled ? '1' : '0.4';
                    widthRow.style.pointerEvents = enabled ? 'auto' : 'none';
                    for (const [wid, wb] of widthBtns.entries()) {
                        const active = state.config.artifactWidth === wid;
                        wb.style.borderColor = active ? '#3b82f6' : '';
                        wb.style.background = active ? 'rgba(59,130,246,0.18)' : '';
                    }
                }
                for (const [sv, sb] of sbLimitBtns.entries()) {
                    const active = Number(state.config.sidebarChatLimit || 0) === sv;
                    sb.style.borderColor = active ? '#3b82f6' : '';
                    sb.style.background = active ? 'rgba(59,130,246,0.18)' : '';
                }
                for (const [cv, cb] of ctxTargetBtns.entries()) {
                    const active = Number(state.config.contextTarget || 0) === cv;
                    cb.style.borderColor = active ? '#3b82f6' : '';
                    cb.style.background = active ? 'rgba(59,130,246,0.18)' : '';
                }
                const pending = hasPendingRestart();
                dot.style.display = pending ? 'inline-block' : 'none';
                if (restartBanner) restartBanner.style.display = pending ? 'flex' : 'none';
            }

            let isOpen = false;
            function positionPanel() {
                const r = topBtn.getBoundingClientRect();
                panel.style.top = (r.bottom + 6) + 'px';
                panel.style.left = Math.max(8, Math.min(window.innerWidth - 352, r.right - 344)) + 'px';
            }
            function closePanel() {
                isOpen = false;
                panel.classList.remove('ag-exp-visible');
                panel.classList.add('ag-exp-hidden');
            }
            topBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (isOpen) { closePanel(); return; }
                refreshUi();
                positionPanel();
                isOpen = true;
                panel.classList.remove('ag-exp-hidden');
                panel.classList.add('ag-exp-visible');
                if (!state.uiSeen) { state.uiSeen = true; saveConfig(false); }
            });
            document.addEventListener('click', (e) => {
                if (isOpen && !panel.contains(e.target) && !wrapper.contains(e.target)) closePanel();
            });
            document.addEventListener('keydown', (e) => {
                if (isOpen && e.key === 'Escape') closePanel();
            });
            window.addEventListener('resize', () => { if (isOpen) positionPanel(); });

            function attach() {
                if (!document.getElementById('suite-flags-topbar-wrapper')) {
                    const rtlWrap = document.getElementById('rtl-topbar-wrapper');
                    if (rtlWrap && rtlWrap.parentElement) {
                        rtlWrap.parentElement.insertBefore(wrapper, rtlWrap);
                    } else {
                        const anchor =
                            document.querySelector('[data-testid="titlebar-more-actions"]') ||
                            document.querySelector('[data-testid="install-editor"]');
                        if (anchor && anchor.parentElement) anchor.parentElement.appendChild(wrapper);
                    }
                }
                if (!document.getElementById('suite-flags-dropdown-panel') && document.body) {
                    document.body.appendChild(panel);
                }
            }

            refreshUi();
            attach();
            const obs = new MutationObserver(() => attach());
            if (document.body) obs.observe(document.body, { childList: true, subtree: true });
        }

        const waitTimer = setInterval(() => {
            if (document.getElementById('root')?.children?.length && (document.querySelector('#rtl-topbar-wrapper') || document.querySelector('[data-testid="titlebar-more-actions"]') || document.querySelector('[data-testid="install-editor"]'))) {
                clearInterval(waitTimer);
                initPanel();
            }
        }, 250);
    }

    if (root) root.__antigravityMountAppExperiments = mountAppExperiments;
})(typeof window !== 'undefined' ? window : globalThis);
