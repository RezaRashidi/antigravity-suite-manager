'use strict';

/**
 * Surgical, anchor-verified patcher for Antigravity main.js (App in-memory & IDE jetskiAgent/main.js).
 * Fail-open per component: missing anchors skip safely without breaking the bundle.
 */

const INDICATOR_ANCHOR = 'contextUsageIndicator:void 0,';
const COST_MARKER = '.costSummary!==void 0&&(';
const IDENT = '[A-Za-z_$][\\w$]*';

function detectNames(source) {
    const counts = new Map();
    const call = '.useState)';
    const before = new RegExp(`\\(0,(${IDENT})$`);
    for (let at = source.indexOf(call); at !== -1; at = source.indexOf(call, at + 1)) {
        const m = before.exec(source.slice(Math.max(0, at - 40), at));
        if (m) counts.set(m[1], (counts.get(m[1]) || 0) + 1);
    }
    let react = null;
    let best = 0;
    for (const [name, count] of counts) {
        if (count > best) { react = name; best = count; }
    }
    if (!react || best < 20 || !source.includes(`${react}.createElement(`)) {
        return { ok: false, reason: 'React namespace not found' };
    }

    const marker = '{optimisticState:';
    const shape = new RegExp(`(${IDENT})=\\(${IDENT},${IDENT}\\)=>\\{var ${IDENT}=\\[\\],\\{optimisticState:${IDENT},trueState:${IDENT}\\}=${IDENT}\\($`);
    const hooks = [];
    for (let at = source.indexOf(marker); at !== -1; at = source.indexOf(marker, at + 1)) {
        const end = source.indexOf('(', at);
        if (end === -1 || end - at > 200) continue;
        const m = shape.exec(source.slice(Math.max(0, at - 200), end + 1));
        if (m) hooks.push(m);
    }
    if (hooks.length !== 1) {
        return { ok: false, reason: `Conversation state hook matched ${hooks.length} times` };
    }
    return { ok: true, react, stateHook: hooks[0][1] };
}

function indicatorFactory(React, useConversationState) {
    const h = React.createElement;
    const TYPE_LABELS = {
        1: 'System prompt', 2: 'Tools', 3: 'Rules', 4: 'MCP tools', 5: 'Skills',
        6: 'Subagents', 7: 'Chat messages', 8: 'Workflows', 9: 'Plugins', 10: 'Flows',
    };
    const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899', '#06b6d4', '#64748b', '#e07b53', '#8db255', '#c77dba'];
    const selectUsage = (st) => st?.agentState?.contextWindowUsage;
    const selectCompacted = (st) => (st?.agentState?.compactedAtStepIndices?.length ?? 0) > 0;
    const num = (v) => { const n = Number(v ?? 0); return Number.isFinite(n) && n > 0 ? n : 0; };
    const fmtTok = (v) => {
        const n = num(v);
        if (n >= 1e6) return `${(n / 1e6).toFixed(n >= 1e7 ? 1 : 2).replace(/\.?0+$/, '')}M`;
        if (n >= 1e3) return `${(n / 1e3).toFixed(n >= 1e5 ? 0 : 1).replace(/\.0$/, '')}k`;
        return String(Math.round(n));
    };

    function summarize(usage, compacted) {
        const used = num(usage?.estimatedTokensUsed);
        const max = num(usage?.maxContextTokens);
        const ratio = max > 0 ? Math.min(1, used / max) : 0;
        const groups = [];
        for (const g of Array.isArray(usage?.tokenGroups) ? usage.tokenGroups : []) {
            const tokens = num(g?.numTokens);
            if (tokens > 0) groups.push({ label: String(g?.name || TYPE_LABELS[g?.type] || 'Other'), tokens });
        }
        return {
            used, max, ratio, groups,
            compacted: Boolean(compacted) || num(usage?.estimatedAfterCompaction) > 0,
            color: ratio >= 0.85 ? '#ef4444' : ratio >= 0.65 ? '#f59e0b' : 'var(--primary, #3b82f6)',
        };
    }

    function el(tag, css, text) {
        const node = document.createElement(tag);
        if (css) node.style.cssText = css;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function fillPopover(box, info) {
        box.replaceChildren();
        const head = el('div', 'display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px');
        const title = el('div', 'display:flex;align-items:center;gap:6px;font-weight:600;font-size:12.5px');
        title.append(el('span', '', 'Context Window'));
        if (info.compacted) {
            title.append(el('span', 'font-size:10px;padding:1px 6px;border-radius:999px;background:var(--secondary);color:var(--secondary-foreground)', 'Compacted'));
        }
        const totalTxt = info.max > 0 ? `${fmtTok(info.used)} / ${fmtTok(info.max)} (${(info.ratio * 100).toFixed(1)}%)` : (info.used > 0 ? `${fmtTok(info.used)} tokens` : 'Empty');
        head.append(title, el('span', 'font-variant-numeric:tabular-nums;color:var(--secondary-foreground);font-weight:500', totalTxt));
        box.append(head);

        const bar = el('div', 'height:6px;width:100%;border-radius:999px;background:var(--secondary);overflow:hidden;display:flex;margin-bottom:10px');
        if (info.groups.length > 0 && info.max > 0) {
            info.groups.forEach((g, i) => bar.append(el('div', `width:${Math.min(100, (g.tokens / info.max) * 100)}%;height:100%;background:${COLORS[i % COLORS.length]}`)));
        } else {
            bar.append(el('div', `width:${Math.min(100, info.ratio * 100)}%;height:100%;background:${info.color}`));
        }
        box.append(bar);

        if (info.groups.length === 0) {
            box.append(el('div', 'color:var(--muted-foreground);font-size:11.5px', info.max > 0 ? `Remaining: ${fmtTok(Math.max(0, info.max - info.used))}` : 'Send a message to measure context usage.'));
            return;
        }
        const list = el('div', 'display:flex;flex-direction:column;gap:5px');
        info.groups.forEach((g, i) => {
            const row = el('div', 'display:flex;align-items:center;justify-content:space-between;gap:8px');
            const name = el('div', 'display:flex;align-items:center;gap:6px;min-width:0');
            name.append(el('span', `width:7px;height:7px;border-radius:50%;flex-shrink:0;background:${COLORS[i % COLORS.length]}`), el('span', 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap', g.label));
            const base = info.max > 0 ? info.max : info.used;
            const share = base > 0 ? ((g.tokens / base) * 100).toFixed(1) : '0.0';
            row.append(name, el('span', 'font-variant-numeric:tabular-nums;color:var(--secondary-foreground);flex-shrink:0', `${fmtTok(g.tokens)} (${share}%)`));
            list.append(row);
        });
        box.append(list);
    }

    function ContextUsageIndicator({ conversationId }) {
        const [open, setOpen] = React.useState(false);
        const triggerRef = React.useRef(null);
        const boxRef = React.useRef(null);
        const usage = useConversationState(conversationId, { selector: selectUsage });
        const compacted = useConversationState(conversationId, { selector: selectCompacted });
        const info = summarize(usage, compacted);

        React.useEffect(() => {
            if (!open) return undefined;
            const box = el('div', 'position:fixed;width:300px;max-height:min(420px,calc(100vh - 24px));overflow-y:auto;box-sizing:border-box;background:var(--popover,var(--card,#18181b));color:var(--foreground,#f4f4f5);border:1px solid var(--border,rgba(255,255,255,.15));border-radius:12px;box-shadow:0 12px 32px rgba(0,0,0,.35);padding:12px;z-index:99999;font-size:12px;line-height:1.45;direction:ltr');
            box.setAttribute('role', 'dialog');
            document.body.append(box);
            boxRef.current = box;
            const place = () => {
                if (!triggerRef.current) return;
                const r = triggerRef.current.getBoundingClientRect();
                const left = Math.max(12, Math.min(window.innerWidth - 312, r.right - 300));
                const above = r.top > 280 || r.top > window.innerHeight - r.bottom;
                box.style.left = `${left}px`;
                box.style.top = `${above ? r.top - 8 : r.bottom + 8}px`;
                box.style.transform = above ? 'translateY(-100%)' : 'none';
            };
            const onDown = (e) => { if (!triggerRef.current?.contains(e.target) && !box.contains(e.target)) setOpen(false); };
            const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
            place();
            window.addEventListener('mousedown', onDown, true);
            window.addEventListener('keydown', onKey, true);
            window.addEventListener('resize', place);
            return () => {
                window.removeEventListener('mousedown', onDown, true);
                window.removeEventListener('keydown', onKey, true);
                window.removeEventListener('resize', place);
                box.remove();
                boxRef.current = null;
            };
        }, [open]);

        React.useEffect(() => { if (boxRef.current) fillPopover(boxRef.current, info); });

        const pct = info.ratio * 100;
        const label = info.max > 0 ? (pct > 0 && pct < 1 ? '<1%' : `${Math.round(pct)}%`) : '0%';
        const tip = info.max > 0 ? `Context: ${fmtTok(info.used)} / ${fmtTok(info.max)} (${pct.toFixed(1)}%)` : 'Context Window Usage';
        const r = 6;
        const c = 2 * Math.PI * r;
        return h('button', {
            ref: triggerRef, type: 'button', onClick: () => setOpen((v) => !v), title: open ? undefined : tip,
            'data-suite-context-indicator': 'native',
            className: 'flex cursor-pointer items-center h-7 gap-1.5 rounded-full px-2 text-xs text-secondary-foreground select-none outline-none hover:bg-muted transition-colors',
            style: { background: 'transparent', border: 'none' },
        },
        h('svg', { width: 15, height: 15, viewBox: '0 0 16 16', style: { transform: 'rotate(-90deg)', flexShrink: 0 } },
            h('circle', { cx: 8, cy: 8, r, fill: 'none', stroke: 'currentColor', strokeOpacity: 0.25, strokeWidth: 2 }),
            h('circle', { cx: 8, cy: 8, r, fill: 'none', stroke: info.color, strokeWidth: 2, strokeDasharray: c, strokeDashoffset: c * (1 - info.ratio), strokeLinecap: 'round' })
        ),
        h('span', { style: { fontVariantNumeric: 'tabular-nums', fontSize: '11.5px', fontWeight: 500 } }, label));
    }

    class Boundary extends React.Component {
        constructor(props) { super(props); this.state = { failed: false }; }
        static getDerivedStateFromError() { return { failed: true }; }
        componentDidCatch() {}
        render() { return this.state.failed ? null : this.props.children; }
    }
    return function SafeContextIndicator(props) {
        return h(Boundary, null, h(ContextUsageIndicator, props));
    };
}

function costRepricerFactory(table) {
    const rows = table && typeof table === 'object' ? table : {};
    const done = new WeakSet();
    const PRICE_FIELDS = ['inputPricePerMillionTokens', 'outputPricePerMillionTokens', 'cacheReadPricePerMillionTokens'];
    const CATEGORIES = [['input', 0], ['cacheRead', 2], ['output', 1], ['thinking', 1], ['response', 1]];
    const count = (v) => { let n = 0; try { n = Number(v ?? 0); } catch { n = 0; } return Number.isFinite(n) && n > 0 ? n : 0; };
    const keyOf = (name) => {
        if (typeof name !== 'string' || name.length > 200) return '';
        let t = name.trim().toLowerCase().replace(/^.*\//, '').replace(/@.*$/, '');
        while (true) { const n = t.replace(/\s*\([^()]*\)\s*$/, ''); if (n === t) break; t = n; }
        t = t.replace(/[^a-z0-9.]+/g, '-').replace(/^-+|-+$/g, '').replace(/^model-(?:vertex-|google-|anthropic-|openai-)?/, '');
        while (true) { const n = t.replace(/-(?:minimal|low|medium|high|xhigh|thinking|preview|latest|tiered|maas)$/, ''); if (n === t) break; t = n; }
        return t;
    };
    const hasOwnPrices = (p) => PRICE_FIELDS.some((f) => count(p?.[f]) > 0);
    const isEmpty = (s) => Boolean(s) && typeof s === 'object' && count(s.estimatedCostUsd) === 0 && !hasOwnPrices(s.pricing);
    const rateOf = (s) => {
        const p = s?.pricing;
        if (!p || typeof p !== 'object' || hasOwnPrices(p)) return null;
        const k = keyOf(p.modelName);
        if (!k) return null;
        if (Array.isArray(rows[k]) && rows[k].length === 3) return rows[k];
        for (const rk of Object.keys(rows)) {
            if (k.startsWith(rk) || rk.startsWith(k)) return rows[rk];
        }
        if (k.includes('opus')) return [5.0, 25.0, 0.5];
        if (k.includes('claude') || k.includes('sonnet')) return [3.0, 15.0, 0.3];
        if (k.includes('haiku')) return [1.0, 5.0, 0.1];
        if (k.includes('flash') || k.includes('carbon') || k.includes('argon')) return [0.5, 3.0, 0.05];
        if (k.includes('gemini') || k.includes('hydrogen') || k.includes('neon')) return [2.0, 12.0, 0.2];
        return null;
    };
    const tokensOf = (s) => CATEGORIES.map(([n]) => count(s?.[n]?.tokens));
    const usd = (n) => (Number.isFinite(n) && n > 0 ? n : 0);
    const sameMain = (a, b) => a[0] === b[0] && a[1] === b[1] && a[2] === b[2];
    const costsAt = (t, r) => CATEGORIES.map(([, p], i) => (t[i] * r[p]) / 1e6);
    function writeCosts(s, c) {
        CATEGORIES.forEach(([n], i) => { if (s[n] && typeof s[n] === 'object') s[n].estimatedCostUsd = usd(c[i]); });
        s.estimatedCostUsd = usd(c[0] + c[1] + (s.output ? c[2] : c[3] + c[4]));
    }
    function writePrices(s, r, est) {
        const p = s.pricing;
        if (!r || !p || typeof p !== 'object') return;
        p.inputPricePerMillionTokens = r[0];
        p.outputPricePerMillionTokens = r[1];
        p.cacheReadPricePerMillionTokens = r[2];
        p.isEstimated = Boolean(est);
    }
    function fill(s) {
        if (!isEmpty(s)) return null;
        const r = rateOf(s);
        if (!r) return null;
        const c = costsAt(tokensOf(s), r);
        writeCosts(s, c);
        writePrices(s, r, false);
        return c;
    }
    function reprice(summary) {
        if (!summary || typeof summary !== 'object' || done.has(summary)) return summary;
        done.add(summary);
        const steps = [];
        const turnCosts = summary.turnCosts && typeof summary.turnCosts === 'object' ? summary.turnCosts : {};
        for (const id of Object.keys(turnCosts)) {
            const e = turnCosts[id];
            if (!e || typeof e !== 'object') continue;
            const total = e.cumulativeTotal;
            const st = {
                total, open: isEmpty(total), ownRate: rateOf(total), totalTokens: tokensOf(total),
                rate: rateOf(e.turn), turnTokens: tokensOf(e.turn), subTokens: tokensOf(e.subagent),
            };
            st.turnCosts = fill(e.turn);
            st.subCosts = fill(e.subagent);
            steps.push(st);
        }
        const size = (t) => t[0] + t[1] + t[2];
        steps.sort((a, b) => size(a.totalTokens) - size(b.totalTokens));
        let before = [0, 0, 0, 0, 0];
        const sum = [0, 0, 0, 0, 0];
        let estimated = false;
        const add = (cs) => cs.forEach((v, i) => (sum[i] += v));
        for (const st of steps) {
            if (!st.total || typeof st.total !== 'object') continue;
            const grown = st.totalTokens.map((n, i) => Math.max(0, n - before[i]));
            const both = st.turnTokens.map((n, i) => n + st.subTokens[i]);
            if (st.turnCosts && sameMain(grown, st.turnTokens)) add(st.turnCosts);
            else if (st.turnCosts && sameMain(grown, both)) { add(st.turnCosts); if (st.subCosts) add(st.subCosts); }
            else if (st.rate) { add(costsAt(grown, st.rate)); estimated = true; }
            before = st.totalTokens;
            if (st.open) { writeCosts(st.total, sum); writePrices(st.total, st.ownRate, estimated); }
        }
        const subs = summary.subagentCosts && typeof summary.subagentCosts === 'object' ? summary.subagentCosts : {};
        const listedTok = [0, 0, 0, 0, 0], listedCost = [0, 0, 0, 0, 0];
        for (const id of Object.keys(subs)) {
            tokensOf(subs[id]).forEach((n, i) => (listedTok[i] += n));
            const cs = fill(subs[id]);
            if (cs) cs.forEach((v, i) => (listedCost[i] += v));
        }
        const total = summary.total;
        if (total && typeof total === 'object') {
            const all = total.subagent, allTok = tokensOf(all);
            let allCosts = null;
            if (isEmpty(all)) {
                if (rateOf(all)) allCosts = fill(all);
                else if (size(allTok) > 0 && sameMain(allTok, listedTok)) { writeCosts(all, listedCost); allCosts = listedCost; }
            }
            const main = total.turn;
            if (isEmpty(main)) {
                if (steps.length > 0 && sameMain(tokensOf(main), before)) { writeCosts(main, sum); writePrices(main, rateOf(main), estimated); }
                else fill(main);
            }
            const grand = total.cumulativeTotal;
            if (isEmpty(grand)) {
                const r = rateOf(grand), tok = tokensOf(grand);
                if (steps.length === 0 && size(allTok) === 0) fill(grand);
                else {
                    const withSub = before.map((n, i) => n + allTok[i]);
                    if (!sameMain(tok, before)) {
                        if (sameMain(tok, withSub)) { if (allCosts) add(allCosts); }
                        else if (r) { add(costsAt(tok.map((n, i) => Math.max(0, n - before[i])), r)); estimated = true; }
                    }
                    writeCosts(grand, sum);
                    writePrices(grand, r, estimated);
                }
            }
        }
        return summary;
    }
    return function safeReprice(summary) {
        try { return reprice(summary); } catch (_) { return summary; }
    };
}

function findCostPlaces(source) {
    const places = [];
    const nameBefore = new RegExp(`(${IDENT})$`);
    const tail = new RegExp(`^(${IDENT})\\.costSummary=(${IDENT})\\.costSummary\\)`);
    for (let at = source.indexOf(COST_MARKER); at !== -1; at = source.indexOf(COST_MARKER, at + 1)) {
        const from = nameBefore.exec(source.slice(Math.max(0, at - 60), at));
        const rest = tail.exec(source.slice(at + COST_MARKER.length, at + COST_MARKER.length + 200));
        if (!from || !rest || rest[2] !== from[1]) continue;
        places.push({ start: at - from[1].length, end: at + COST_MARKER.length + rest[0].length, from: from[1], to: rest[1] });
    }
    return places;
}

function replaceWindowSlice(source, marker, re, replacer) {
    if (!source.includes(marker)) return { source, count: 0 };
    let out = '';
    let cursor = 0;
    let count = 0;
    for (let at = source.indexOf(marker); at !== -1; at = source.indexOf(marker, at + marker.length)) {
        const winStart = Math.max(cursor, at - 220);
        const winEnd = Math.min(source.length, at + marker.length + 140);
        const slice = source.slice(winStart, winEnd);
        const replaced = slice.replace(re, (...args) => {
            count += 1;
            return replacer(...args);
        });
        out += source.slice(cursor, winStart) + replaced;
        cursor = winEnd;
    }
    out += source.slice(cursor);
    return { source: out, count };
}

function replaceCostDollarIcon(source) {
    // Matches the native 24x24 circular dollar SVG in App (`F.createElement(...)`) and IDE (`d(...)` / `v(...)`)
    const marker = 'M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8';
    const re = new RegExp(
        `(${IDENT}(?:\\.createElement)?)\\(\\s*"circle"\\s*,\\s*\\{\\s*cx:"12"\\s*,\\s*cy:"12"\\s*,\\s*r:"10"\\s*\\}\\s*\\)\\s*,\\s*` +
        `\\1\\(\\s*"path"\\s*,\\s*\\{\\s*d:"M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"\\s*\\}\\s*\\)\\s*,\\s*` +
        `\\1\\(\\s*"path"\\s*,\\s*\\{\\s*d:"M12 18V6"\\s*\\}\\s*\\)`,
        'g'
    );
    return replaceWindowSlice(source, marker, re, (_full, call) => (
        `${call}("path",{d:"M4 20h16"}),` +
        `${call}("path",{d:"M7 16v-5"}),` +
        `${call}("path",{d:"M12 16V6"}),` +
        `${call}("path",{d:"M17 16v-8"})`
    ));
}

function patchSidebarChatLimit(source) {
    let out = source;
    let count = 0;
    const wsRe = new RegExp(`(${IDENT})\\?6:30,(${IDENT})=(${IDENT})\\.items\\.length>`, 'g');
    out = out.replace(wsRe, (_m, aa, tVar, xVar) => {
        count += 1;
        return `(${aa}?(globalThis.__SUITE_SIDEBAR_LIMIT===-1?9999:(globalThis.__SUITE_SIDEBAR_LIMIT>0?globalThis.__SUITE_SIDEBAR_LIMIT:6)):30),${tVar}=${xVar}.items.length>`;
    });
    const pinRe = new RegExp(`Math\\.max\\(0,5-(${IDENT})\\.pinnedIds\\.length\\)`, 'g');
    out = out.replace(pinRe, (_m, oVar) => {
        count += 1;
        return `Math.max(0,(globalThis.__SUITE_SIDEBAR_LIMIT===-1?9999:(globalThis.__SUITE_SIDEBAR_LIMIT>0?globalThis.__SUITE_SIDEBAR_LIMIT:5))-${oVar}.pinnedIds.length)`;
    });
    return { source: out, count };
}

function patchContextTarget(source) {
    let out = source;
    let count = 0;
    const appRe = new RegExp(`checkpointConfig:(${IDENT})\\?(${IDENT})\\((${IDENT}\\.CheckpointConfigSchema),\\{contextWindow:\\1\\}\\):void 0`, 'g');
    out = out.replace(appRe, (_m, rVar, icVar, schemaRef) => {
        count += 1;
        return `checkpointConfig:(${rVar}||globalThis.__SUITE_CONTEXT_TARGET>0)?${icVar}(${schemaRef},{...(${rVar}?{contextWindow:${rVar}}:{}),...(globalThis.__SUITE_CONTEXT_TARGET>0?{maxTokenLimit:Number(globalThis.__SUITE_CONTEXT_TARGET)}:{})}):void 0`;
    });
    const ideRe = new RegExp(`checkpointConfig:(${IDENT})!==void 0\\?(${IDENT})\\((${IDENT}),\\{maxTokenLimit:\\1\\}\\):void 0`, 'g');
    out = out.replace(ideRe, (_m, hVar, beVar, schemaVar) => {
        count += 1;
        return `checkpointConfig:(globalThis.__SUITE_CONTEXT_TARGET>0||${hVar}!==void 0)?${beVar}(${schemaVar},{maxTokenLimit:globalThis.__SUITE_CONTEXT_TARGET>0?Number(globalThis.__SUITE_CONTEXT_TARGET):${hVar}}):void 0`;
    });
    return { source: out, count };
}

function patchMainJs(source, { enableIndicator = false, priceTable = null, replaceCostIcon = true, enableSidebarLimit = false, enableContextTarget = false } = {}) {
    let out = source;
    const report = {
        indicator: { ok: false, skipped: true },
        costs: { ok: false, skipped: true },
        costIcon: { count: 0 },
        sidebarLimit: { count: 0 },
        contextTarget: { count: 0 },
    };

    if (enableIndicator) {
        const idx = out.indexOf(INDICATOR_ANCHOR);
        const det = detectNames(out);
        if (idx !== -1 && det.ok) {
            const expr = `(${indicatorFactory.toString()})(${det.react},${det.stateHook})`;
            out = out.slice(0, idx) + `contextUsageIndicator:{Indicator:${expr}},` + out.slice(idx + INDICATOR_ANCHOR.length);
            report.indicator = { ok: true, skipped: false };
        } else {
            report.indicator = { ok: false, skipped: false, reason: idx === -1 ? 'anchor missing' : det.reason };
        }
    }

    if (priceTable && typeof priceTable === 'object') {
        const places = findCostPlaces(out);
        if (places.length > 0) {
            const fnExpr = `(${costRepricerFactory.toString()})(${JSON.stringify(priceTable)})`;
            for (let i = places.length - 1; i >= 0; i -= 1) {
                const p = places[i];
                const repl = `${p.from}.costSummary!==void 0&&(${p.to}.costSummary=(${fnExpr})(${p.from}.costSummary))`;
                out = out.slice(0, p.start) + repl + out.slice(p.end);
            }
            report.costs = { ok: true, skipped: false, count: places.length };
        } else {
            report.costs = { ok: false, skipped: false, reason: 'costSummary anchor missing' };
        }
    }

    if (replaceCostIcon) {
        const iconRes = replaceCostDollarIcon(out);
        out = iconRes.source;
        report.costIcon = { count: iconRes.count };
    }

    if (enableSidebarLimit) {
        const sbRes = patchSidebarChatLimit(out);
        out = sbRes.source;
        report.sidebarLimit = { count: sbRes.count };
    }

    if (enableContextTarget) {
        const ctRes = patchContextTarget(out);
        out = ctRes.source;
        report.contextTarget = { count: ctRes.count };
    }

    return { source: out, report };
}

function restoreCostDollarIcon(source) {
    const marker = 'd:"M4 20h16"';
    const re = new RegExp(
        `(${IDENT}(?:\\.createElement)?)\\(\\s*"path"\\s*,\\s*\\{\\s*d:"M4 20h16"\\s*\\}\\s*\\)\\s*,\\s*` +
        `\\1\\(\\s*"path"\\s*,\\s*\\{\\s*d:"M7 16v-5"\\s*\\}\\s*\\)\\s*,\\s*` +
        `\\1\\(\\s*"path"\\s*,\\s*\\{\\s*d:"M12 16V6"\\s*\\}\\s*\\)\\s*,\\s*` +
        `\\1\\(\\s*"path"\\s*,\\s*\\{\\s*d:"M17 16v-8"\\s*\\}\\s*\\)`,
        'g'
    );
    return replaceWindowSlice(source, marker, re, (_full, call) => (
        `${call}("circle",{cx:"12",cy:"12",r:"10"}),` +
        `${call}("path",{d:"M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"}),` +
        `${call}("path",{d:"M12 18V6"})`
    ));
}

module.exports = {
    INDICATOR_ANCHOR,
    COST_MARKER,
    detectNames,
    findCostPlaces,
    replaceCostDollarIcon,
    restoreCostDollarIcon,
    patchSidebarChatLimit,
    patchContextTarget,
    patchMainJs,
    indicatorFactory,
    costRepricerFactory,
};
