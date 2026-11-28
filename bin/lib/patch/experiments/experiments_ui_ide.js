/**
 * Antigravity IDE Experiment Flags UI, Artifact Width & Prompt-Bar Context/Cost Pill.
 * Pure DOM builders (Trusted Types safe, zero innerHTML).
 */
(function (root) {
    'use strict';

    function mountIdeExperiments(catalog, initialPayload, bootFlags, headless) {
        if (window.__ANTIGRAVITY_SUITE_IDE_EXPERIMENTS_LOADED__) return;
        window.__ANTIGRAVITY_SUITE_IDE_EXPERIMENTS_LOADED__ = true;

        const LIST = Array.isArray(catalog) ? catalog : [];
        const WIDTH_CSS = { default: '56rem', wide: '80rem', full: 'none' };
        const state = {
            flags: Object.assign({}, initialPayload?.flags || {}),
            config: Object.assign({ artifactWidth: 'default', sidebarChatLimit: 0, contextTarget: 0 }, initialPayload?.config || {}),
            uiSeen: Boolean(initialPayload?.uiSeen),
        };
        const boot = Object.assign({}, bootFlags || state.flags);
        const feat = root?.__antigravitySuiteFeatures || null;

        function el(tag, css, children, attrs) {
            const node = document.createElement(tag);
            if (css) node.style.cssText = css;
            if (attrs) {
                for (const [k, v] of Object.entries(attrs)) {
                    if (k === 'text') node.textContent = v;
                    else if (k === 'className') node.className = v;
                    else node.setAttribute(k, String(v));
                }
            }
            if (Array.isArray(children)) {
                for (const c of children) if (c) node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
            } else if (typeof children === 'string') {
                node.textContent = children;
            }
            return node;
        }

        function hasPendingRestart() {
            return LIST.some((it) => it.requiresRestart && Boolean(state.flags[it.id]) !== Boolean(boot[it.id]));
        }

        function syncLocalStorage() {
            try {
                const k = 'jetski.developer.customFlagOverrides';
                let cur = {};
                try { cur = JSON.parse(window.localStorage.getItem(k) || '{}'); } catch (_) {}
                if (!cur || typeof cur !== 'object' || Array.isArray(cur)) cur = {};
                for (const it of LIST) cur[it.id] = Boolean(state.flags[it.id]);
                window.localStorage.setItem(k, JSON.stringify(cur));
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
            st.textContent = `:root, html, body { --max-artifact-width: ${w} !important; } .max-w-\\[var\\(--max-artifact-width\\,56rem\\)\\], [data-testid="artifact-view"] .max-w-3xl, [data-testid="artifact-view"] .prose, [data-testid="artifact-view"] .markdown-body { max-width: ${w} !important; }`;
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
            try { console.log('SUITE_RELAUNCH_IDE'); } catch (_) {}
        }

        syncLocalStorage();
        applyArtifactWidthStyle();
        if (feat) {
            feat.applyCompactLayout(Boolean(state.flags['enable-compact-layout']));
            feat.mountFileContextMenu(() => state.flags['enable-file-context-menu'] !== false);
            feat.mountFullTextSearch(() => state.flags['enable-fulltext-search'] !== false);
            feat.mountSpeedTelemetry(() => state.flags['enable-speed-telemetry'] !== false);
        }

        // Prompt-bar lightweight Context Window + Cost Pill inside chat / jetski frames
        function mountContextCostPill() {
            if (!state.flags['enable-context-usage-indicator'] && !state.flags['enable-cost-accumulator']) return;
            const fmtTok = (n) => {
                if (n >= 1e6) return (n / 1e6).toFixed(2).replace(/\.?0+$/, '') + 'M';
                if (n >= 1e3) return (n / 1e3).toFixed(n >= 1e5 ? 0 : 1).replace(/\.0$/, '') + 'k';
                return String(Math.round(n || 0));
            };
            const fmtUsd = (v) => (v >= 1 ? '$' + v.toFixed(2) : '$' + Number(v || 0).toFixed(4));

            let latestData = null;
            let popOpen = false;
            let popEl = null;

            const ringFg = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            const ringBg = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('width', '14');
            svg.setAttribute('height', '14');
            svg.setAttribute('viewBox', '0 0 16 16');
            svg.style.cssText = 'transform:rotate(-90deg);flex-shrink:0;';
            const r = 6;
            const c = 2 * Math.PI * r;
            ringBg.setAttribute('cx', '8'); ringBg.setAttribute('cy', '8'); ringBg.setAttribute('r', String(r));
            ringBg.setAttribute('fill', 'none'); ringBg.setAttribute('stroke', 'currentColor'); ringBg.setAttribute('stroke-opacity', '0.25'); ringBg.setAttribute('stroke-width', '2');
            ringFg.setAttribute('cx', '8'); ringFg.setAttribute('cy', '8'); ringFg.setAttribute('r', String(r));
            ringFg.setAttribute('fill', 'none'); ringFg.setAttribute('stroke', '#3b82f6'); ringFg.setAttribute('stroke-width', '2');
            ringFg.setAttribute('stroke-dasharray', String(c)); ringFg.setAttribute('stroke-dashoffset', String(c)); ringFg.setAttribute('stroke-linecap', 'round');
            svg.appendChild(ringBg);
            svg.appendChild(ringFg);

            const txtSpan = el('span', 'font-variant-numeric:tabular-nums;font-size:11px;font-weight:500;', '0%');
            const pill = el('button', 'display:inline-flex;align-items:center;gap:5px;height:24px;padding:0 7px;border-radius:999px;border:1px solid rgba(128,128,128,0.22);background:transparent;color:inherit;cursor:pointer;font-size:11px;opacity:0.88;margin-left:4px;', [svg, txtSpan], { id: 'suite-ide-context-cost-pill', type: 'button', title: 'Context Window & Session Cost' });

            function closePop() {
                popOpen = false;
                if (popEl) { popEl.remove(); popEl = null; }
            }

            function renderPop() {
                if (!popEl) return;
                popEl.replaceChildren();
                const d = latestData || { currentContextTokens: 0, contextLimit: 200000, contextPct: 0, totalInputTokens: 0, totalCacheReadTokens: 0, totalOutputTokens: 0, cacheHitPct: 0, sessionCostUsd: 0, cacheSavingsUsd: 0, model: 'Unknown' };
                popEl.appendChild(el('div', 'display:flex;justify-content:space-between;font-weight:600;margin-bottom:6px;', [
                    el('span', '', 'Context & Cost'),
                    el('span', 'opacity:0.8;', `${d.contextPct || 0}%`),
                ]));
                const bar = el('div', 'height:6px;width:100%;border-radius:999px;background:rgba(128,128,128,0.25);overflow:hidden;margin-bottom:8px;');
                const pct = Math.min(100, Number(d.contextPct || 0));
                const col = pct >= 85 ? '#ef4444' : pct >= 65 ? '#f59e0b' : '#3b82f6';
                bar.appendChild(el('div', `height:100%;width:${pct}%;background:${col};`));
                popEl.appendChild(bar);
                const rows = [
                    ['Model', String(d.model || 'Unknown')],
                    ['Context', `${fmtTok(d.currentContextTokens)} / ${fmtTok(d.contextLimit)}`],
                    ['Input / Cache', `${fmtTok(d.totalInputTokens)} / ${fmtTok(d.totalCacheReadTokens)} (${d.cacheHitPct || 0}%)`],
                    ['Output', fmtTok(d.totalOutputTokens)],
                    ['Session Cost', fmtUsd(d.sessionCostUsd)],
                    ['Cache Saved', fmtUsd(d.cacheSavingsUsd)],
                ];
                for (const [k, v] of rows) {
                    popEl.appendChild(el('div', 'display:flex;justify-content:space-between;gap:12px;padding:2px 0;font-size:11.5px;', [
                        el('span', 'opacity:0.7;', k),
                        el('span', 'font-variant-numeric:tabular-nums;font-weight:500;', v),
                    ]));
                }
            }

            pill.addEventListener('click', (e) => {
                e.stopPropagation();
                if (popOpen) { closePop(); return; }
                popOpen = true;
                popEl = el('div', 'position:fixed;z-index:999999;width:270px;padding:10px 12px;border-radius:10px;background:var(--vscode-editorWidget-background,#1e1e1e);color:var(--vscode-editorWidget-foreground,#e4e4e7);border:1px solid var(--vscode-editorWidget-border,rgba(255,255,255,0.16));box-shadow:0 10px 28px rgba(0,0,0,0.45);font-size:12px;direction:ltr;');
                document.body.appendChild(popEl);
                renderPop();
                const rect = pill.getBoundingClientRect();
                popEl.style.left = Math.max(8, Math.min(window.innerWidth - 278, rect.left)) + 'px';
                popEl.style.top = Math.max(8, rect.top - popEl.offsetHeight - 8) + 'px';
            });
            document.addEventListener('click', (e) => { if (popOpen && popEl && !popEl.contains(e.target) && !pill.contains(e.target)) closePop(); });

            function detectCascade() {
                try { if (typeof window.__antigravityDetectCascadeId === 'function') return window.__antigravityDetectCascadeId(pill); } catch (_) {}
                const m = (window.location.href || '').match(/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/i);
                return m ? m[0] : '';
            }

            async function refreshPill() {
                const cid = detectCascade();
                try {
                    const res = await fetch(`http://127.0.0.1:41999/api/usage/active?cascadeId=${encodeURIComponent(cid || '')}`);
                    if (!res.ok) return;
                    const data = await res.json();
                    latestData = data;
                    const ratio = Math.min(1, Number(data.contextPct || 0) / 100);
                    ringFg.setAttribute('stroke-dashoffset', String(c * (1 - ratio)));
                    ringFg.setAttribute('stroke', ratio >= 0.85 ? '#ef4444' : ratio >= 0.65 ? '#f59e0b' : '#3b82f6');
                    const parts = [];
                    if (state.flags['enable-context-usage-indicator']) parts.push(`${Math.round(Number(data.contextPct || 0))}%`);
                    if (state.flags['enable-cost-accumulator'] && Number(data.sessionCostUsd || 0) > 0) parts.push(fmtUsd(data.sessionCostUsd));
                    txtSpan.textContent = parts.join(' · ') || '0%';
                    if (popOpen) renderPop();
                } catch (_) {}
            }

            function attachPill() {
                if (document.getElementById('suite-ide-context-cost-pill')) return;
                if (document.querySelector('[data-suite-context-indicator="native"]')) return;
                const anchor = document.getElementById('antigravity-account-pill') || document.querySelector('[data-testid="model-selector-trigger"]');
                if (anchor && anchor.parentElement) {
                    anchor.parentElement.insertBefore(pill, anchor.nextSibling);
                    void refreshPill();
                }
            }
            attachPill();
            setInterval(attachPill, 1500);
            setInterval(refreshPill, 4500);
        }

        if (headless) {
            mountContextCostPill();
            return;
        }
        mountContextCostPill();

        // Main workbench statusbar UI + floating flags panel
        const switchRefs = new Map();
        const widthBtns = new Map();
        const sbLimitBtns = new Map();
        const ctxTargetBtns = new Map();
        let widthRow = null;
        let restartBanner = null;
        let isOpen = false;

        function closePanel() {
            const p = document.getElementById('antigravity-flags-settings-panel');
            if (p) p.style.display = 'none';
            isOpen = false;
        }

        function syncUi() {
            const btn = document.getElementById('antigravity-flags-statusbar-btn');
            const pending = hasPendingRestart();
            if (btn) {
                btn.textContent = pending ? '⚙ Flags •' : '⚙ Flags';
                btn.style.color = pending ? '#f59e0b' : '#38bdf8';
            }
            for (const [id, sw] of switchRefs.entries()) {
                const on = Boolean(state.flags[id]);
                sw.style.background = on ? 'var(--vscode-button-background, #3b82f6)' : '#64748b';
                const knob = sw.firstElementChild;
                if (knob) knob.style.left = on ? '19px' : '3px';
            }
            if (widthRow) {
                const enabled = state.flags['configure-artifact-width'] !== false;
                widthRow.style.opacity = enabled ? '1' : '0.4';
                widthRow.style.pointerEvents = enabled ? 'auto' : 'none';
                for (const [wid, wb] of widthBtns.entries()) {
                    const active = state.config.artifactWidth === wid;
                    wb.style.borderColor = active ? '#3b82f6' : 'rgba(128,128,128,0.35)';
                    wb.style.background = active ? 'rgba(59,130,246,0.22)' : 'transparent';
                }
            }
            for (const [sv, sb] of sbLimitBtns.entries()) {
                const active = Number(state.config.sidebarChatLimit || 0) === sv;
                sb.style.borderColor = active ? '#3b82f6' : 'rgba(128,128,128,0.35)';
                sb.style.background = active ? 'rgba(59,130,246,0.22)' : 'transparent';
            }
            for (const [cv, cb] of ctxTargetBtns.entries()) {
                const active = Number(state.config.contextTarget || 0) === cv;
                cb.style.borderColor = active ? '#3b82f6' : 'rgba(128,128,128,0.35)';
                cb.style.background = active ? 'rgba(59,130,246,0.22)' : 'transparent';
            }
            if (restartBanner) restartBanner.style.display = pending ? 'flex' : 'none';
        }

        function ensurePanel() {
            let panel = document.getElementById('antigravity-flags-settings-panel');
            if (panel) return panel;

            const body = el('div', 'display:flex;flex-direction:column;gap:8px;max-height:420px;overflow-y:auto;padding-right:2px;');
            for (const grp of [
                { key: 'ui', title: 'Editor & UI (Live)' },
                { key: 'fork', title: 'Conversation Forking' },
                { key: 'agent', title: 'Agent & Telemetry (Restart Required)' },
            ]) {
                const items = LIST.filter((it) => it.group === grp.key);
                if (!items.length) continue;
                body.appendChild(el('div', 'font-size:10px;font-weight:700;opacity:0.6;text-transform:uppercase;letter-spacing:0.05em;margin-top:4px;', grp.title));
                for (const it of items) {
                    const on = Boolean(state.flags[it.id]);
                    const knob = el('span', `width:14px;height:14px;background:#fff;border-radius:50%;position:absolute;top:2px;left:${on ? '19px' : '3px'};transition:left 0.18s;`);
                    const sw = el('button', `width:36px;height:18px;border-radius:9px;border:none;cursor:pointer;position:relative;flex-shrink:0;background:${on ? '#3b82f6' : '#64748b'};`, [knob], { type: 'button' });
                    sw.addEventListener('click', () => {
                        state.flags[it.id] = !state.flags[it.id];
                        saveConfig(false);
                        syncUi();
                    });
                    switchRefs.set(it.id, sw);

                    body.appendChild(el('div', 'display:flex;align-items:center;justify-content:space-between;gap:10px;', [
                        el('div', 'display:flex;flex-direction:column;min-width:0;', [
                            el('span', 'font-size:12px;font-weight:500;', it.label + (it.requiresRestart ? ' (Restart)' : '')),
                            el('span', 'font-size:10.5px;opacity:0.68;', it.description),
                        ]),
                        sw,
                    ]));

                    if (it.hasWidthOption) {
                        const segs = el('div', 'display:flex;gap:4px;');
                        for (const opt of [{ id: 'default', label: 'Default' }, { id: 'wide', label: 'Wide' }, { id: 'full', label: 'Full' }]) {
                            const b = el('button', 'padding:3px 7px;border-radius:5px;border:1px solid rgba(128,128,128,0.35);background:transparent;color:inherit;font-size:11px;cursor:pointer;', opt.label, { type: 'button' });
                            b.addEventListener('click', () => {
                                state.config.artifactWidth = opt.id;
                                saveConfig(false);
                                syncUi();
                            });
                            widthBtns.set(opt.id, b);
                            segs.appendChild(b);
                        }
                        widthRow = el('div', 'display:flex;align-items:center;justify-content:space-between;padding:2px 0 4px;', [
                            el('span', 'font-size:11px;opacity:0.75;', 'Artifact Pane Width'),
                            segs,
                        ]);
                        body.appendChild(widthRow);
                    }
                }
            }

            const sbSegs = el('div', 'display:flex;gap:4px;');
            for (const opt of [{ v: 0, l: 'Default' }, { v: 10, l: '10' }, { v: 20, l: '20' }, { v: -1, l: 'All' }]) {
                const b = el('button', 'padding:3px 7px;border-radius:5px;border:1px solid rgba(128,128,128,0.35);background:transparent;color:inherit;font-size:11px;cursor:pointer;', opt.l, { type: 'button' });
                b.addEventListener('click', () => { state.config.sidebarChatLimit = opt.v; saveConfig(false); syncUi(); });
                sbLimitBtns.set(opt.v, b);
                sbSegs.appendChild(b);
            }
            body.appendChild(el('div', 'font-size:10px;font-weight:700;opacity:0.6;text-transform:uppercase;letter-spacing:0.05em;margin-top:4px;', 'Sidebar & Context Caps'));
            body.appendChild(el('div', 'display:flex;align-items:center;justify-content:space-between;padding:2px 0;', [
                el('span', 'font-size:11px;opacity:0.78;', 'Chats / Project'),
                sbSegs,
            ]));

            const ctSegs = el('div', 'display:flex;gap:4px;');
            for (const opt of [{ v: 0, l: 'Default' }, { v: 256000, l: '256K' }, { v: 500000, l: '500K' }, { v: 1000000, l: '1M' }]) {
                const b = el('button', 'padding:3px 7px;border-radius:5px;border:1px solid rgba(128,128,128,0.35);background:transparent;color:inherit;font-size:11px;cursor:pointer;', opt.l, { type: 'button' });
                b.addEventListener('click', () => { state.config.contextTarget = opt.v; saveConfig(false); syncUi(); });
                ctxTargetBtns.set(opt.v, b);
                ctSegs.appendChild(b);
            }
            body.appendChild(el('div', 'display:flex;align-items:center;justify-content:space-between;padding:2px 0 4px;', [
                el('span', 'font-size:11px;opacity:0.78;', 'Context Target'),
                ctSegs,
            ]));

            const restartBtn = el('button', 'padding:4px 10px;border:none;border-radius:6px;background:#f59e0b;color:#18181b;font-size:11px;font-weight:700;cursor:pointer;', 'Restart IDE', { type: 'button' });
            restartBtn.addEventListener('click', triggerRestart);
            restartBanner = el('div', 'display:none;align-items:center;justify-content:space-between;gap:8px;padding:7px 9px;border-radius:7px;background:rgba(245,158,11,0.14);border:1px solid rgba(245,158,11,0.32);margin-top:8px;', [
                el('span', 'font-size:11px;color:#fbbf24;', 'Boot/server flag changed'),
                restartBtn,
            ]);

            const enableBtn = el('button', 'padding:4px 8px;border:1px solid rgba(128,128,128,0.35);border-radius:6px;background:transparent;color:inherit;font-size:11px;cursor:pointer;', 'Enable All Safe', { type: 'button' });
            enableBtn.addEventListener('click', () => { for (const it of LIST) state.flags[it.id] = true; saveConfig(true); syncUi(); });
            const relaunchBtn = el('button', 'padding:4px 8px;border:1px solid rgba(128,128,128,0.35);border-radius:6px;background:transparent;color:inherit;font-size:11px;cursor:pointer;', 'Restart IDE', { type: 'button' });
            relaunchBtn.addEventListener('click', triggerRestart);

            const closeX = el('span', 'cursor:pointer;font-size:16px;opacity:0.7;padding:0 4px;', '✕');
            closeX.addEventListener('click', closePanel);

            panel = el('div', 'display:none;position:fixed;bottom:32px;right:16px;z-index:999999;background:var(--vscode-editorWidget-background,#1e1e1e);color:var(--vscode-editorWidget-foreground,#d4d4d4);border:1px solid var(--vscode-editorWidget-border,#454545);border-radius:10px;padding:14px;width:356px;box-shadow:0 10px 30px rgba(0,0,0,0.45);font-size:12.5px;direction:ltr;font-family:var(--vscode-font-family,system-ui,sans-serif);', [
                el('div', 'display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(128,128,128,0.2);padding-bottom:8px;margin-bottom:8px;', [
                    el('span', 'font-weight:700;font-size:12px;', 'Experiment Flags'),
                    closeX,
                ]),
                body,
                restartBanner,
                el('div', 'display:flex;justify-content:space-between;align-items:center;border-top:1px solid rgba(128,128,128,0.2);padding-top:8px;margin-top:8px;', [
                    enableBtn,
                    relaunchBtn,
                ]),
            ], { id: 'antigravity-flags-settings-panel' });

            document.body.appendChild(panel);
            return panel;
        }

        function tryInsertStatusBar() {
            if (document.getElementById('antigravity-flags-statusbar-btn')) return;
            const bar =
                document.querySelector('.part.statusbar .right-items') ||
                document.querySelector('.part.statusbar .items-container.right-items') ||
                document.querySelector('[id="workbench.parts.statusbar"] .right-items') ||
                document.querySelector('.part.statusbar');
            if (!bar) return;

            const item = el('a', 'cursor:pointer !important;padding:0 8px !important;display:inline-flex !important;align-items:center !important;font-size:11px !important;height:100% !important;line-height:22px !important;text-decoration:none !important;white-space:nowrap !important;color:#38bdf8 !important;', '⚙ Flags', {
                id: 'antigravity-flags-statusbar-btn',
                className: 'statusbar-item right',
                href: '#',
                title: 'Experiment Flags & Context/Cost Settings',
            });
            item.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const panel = ensurePanel();
                if (isOpen) closePanel();
                else {
                    syncUi();
                    panel.style.display = 'block';
                    isOpen = true;
                }
            });
            const rtlBtn = document.getElementById('antigravity-rtl-statusbar-btn');
            if (rtlBtn && rtlBtn.parentElement === bar) bar.insertBefore(item, rtlBtn);
            else bar.prepend(item);

            if (!document.getElementById('antigravity-usage-statusbar-btn')) {
                const uBtn = el('a', 'cursor:pointer !important;padding:0 8px !important;display:inline-flex !important;align-items:center !important;font-size:11px !important;height:100% !important;line-height:22px !important;text-decoration:none !important;white-space:nowrap !important;color:#34d399 !important;', 'Usage', {
                    id: 'antigravity-usage-statusbar-btn',
                    className: 'statusbar-item right',
                    href: '#',
                    title: 'Multi-Account Usage & Spend Dashboard',
                });
                uBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (feat) feat.openUsageDashboardModal('all');
                });
                bar.insertBefore(uBtn, item);
            }
            syncUi();
        }

        document.addEventListener('click', (e) => {
            if (!isOpen) return;
            const panel = document.getElementById('antigravity-flags-settings-panel');
            const btn = document.getElementById('antigravity-flags-statusbar-btn');
            if (panel && panel.contains(e.target)) return;
            if (btn && (btn === e.target || btn.contains(e.target))) return;
            closePanel();
        });
        document.addEventListener('keydown', (e) => { if (isOpen && e.key === 'Escape') closePanel(); });

        tryInsertStatusBar();
        setInterval(tryInsertStatusBar, 1500);
    }

    if (root) root.__antigravityMountIdeExperiments = mountIdeExperiments;
})(typeof window !== 'undefined' ? window : globalThis);
