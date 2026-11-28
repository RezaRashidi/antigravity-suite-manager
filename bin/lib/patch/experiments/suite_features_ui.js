/**
 * Shared Pure-DOM Client Features for Antigravity App & IDE:
 * 1. Compact Layout CSS
 * 2. File Context Menu (#L:C attach, copy, open, reveal)
 * 3. Full-Text Conversation Search inside native picker
 * 4. Speed, TTFT, Cache Drop Anomaly & Per-Turn Telemetry
 * 5. Multi-Account Usage Dashboard Popover Modal (with 53-week heatmap)
 * Zero innerHTML (Trusted Types compliant).
 */
(function (root) {
    'use strict';

    const ROUTER_BASE = 'http://127.0.0.1:41999';

    function el(tag, css, children, attrs) {
        const node = document.createElement(tag);
        if (css) node.style.cssText = css;
        if (attrs) {
            for (const [k, v] of Object.entries(attrs)) {
                if (k === 'className') node.className = v;
                else if (k === 'text') node.textContent = v;
                else if (v !== undefined && v !== null) node.setAttribute(k, String(v));
            }
        }
        if (Array.isArray(children)) {
            for (const c of children) if (c) node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
        } else if (typeof children === 'string') {
            node.textContent = children;
        }
        return node;
    }

    function fmtTok(v) {
        const n = Number(v || 0);
        if (!Number.isFinite(n) || n <= 0) return '0';
        if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 1 : 2).replace(/\.?0+$/, '') + 'M';
        if (n >= 1e3) return (n / 1e3).toFixed(n >= 1e5 ? 0 : 1).replace(/\.0$/, '') + 'k';
        return String(Math.round(n));
    }

    function fmtUsd(v) {
        const n = Number(v || 0);
        if (!Number.isFinite(n) || n <= 0) return '$0.00';
        return n >= 1 ? '$' + n.toFixed(2) : '$' + n.toFixed(n < 0.01 ? 4 : 3);
    }

    function detectActiveCascadeId(refEl) {
        try {
            if (typeof window.__antigravityDetectCascadeId === 'function') {
                const cid = window.__antigravityDetectCascadeId(refEl);
                if (cid && cid !== 'default') return cid;
            }
        } catch (_) {}
        const m = (window.location.pathname + window.location.hash + window.location.href).match(/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/i);
        return m ? m[0] : '';
    }

    function navigateToConversation(cascadeId) {
        if (!cascadeId) return;
        const row = document.querySelector(`[data-cascade-id="${cascadeId}"]`);
        if (row && typeof row.click === 'function') {
            row.click();
            return;
        }
        // Fallback: check React provider router on #root / input box
        try {
            const anchor = document.querySelector('[aria-label="Message input"], #root > div') || document.body?.firstElementChild;
            const fk = anchor && Object.keys(anchor).find((k) => k.startsWith('__reactFiber$'));
            for (let n = fk ? anchor[fk] : null; n; n = n.return) {
                const val = n.tag === 10 ? n.memoizedProps?.value : null;
                if (val && typeof val.navigate === 'function' && typeof val.buildRouteTree === 'function') {
                    void val.navigate({ to: '/conversation/$cascadeId', params: { cascadeId } }).catch(() => {});
                    return;
                }
            }
        } catch (_) {}
    }

    // 1. Compact Layout
    function applyCompactLayout(enabled) {
        let st = document.getElementById('suite-compact-layout-style');
        if (!st) {
            st = document.createElement('style');
            st.id = 'suite-compact-layout-style';
            (document.head || document.documentElement).appendChild(st);
        }
        if (!enabled) {
            delete document.documentElement.dataset.suiteCompact;
            st.textContent = '';
            return;
        }
        document.documentElement.dataset.suiteCompact = '1';
        st.textContent = `
            html[data-suite-compact="1"] [data-testid="agent-response"],
            html[data-suite-compact="1"] [data-testid="user-input-step"] {
                line-height: 1.42 !important;
            }
            html[data-suite-compact="1"] [data-testid="agent-response"] :is(p, li, pre, code) {
                line-height: 1.42 !important;
            }
            html[data-suite-compact="1"] [data-testid="agent-response"] p + p {
                margin-top: 0.45em !important;
            }
            html[data-suite-compact="1"] [data-testid="agent-response"] :is([data-testid="worked-for-collapsible"], [data-testid="tool-group-collapsible"], div.group.min-h-8) {
                min-height: 24px !important;
                padding-top: 2px !important;
                padding-bottom: 2px !important;
            }
            html[data-suite-compact="1"] [data-testid="conversation-row-sidebar"] {
                padding-top: 3px !important;
                padding-bottom: 3px !important;
                min-height: 26px !important;
            }
        `;
    }

    // 2. File Context Menu (#L:C)
    function parseFileReference(rawUri, sourceEl) {
        let s = String(rawUri || '').trim();
        if (!s) return null;
        s = s.replace(/^file:\/\//i, '');
        let lineAnchor = '';
        const lm = s.match(/(#L\d+(?:-L?\d+)?)$/i);
        if (lm) {
            lineAnchor = lm[1];
            s = s.slice(0, -lm[1].length);
        } else {
            const cm = s.match(/:(\d+)(?::(\d+))?$/);
            if (cm) {
                lineAnchor = cm[2] ? `#L${cm[1]}:${cm[2]}` : `#L${cm[1]}`;
                s = s.slice(0, -cm[0].length);
            }
        }
        try { s = decodeURIComponent(s); } catch (_) {}
        if (!s || !s.startsWith('/')) {
            const textHint = String(sourceEl?.textContent || '').trim();
            const hm = textHint.match(/(#L\d+(?:-L?\d+)?)/i);
            if (hm && !lineAnchor) lineAnchor = hm[1];
        }
        return { cleanPath: s, lineAnchor, fullRef: s + lineAnchor };
    }

    function insertTextIntoComposer(text) {
        const box = document.querySelector('[aria-label="Message input"], [contenteditable="true"][role="textbox"], textarea[placeholder*="Ask"]');
        if (!box) {
            try { navigator.clipboard?.writeText(text); } catch (_) {}
            return false;
        }
        box.focus();
        try {
            if (box.isContentEditable) {
                document.execCommand('insertText', false, text + ' ');
            } else {
                const proto = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value');
                const next = (box.value ? box.value + ' ' : '') + text + ' ';
                if (proto && proto.set) proto.set.call(box, next);
                else box.value = next;
                box.dispatchEvent(new Event('input', { bubbles: true }));
            }
            return true;
        } catch (_) {
            return false;
        }
    }

    function mountFileContextMenu(isEnabledFn) {
        if (window.__SUITE_FILE_MENU_MOUNTED__) return;
        window.__SUITE_FILE_MENU_MOUNTED__ = true;
        let menuNode = null;
        function closeMenu() {
            if (menuNode) { menuNode.remove(); menuNode = null; }
        }
        document.addEventListener('click', (e) => {
            if (menuNode && !menuNode.contains(e.target)) closeMenu();
        }, true);
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeMenu(); }, true);

        window.addEventListener('contextmenu', (e) => {
            if (!isEnabledFn()) return;
            const target = e.target?.closest?.('a[href^="file://"], [data-uri^="file://"], [data-uri^="/"], [data-path^="/"]');
            if (!target) return;
            const rawUri = target.getAttribute('data-uri') || target.getAttribute('href') || target.getAttribute('data-path') || '';
            const info = parseFileReference(rawUri, target);
            if (!info || !info.cleanPath) return;

            e.preventDefault();
            e.stopPropagation();
            closeMenu();

            menuNode = el('div', 'position:fixed;z-index:9999999;min-width:195px;padding:5px;border-radius:9px;background:var(--popover,#18181b);color:var(--popover-foreground,#f4f4f5);border:1px solid var(--border,rgba(255,255,255,0.16));box-shadow:0 12px 28px rgba(0,0,0,0.45);font-size:12px;direction:ltr;display:flex;flex-direction:column;gap:2px;', null, { 'data-suite-file-menu': '1' });

            const items = [
                { label: `Attach to Chat (@${info.cleanPath.split('/').pop()}${info.lineAnchor})`, fn: () => insertTextIntoComposer('@' + info.fullRef) },
                { label: 'Copy Path', fn: () => navigator.clipboard?.writeText(info.cleanPath) },
                info.lineAnchor ? { label: `Copy Path (${info.lineAnchor})`, fn: () => navigator.clipboard?.writeText(info.fullRef) } : null,
                { label: 'Reveal in Folder', fn: () => console.log('SUITE_FILE_ACTION|' + JSON.stringify({ action: 'reveal', filePath: info.cleanPath })) },
                { label: 'Open Externally', fn: () => console.log('SUITE_FILE_ACTION|' + JSON.stringify({ action: 'open', filePath: info.cleanPath })) },
            ].filter(Boolean);

            for (const it of items) {
                const btn = el('button', 'text-align:left;padding:5px 8px;border:none;border-radius:6px;background:transparent;color:inherit;cursor:pointer;font-size:11.5px;white-space:nowrap;', it.label, { type: 'button' });
                btn.addEventListener('mouseenter', () => { btn.style.background = 'var(--muted,rgba(255,255,255,0.09))'; });
                btn.addEventListener('mouseleave', () => { btn.style.background = 'transparent'; });
                btn.addEventListener('click', () => { closeMenu(); try { it.fn(); } catch (_) {} });
                menuNode.appendChild(btn);
            }

            document.body.appendChild(menuNode);
            menuNode.style.left = Math.min(window.innerWidth - menuNode.offsetWidth - 8, e.clientX) + 'px';
            menuNode.style.top = Math.min(window.innerHeight - menuNode.offsetHeight - 8, e.clientY) + 'px';
        }, true);
    }

    // 3. Full-Text Conversation Search inside native picker
    function mountFullTextSearch(isEnabledFn) {
        if (window.__SUITE_FT_SEARCH_MOUNTED__) return;
        window.__SUITE_FT_SEARCH_MOUNTED__ = true;
        let lastQ = '';
        let timer = null;

        async function runQuery(q, listContainer) {
            if (!q || q.length < 2) {
                const old = listContainer.querySelector('#suite-ft-search-section');
                if (old) old.remove();
                return;
            }
            try {
                const res = await fetch(`${ROUTER_BASE}/api/usage/search?q=${encodeURIComponent(q)}&limit=15`);
                if (!res.ok) return;
                const data = await res.json();
                let sec = listContainer.querySelector('#suite-ft-search-section');
                if (!sec) {
                    sec = el('div', 'margin-top:8px;padding-top:8px;border-top:1px solid var(--border,rgba(255,255,255,0.12));display:flex;flex-direction:column;gap:4px;', null, { id: 'suite-ft-search-section' });
                    listContainer.appendChild(sec);
                }
                sec.replaceChildren();
                const matches = Array.isArray(data.results) ? data.results : [];
                sec.appendChild(el('div', 'font-size:10.5px;font-weight:600;text-transform:uppercase;opacity:0.65;padding:2px 8px;', `Full-Text Matches (${matches.length})`));
                if (!matches.length) {
                    sec.appendChild(el('div', 'font-size:11.5px;opacity:0.55;padding:4px 8px;', 'No message body matches found.'));
                    return;
                }
                for (const m of matches) {
                    const row = el('button', 'text-align:left;width:100%;padding:6px 8px;border:none;border-radius:6px;background:transparent;color:inherit;cursor:pointer;display:flex;flex-direction:column;gap:2px;', [
                        el('div', 'display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:11.5px;font-weight:600;', [
                            el('span', 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;', m.title || m.cascadeId.slice(0, 8)),
                            el('span', 'font-size:10px;opacity:0.65;flex-shrink:0;', [m.role, m.accountEmail ? m.accountEmail.split('@')[0] : ''].filter(Boolean).join(' · ')),
                        ]),
                        el('div', 'font-size:11px;opacity:0.75;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;', m.snippet || ''),
                    ], { type: 'button' });
                    row.addEventListener('mouseenter', () => { row.style.background = 'var(--muted,rgba(255,255,255,0.08))'; });
                    row.addEventListener('mouseleave', () => { row.style.background = 'transparent'; });
                    row.addEventListener('click', (ev) => {
                        ev.preventDefault();
                        ev.stopPropagation();
                        const esc = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
                        document.dispatchEvent(esc);
                        navigateToConversation(m.cascadeId);
                    });
                    sec.appendChild(row);
                }
            } catch (_) {}
        }

        function attachPicker() {
            if (!isEnabledFn()) return;
            const input = document.querySelector('input[placeholder="Search for conversations..."], [data-testid="fast-pick-viewport"] input');
            if (!input || input.dataset.suiteFtBound) return;
            input.dataset.suiteFtBound = '1';
            const card = input.closest('[data-testid="fast-pick-viewport"]')?.querySelector('[role="listbox"], .overflow-y-auto') || input.parentElement?.parentElement;
            if (!card) return;
            input.addEventListener('input', () => {
                const q = input.value.trim();
                if (q === lastQ) return;
                lastQ = q;
                if (timer) clearTimeout(timer);
                timer = setTimeout(() => void runQuery(q, card), 220);
            });
        }
        setInterval(attachPicker, 500);
    }

    // 4. Multi-Account Usage Dashboard Modal
    function renderHeatmapSvg(heatmapData) {
        const ns = 'http://www.w3.org/2000/svg';
        const cols = 53, rows = 7, cell = 9, gap = 2;
        const svg = document.createElementNS(ns, 'svg');
        svg.setAttribute('viewBox', `0 0 ${cols * (cell + gap)} ${rows * (cell + gap)}`);
        svg.setAttribute('width', '100%');
        svg.style.cssText = 'display:block;max-width:580px;height:auto;';

        const entries = Object.values(heatmapData || {});
        const maxTok = Math.max(1, ...entries.map((d) => Number(d.tokens || 0)));
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const totalDays = cols * 7;
        const start = new Date(today.getTime() - (totalDays - 1) * 86400000);
        const startShift = start.getDay();

        for (let w = 0; w < cols; w++) {
            for (let d = 0; d < 7; d++) {
                const offset = w * 7 + d - startShift;
                const dt = new Date(start.getTime() + offset * 86400000);
                if (dt > today) continue;
                const key = dt.toISOString().slice(0, 10);
                const item = heatmapData?.[key];
                const tok = Number(item?.tokens || 0);
                const ratio = tok > 0 ? Math.min(1, Math.sqrt(tok / maxTok)) : 0;
                const color = tok === 0
                    ? 'rgba(128,128,128,0.16)'
                    : ratio > 0.72 ? '#16a34a' : ratio > 0.45 ? '#22c55e' : ratio > 0.2 ? '#4ade80' : '#86efac';
                const rect = document.createElementNS(ns, 'rect');
                rect.setAttribute('x', String(w * (cell + gap)));
                rect.setAttribute('y', String(d * (cell + gap)));
                rect.setAttribute('width', String(cell));
                rect.setAttribute('height', String(cell));
                rect.setAttribute('rx', '2');
                rect.setAttribute('fill', color);
                const tip = document.createElementNS(ns, 'title');
                tip.textContent = `${key}: ${fmtTok(tok)} tok (${fmtUsd(item?.costUsd || 0)})`;
                rect.appendChild(tip);
                svg.appendChild(rect);
            }
        }
        return svg;
    }

    function openUsageDashboardModal(initialAccount = 'all') {
        const existing = document.getElementById('suite-usage-dashboard-overlay');
        if (existing) { existing.remove(); return; }

        let curRange = '7d';
        let curAccount = initialAccount || 'all';
        const overlay = el('div', 'position:fixed;inset:0;z-index:9999990;background:rgba(0,0,0,0.55);display:flex;align-items:center;justify-content:center;padding:16px;direction:ltr;', null, { id: 'suite-usage-dashboard-overlay' });
        const modal = el('div', 'width:min(820px,96vw);max-height:88vh;overflow-y:auto;border-radius:12px;background:var(--popover,var(--card,#18181b));color:var(--foreground,#f4f4f5);border:1px solid var(--border,rgba(255,255,255,0.16));box-shadow:0 20px 50px rgba(0,0,0,0.55);padding:16px;font-family:ui-sans-serif,system-ui,sans-serif;font-size:12px;box-sizing:border-box;');
        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        const close = () => overlay.remove();
        overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
        document.addEventListener('keydown', function onEsc(e) {
            if (e.key === 'Escape') { close(); document.removeEventListener('keydown', onEsc, true); }
        }, true);

        async function loadAndRender() {
            modal.replaceChildren(el('div', 'padding:24px;text-align:center;opacity:0.7;', 'Loading Multi-Account Usage Analytics...'));
            try {
                const res = await fetch(`${ROUTER_BASE}/api/usage/dashboard?range=${encodeURIComponent(curRange)}&account=${encodeURIComponent(curAccount)}`);
                if (!res.ok) throw new Error('Router unavailable');
                const data = await res.json();
                renderData(data);
            } catch (err) {
                modal.replaceChildren(el('div', 'padding:20px;color:#f87171;', 'Failed to fetch dashboard from router (127.0.0.1:41999). Make sure multi-account router is running.'));
            }
        }

        function chip(label, active, onClick) {
            const b = el('button', `padding:4px 9px;border-radius:999px;border:1px solid ${active ? '#3b82f6' : 'var(--border,rgba(255,255,255,0.18))'};background:${active ? 'rgba(59,130,246,0.2)' : 'transparent'};color:inherit;cursor:pointer;font-size:11px;font-weight:${active ? 600 : 400};`, label, { type: 'button' });
            b.addEventListener('click', onClick);
            return b;
        }

        function renderData(d) {
            modal.replaceChildren();
            const closeBtn = el('button', 'border:none;background:transparent;color:inherit;cursor:pointer;font-size:16px;opacity:0.75;padding:2px 6px;', '×', { type: 'button' });
            closeBtn.addEventListener('click', close);
            modal.appendChild(el('div', 'display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;', [
                el('div', 'font-size:14px;font-weight:700;', 'Antigravity Multi-Account Usage & Spend'),
                closeBtn,
            ]));

            // Filters row
            const rangeRow = el('div', 'display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;');
            for (const [rid, rlabel] of [['today', 'Today'], ['7d', 'Weekly / 7d'], ['30d', '30 Days'], ['all', 'All Time']]) {
                rangeRow.appendChild(chip(rlabel, curRange === rid, () => { curRange = rid; void loadAndRender(); }));
            }
            modal.appendChild(rangeRow);

            const accRow = el('div', 'display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;');
            accRow.appendChild(chip('All Accounts', curAccount === 'all', () => { curAccount = 'all'; void loadAndRender(); }));
            for (const em of d.availableAccounts || []) {
                accRow.appendChild(chip(em, curAccount === em, () => { curAccount = em; void loadAndRender(); }));
            }
            modal.appendChild(accRow);

            // KPI cards
            const kpis = el('div', 'display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:14px;');
            const tot = d.totals || {};
            for (const [lbl, val, sub] of [
                ['Est. Spend', fmtUsd(tot.costUsd), `Saved ${fmtUsd(tot.cacheSavingsUsd)}`],
                ['Cache Hit Rate', `${tot.cacheHitPct || 0}%`, `${tot.anomalies || 0} cache drops`],
                ['Total Tokens', fmtTok((tot.inputTokens || 0) + (tot.cacheReadTokens || 0) + (tot.outputTokens || 0)), `${tot.turns || 0} turns`],
                ['Sessions', String(tot.sessions || 0), `${(d.accounts || []).length} accounts`],
            ]) {
                kpis.appendChild(el('div', 'padding:10px;border-radius:8px;border:1px solid var(--border,rgba(255,255,255,0.12));background:rgba(128,128,128,0.06);', [
                    el('div', 'font-size:10.5px;opacity:0.65;', lbl),
                    el('div', 'font-size:16px;font-weight:700;margin:2px 0;font-variant-numeric:tabular-nums;', val),
                    el('div', 'font-size:10px;opacity:0.65;', sub),
                ]));
            }
            modal.appendChild(kpis);

            // 53-week Heatmap
            modal.appendChild(el('div', 'font-size:11px;font-weight:600;margin-bottom:6px;opacity:0.8;', '53-Week Token & Spend Heatmap'));
            modal.appendChild(el('div', 'margin-bottom:14px;padding:8px;border-radius:8px;border:1px solid var(--border,rgba(255,255,255,0.1));', [renderHeatmapSvg(d.heatmap)]));

            // Per-account breakdown
            if ((d.accounts || []).length > 0) {
                modal.appendChild(el('div', 'font-size:11px;font-weight:600;margin-bottom:6px;opacity:0.8;', 'By Account'));
                const accBox = el('div', 'border:1px solid var(--border,rgba(255,255,255,0.1));border-radius:8px;overflow:hidden;margin-bottom:14px;');
                for (const a of d.accounts) {
                    const row = el('div', 'display:flex;justify-content:space-between;align-items:center;padding:6px 10px;border-bottom:1px solid var(--border,rgba(255,255,255,0.06));font-size:11.5px;cursor:pointer;', [
                        el('span', 'font-weight:500;', a.email),
                        el('span', 'opacity:0.75;font-variant-numeric:tabular-nums;', `${a.sessions} chats · ${fmtTok(a.totalTokens)} tok · ${a.cacheHitPct}% cache · ${fmtUsd(a.costUsd)}`),
                    ]);
                    row.addEventListener('click', () => { curAccount = a.email; void loadAndRender(); });
                    accBox.appendChild(row);
                }
                modal.appendChild(accBox);
            }

            // Models breakdown
            if ((d.models || []).length > 0) {
                modal.appendChild(el('div', 'font-size:11px;font-weight:600;margin-bottom:6px;opacity:0.8;', 'By Model'));
                const modBox = el('div', 'border:1px solid var(--border,rgba(255,255,255,0.1));border-radius:8px;overflow:hidden;margin-bottom:14px;');
                for (const m of d.models.slice(0, 12)) {
                    modBox.appendChild(el('div', 'display:flex;justify-content:space-between;padding:6px 10px;border-bottom:1px solid var(--border,rgba(255,255,255,0.06));font-size:11.5px;', [
                        el('span', 'font-weight:500;', m.model),
                        el('span', 'opacity:0.75;font-variant-numeric:tabular-nums;', `${m.turns} turns · ${fmtTok(m.totalTokens)} tok · ${m.cacheHitPct}% cache · ${fmtUsd(m.costUsd)}`),
                    ]));
                }
                modal.appendChild(modBox);
            }

            // Recent sessions
            if ((d.recentSessions || []).length > 0) {
                modal.appendChild(el('div', 'font-size:11px;font-weight:600;margin-bottom:6px;opacity:0.8;', 'Recent Sessions (click to open)'));
                const sesBox = el('div', 'border:1px solid var(--border,rgba(255,255,255,0.1));border-radius:8px;overflow:hidden;');
                for (const s of d.recentSessions.slice(0, 10)) {
                    const row = el('div', 'display:flex;justify-content:space-between;gap:8px;padding:6px 10px;border-bottom:1px solid var(--border,rgba(255,255,255,0.06));font-size:11.5px;cursor:pointer;', [
                        el('span', 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;', `${s.title}${s.anomalies ? ` [⚠ ${s.anomalies} cache drop]` : ''}`),
                        el('span', 'flex-shrink:0;opacity:0.75;font-variant-numeric:tabular-nums;', `${s.accountEmail === 'unbound' ? 'local' : s.accountEmail.split('@')[0]} · ${fmtTok(s.totalTokens)} · ${fmtUsd(s.costUsd)}`),
                    ]);
                    row.addEventListener('click', () => { close(); navigateToConversation(s.cascadeId); });
                    sesBox.appendChild(row);
                }
                modal.appendChild(sesBox);
            }
        }
        void loadAndRender();
    }

    // 5. Speed & Per-Turn Telemetry Pill
    function mountSpeedTelemetry(isEnabledFn) {
        if (window.__SUITE_SPEED_MOUNTED__) return;
        window.__SUITE_SPEED_MOUNTED__ = true;
        let lastData = null;
        let popOpen = false;
        let popNode = null;

        const ns = 'http://www.w3.org/2000/svg';
        const icon = document.createElementNS(ns, 'svg');
        icon.setAttribute('width', '14');
        icon.setAttribute('height', '14');
        icon.setAttribute('viewBox', '0 0 24 24');
        icon.setAttribute('fill', 'none');
        icon.setAttribute('stroke', 'currentColor');
        icon.setAttribute('stroke-width', '2');
        icon.setAttribute('stroke-linecap', 'round');
        icon.setAttribute('stroke-linejoin', 'round');
        icon.style.cssText = 'flex-shrink:0;';
        const needle = document.createElementNS(ns, 'path');
        needle.setAttribute('d', 'm12 14 4-4');
        const arc = document.createElementNS(ns, 'path');
        arc.setAttribute('d', 'M3.34 19a10 10 0 1 1 17.32 0');
        icon.appendChild(arc);
        icon.appendChild(needle);

        const txt = el('span', 'font-variant-numeric:tabular-nums;font-size:11px;font-weight:500;display:none;', '');
        const pill = el('button', 'display:inline-flex;align-items:center;justify-content:center;gap:4px;height:28px;min-width:28px;padding:0 6px;border-radius:999px;border:none;background:transparent;color:inherit;cursor:pointer;font-size:11px;opacity:0.82;', [icon, txt], {
            id: 'suite-speed-telemetry-pill',
            type: 'button',
            className: 'flex cursor-pointer items-center h-7 gap-1 rounded-full px-1.5 text-xs text-secondary-foreground select-none outline-none hover:bg-muted transition-colors',
            title: 'Generation Speed, TTFT & Per-Turn Telemetry',
        });

        function closePop() {
            popOpen = false;
            if (popNode) { popNode.remove(); popNode = null; }
        }

        function renderPop() {
            if (!popNode) return;
            popNode.replaceChildren();
            const d = lastData || {};
            popNode.appendChild(el('div', 'display:flex;justify-content:space-between;font-weight:600;margin-bottom:6px;', [
                el('span', '', 'Speed & Telemetry'),
                el('span', 'opacity:0.75;', d.tokPerSec ? `${d.tokPerSec} tok/s` : 'Idle'),
            ]));
            const rows = [
                ['TTFT (1st token)', d.ttftMs ? (d.ttftMs >= 1000 ? `${(d.ttftMs / 1000).toFixed(2)}s` : `${d.ttftMs}ms`) : '-'],
                ['Last Turn Dur.', d.lastTurnDurationMs ? `${(d.lastTurnDurationMs / 1000).toFixed(1)}s` : '-'],
                ['Avg Speed', d.avgTokPerSec ? `${d.avgTokPerSec} tok/s` : '-'],
                ['Cache Hit', `${d.cacheHitPct || 0}% (saved ${fmtUsd(d.cacheSavingsUsd)})`],
                ['Session Spend', `${fmtUsd(d.sessionCostUsd)} (${d.turns || 0} turns)`],
                ['Account', d.accountEmail || 'Default'],
            ];
            for (const [k, v] of rows) {
                popNode.appendChild(el('div', 'display:flex;justify-content:space-between;gap:10px;padding:2px 0;font-size:11.5px;', [
                    el('span', 'opacity:0.7;', k),
                    el('span', 'font-variant-numeric:tabular-nums;font-weight:500;', v),
                ]));
            }
            if (Array.isArray(d.cacheAnomalies) && d.cacheAnomalies.length > 0) {
                const lastA = d.cacheAnomalies[d.cacheAnomalies.length - 1];
                popNode.appendChild(el('div', 'margin-top:6px;padding:5px 7px;border-radius:6px;background:rgba(245,158,11,0.14);color:#fbbf24;font-size:10.5px;', `Cache Drop Alert: ${lastA.prevHitPct}% -> ${lastA.hitPct}% (-${lastA.dropPct}%)`));
            }
            if (Array.isArray(d.subagents) && d.subagents.length > 0) {
                popNode.appendChild(el('div', 'margin-top:7px;font-size:10.5px;font-weight:600;opacity:0.7;', `Subagents (${d.subagents.length})`));
                for (const s of d.subagents.slice(0, 4)) {
                    popNode.appendChild(el('div', 'display:flex;justify-content:space-between;font-size:10.5px;opacity:0.85;padding:1px 0;', [
                        el('span', 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:140px;', `${s.role} (${s.state})`),
                        el('span', 'font-variant-numeric:tabular-nums;', `${fmtTok(s.tokens)} · ${fmtUsd(s.costUsd)}`),
                    ]));
                }
            }
            const dashBtn = el('button', 'margin-top:8px;width:100%;padding:5px;border-radius:6px;border:1px solid var(--border,rgba(255,255,255,0.18));background:rgba(59,130,246,0.14);color:inherit;cursor:pointer;font-size:11px;font-weight:500;', 'Open Multi-Account Usage Dashboard', { type: 'button' });
            dashBtn.addEventListener('click', () => { closePop(); openUsageDashboardModal(d.accountEmail || 'all'); });
            popNode.appendChild(dashBtn);
        }

        pill.addEventListener('click', (e) => {
            e.stopPropagation();
            if (popOpen) { closePop(); return; }
            popOpen = true;
            popNode = el('div', 'position:fixed;z-index:999999;width:280px;padding:10px 12px;border-radius:10px;background:var(--popover,var(--card,#18181b));color:var(--foreground,#f4f4f5);border:1px solid var(--border,rgba(255,255,255,0.16));box-shadow:0 12px 30px rgba(0,0,0,0.45);font-size:12px;direction:ltr;');
            document.body.appendChild(popNode);
            renderPop();
            const r = pill.getBoundingClientRect();
            popNode.style.left = Math.max(8, Math.min(window.innerWidth - 288, r.left)) + 'px';
            popNode.style.top = Math.max(8, r.top - popNode.offsetHeight - 8) + 'px';
        });
        document.addEventListener('click', (e) => { if (popOpen && popNode && !popNode.contains(e.target) && !pill.contains(e.target)) closePop(); });

        async function refresh() {
            const enabled = isEnabledFn();
            pill.style.display = enabled ? 'inline-flex' : 'none';
            if (!enabled) return;
            const cid = detectActiveCascadeId(pill);
            try {
                const res = await fetch(`${ROUTER_BASE}/api/usage/active?cascadeId=${encodeURIComponent(cid || '')}`);
                if (!res.ok) return;
                const d = await res.json();
                lastData = d;
                const parts = [];
                if (d.tokPerSec > 0) parts.push(`${d.tokPerSec} t/s`);
                if (d.ttftMs > 0) parts.push(d.ttftMs >= 1000 ? `${(d.ttftMs / 1000).toFixed(1)}s` : `${d.ttftMs}ms`);
                if (d.cacheHitPct > 0) parts.push(`${Math.round(d.cacheHitPct)}%`);
                if (parts.length > 0) {
                    txt.textContent = parts.join(' · ');
                    txt.style.display = 'inline';
                } else {
                    txt.textContent = '';
                    txt.style.display = 'none';
                }
                if (popOpen) renderPop();
            } catch (_) {}
        }

        function resolveTelemetryAnchor() {
            const activeView =
                document.querySelector('[data-testid="conversation-view"]:not([hidden])') ||
                document.querySelector('[data-testid="conversation-view"]');
            const scope = activeView || document;

            // 1. Canonical placement: right-side toolbar group inside .agy-composer-footer (consistent across empty & active chats)
            const footer = scope.querySelector('.agy-composer-footer') || document.querySelector('.agy-composer-footer');
            if (footer && footer.lastElementChild) {
                const rightRow = footer.lastElementChild;
                const nativeCtx = rightRow.querySelector('[data-suite-context-indicator="native"]');
                const idePill = rightRow.querySelector('#suite-ide-context-cost-pill');
                const anchorBtn = nativeCtx || idePill;
                if (anchorBtn) return { parent: rightRow, beforeNode: anchorBtn.nextSibling };
                // Place directly before the Send button (last element in rightRow)
                return { parent: rightRow, beforeNode: rightRow.lastElementChild };
            }

            // 2. Fallback (IDE webview or older UI)
            const idePill = scope.querySelector('#suite-ide-context-cost-pill') || document.getElementById('suite-ide-context-cost-pill');
            if (idePill && idePill.parentElement) return { parent: idePill.parentElement, beforeNode: idePill.nextSibling };
            const ctxNative = scope.querySelector('[data-suite-context-indicator="native"]') || document.querySelector('[data-suite-context-indicator="native"]');
            if (ctxNative && ctxNative.parentElement) return { parent: ctxNative.parentElement, beforeNode: ctxNative.nextSibling };
            return null;
        }

        function attach() {
            if (!isEnabledFn()) { pill.style.display = 'none'; return; }
            pill.style.display = 'inline-flex';
            const slot = resolveTelemetryAnchor();
            if (!slot || !slot.parent) return;
            const wrongOrder = Boolean(slot.beforeNode && slot.beforeNode !== pill && pill.nextSibling !== slot.beforeNode);
            if (pill.parentElement !== slot.parent || wrongOrder) {
                slot.parent.insertBefore(pill, (slot.beforeNode && slot.beforeNode !== pill) ? slot.beforeNode : null);
                void refresh();
            }
        }
        function updateTurnMeta(turnsList) {
            if (!isEnabledFn() || !Array.isArray(turnsList) || !turnsList.length) return;
            const nodes = document.querySelectorAll('[data-testid="agent-response"]');
            if (!nodes.length) return;
            const offset = Math.max(0, turnsList.length - nodes.length);
            for (let i = 0; i < nodes.length; i++) {
                const n = nodes[i];
                const t = turnsList[offset + i];
                if (!t) continue;
                const sig = `${t.model}|${t.outputTokens}|${t.costUsd}|${t.cacheHitPct}|${t.tokPerSec}|${t.anomaly ? 1 : 0}`;
                if (n.dataset.suiteTurnMeta === sig) continue;
                n.dataset.suiteTurnMeta = sig;
                let badge = n.querySelector(':scope > .suite-turn-telemetry-row');
                if (!badge) {
                    badge = el('div', 'font-size:10.5px;opacity:0.62;margin-top:4px;font-variant-numeric:tabular-nums;direction:ltr;display:flex;gap:8px;flex-wrap:wrap;', null, { className: 'suite-turn-telemetry-row' });
                    n.appendChild(badge);
                }
                const parts = [
                    t.model || 'model',
                    t.tokPerSec > 0 ? `${t.tokPerSec} t/s` : null,
                    `${fmtTok(t.inputTokens + t.cacheReadTokens)} in / ${fmtTok(t.outputTokens)} out`,
                    `${t.cacheHitPct}% cache`,
                    fmtUsd(t.costUsd),
                    t.anomaly ? 'cache drop' : null,
                ].filter(Boolean);
                badge.textContent = parts.join(' · ');
            }
        }
        const origRefresh = refresh;
        const wrappedRefresh = async () => {
            await origRefresh();
            if (lastData && Array.isArray(lastData.turnsList)) updateTurnMeta(lastData.turnsList);
        };
        attach();
        setInterval(attach, 1500);
        setInterval(wrappedRefresh, 3500);
    }

    if (root) {
        root.__antigravitySuiteFeatures = {
            applyCompactLayout,
            mountFileContextMenu,
            mountFullTextSearch,
            mountSpeedTelemetry,
            openUsageDashboardModal,
        };
    }
})(typeof window !== 'undefined' ? window : globalThis);
