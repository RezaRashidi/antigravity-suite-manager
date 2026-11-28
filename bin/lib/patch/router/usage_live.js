'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { readCachedPrices, resolveModelRate } = require('./pricing.js');

const _liveTurnStats = new Map();
let _dashboardCache = null;

function getHome() {
    return process.env.REAL_HOME || os.homedir();
}

function readContextTargetOverride() {
    try {
        const expPath = path.join(getHome(), '.config', 'antigravity', 'experiments.json');
        if (fs.existsSync(expPath)) {
            const raw = JSON.parse(fs.readFileSync(expPath, 'utf8'));
            const t = Number(raw?.config?.contextTarget || 0);
            if ([256000, 500000, 1000000].includes(t)) return t;
        }
    } catch (_) {}
    return 0;
}

function loadCascadeBindingsMap() {
    const home = getHome();
    const out = {};
    for (const p of [
        path.join(home, '.config', 'antigravity', 'accounts', 'bindings.json'),
        path.join(home, '.config', 'antigravity', 'multi_account_bindings.json'),
    ]) {
        if (!fs.existsSync(p)) continue;
        try {
            const raw = JSON.parse(fs.readFileSync(p, 'utf8'));
            if (!raw || typeof raw !== 'object') continue;
            for (const [k, v] of Object.entries(raw)) {
                if (k.startsWith('__')) continue;
                if (v && typeof v === 'object' && v.email) out[k] = String(v.email);
                else if (typeof v === 'string' && v) out[k] = v;
            }
            if (Object.keys(out).length) break;
        } catch (_) {}
    }
    return out;
}

function recordStreamStart(cascadeId, requestedModel) {
    if (!cascadeId) return;
    const now = Date.now();
    const prev = _liveTurnStats.get(cascadeId) || {};
    _liveTurnStats.set(cascadeId, {
        ...prev,
        model: requestedModel || prev.model || null,
        startedAt: now,
        firstTokenAt: null,
        lastChunkAt: now,
        endedAt: null,
        ttftMs: prev.ttftMs || 0,
        tokPerSec: prev.tokPerSec || 0,
        lastTurnDurationMs: prev.lastTurnDurationMs || 0,
        active: true,
    });
}

function recordStreamUsageChunk(cascadeId, chunkStr, requestedModel) {
    if (!cascadeId || !chunkStr) return;
    const now = Date.now();
    const cur = _liveTurnStats.get(cascadeId) || { startedAt: now };
    if (!cur.firstTokenAt && (chunkStr.includes('"text"') || chunkStr.includes('"candidatesTokenCount"') || chunkStr.includes('"thoughtsTokenCount"'))) {
        cur.firstTokenAt = now;
        if (cur.startedAt) cur.ttftMs = Math.max(1, now - cur.startedAt);
    }
    cur.lastChunkAt = now;

    const mPrompt = chunkStr.match(/"promptTokenCount"\s*:\s*(\d+)/);
    const mCache = chunkStr.match(/"cachedContentTokenCount"\s*:\s*(\d+)/);
    const mOut = chunkStr.match(/"candidatesTokenCount"\s*:\s*(\d+)/);
    const mThink = chunkStr.match(/"thoughtsTokenCount"\s*:\s*(\d+)/);
    if (mPrompt || mOut) {
        const promptTotal = Number(mPrompt?.[1] || cur.promptTotal || 0);
        const cacheRead = Number(mCache?.[1] || cur.cacheRead || 0);
        const output = Number(mOut?.[1] || 0) + Number(mThink?.[1] || 0);
        cur.promptTotal = promptTotal;
        cur.cacheRead = cacheRead;
        cur.uncachedInput = Math.max(0, promptTotal - cacheRead);
        cur.output = output;
        const genAnchor = cur.firstTokenAt || cur.startedAt || now;
        const genSec = Math.max(0.2, (now - genAnchor) / 1000);
        if (output > 0) cur.tokPerSec = Math.round((output / genSec) * 10) / 10;
    }
    if (requestedModel) cur.model = requestedModel;
    cur.updatedAt = now;
    _liveTurnStats.set(cascadeId, cur);
    _dashboardCache = null;
}

function recordStreamEnd(cascadeId) {
    if (!cascadeId) return;
    const cur = _liveTurnStats.get(cascadeId);
    if (!cur) return;
    const now = Date.now();
    cur.endedAt = now;
    cur.active = false;
    if (cur.startedAt) cur.lastTurnDurationMs = Math.max(1, now - cur.startedAt);
    if (cur.output > 0) {
        const genAnchor = cur.firstTokenAt || cur.startedAt || now;
        const genSec = Math.max(0.2, (now - genAnchor) / 1000);
        cur.tokPerSec = Math.round((cur.output / genSec) * 10) / 10;
    }
    cur.updatedAt = now;
    _liveTurnStats.set(cascadeId, cur);
    _dashboardCache = null;
}

function parseIsoMs(ts) {
    if (typeof ts !== 'string' || !ts.trim()) return 0;
    const ms = Date.parse(ts.trim());
    return Number.isFinite(ms) ? ms : 0;
}

function scanTranscriptSummary(tPath, pricing, contextOverride = 0) {
    const turns = [];
    let lastModel = 'unknown';
    let lastTurnContext = 0;
    let lastTurnCost = 0;
    let totalInput = 0;
    let totalCache = 0;
    let totalOutput = 0;
    let sessionCost = 0;
    let cacheSavings = 0;
    let title = '';
    const cacheAnomalies = [];
    const seen = new Set();

    let lines;
    try {
        if (!fs.existsSync(tPath)) return null;
        lines = fs.readFileSync(tPath, 'utf8').split('\n');
    } catch (_) {
        return null;
    }

    let prevHit = null;
    let prevMs = 0;
    let lastReqMs = 0;

    for (const line of lines) {
        if (!line.trim()) continue;
        let row;
        try { row = JSON.parse(line); } catch (_) { continue; }
        if (typeof row.model === 'string' && row.model.trim()) lastModel = row.model.trim();
        const tsMs = parseIsoMs(row.timestamp || row.created_at || row.createdAt || '');
        const role = String(row.role || row.type || '').toLowerCase();
        if (!title && (role === 'user' || row.user_input)) {
            const rawTxt = String(row.user_input || row.text || row.content || '').trim();
            if (rawTxt && !rawTxt.startsWith('<CONTEXT_SUMMARY>')) {
                title = rawTxt.replace(/\s+/g, ' ').slice(0, 72);
            }
        }
        if (role === 'user' && tsMs > 0) lastReqMs = tsMs;

        const hasTok = ('input_tokens' in row) || ('cache_read_tokens' in row) || ('output_tokens' in row);
        if (!hasTok) continue;
        const stepKey = row.step_index != null ? row.step_index : line;
        if (seen.has(stepKey)) continue;
        seen.add(stepKey);

        const inp = Math.max(0, Number(row.input_tokens || 0));
        const cr = Math.max(0, Number(row.cache_read_tokens || 0));
        const out = Math.max(0, Number(row.output_tokens || 0));
        if (inp === 0 && cr === 0 && out === 0) continue;

        const rate = resolveModelRate(lastModel, pricing);
        const turnCost = ((inp * rate.input) + (cr * (rate.cache_read ?? rate.input)) + (out * rate.output)) / 1e6;
        const savings = Math.max(0, (cr * Math.max(0, rate.input - (rate.cache_read ?? rate.input))) / 1e6);
        const promptTot = inp + cr;
        const hitPct = promptTot > 0 ? Math.round((cr / promptTot) * 1000) / 10 : 0;
        const durationMs = (tsMs > 0 && lastReqMs > 0 && tsMs >= lastReqMs) ? (tsMs - lastReqMs) : (Number(row.duration_ms || row.latency_ms || 0) || 0);
        const tokPerSec = (durationMs >= 200 && out > 0) ? Math.round((out / (durationMs / 1000)) * 10) / 10 : 0;

        let anomaly = false;
        if (prevHit !== null && prevHit >= 50 && hitPct < prevHit - 25 && tsMs > 0 && prevMs > 0 && (tsMs - prevMs) <= 300000) {
            anomaly = true;
            cacheAnomalies.push({
                stepIndex: row.step_index ?? turns.length,
                prevHitPct: prevHit,
                hitPct,
                dropPct: Math.round((prevHit - hitPct) * 10) / 10,
                timestamp: row.timestamp || row.created_at || null,
            });
        }
        prevHit = hitPct;
        if (tsMs > 0) prevMs = tsMs;

        totalInput += inp;
        totalCache += cr;
        totalOutput += out;
        sessionCost += turnCost;
        cacheSavings += savings;
        lastTurnContext = promptTot;
        lastTurnCost = turnCost;

        turns.push({
            stepIndex: row.step_index ?? turns.length,
            model: lastModel,
            inputTokens: inp,
            cacheReadTokens: cr,
            outputTokens: out,
            cacheHitPct: hitPct,
            costUsd: Math.round(turnCost * 1e6) / 1e6,
            durationMs,
            tokPerSec,
            timestamp: row.timestamp || row.created_at || null,
            tsMs,
            anomaly,
        });
    }

    const rate = resolveModelRate(lastModel, pricing);
    const contextLimit = contextOverride > 0 ? contextOverride : (rate.context_limit || 1048576);
    const totalPrompt = totalInput + totalCache;

    return {
        title,
        lastModel: lastModel !== 'unknown' ? lastModel : null,
        contextLimit,
        lastTurnContext,
        lastTurnCost,
        totalInput,
        totalCache,
        totalOutput,
        sessionCost,
        cacheSavings,
        cacheHitPct: totalPrompt > 0 ? Math.round((totalCache / totalPrompt) * 1000) / 10 : 0,
        turns,
        cacheAnomalies,
        lastTsMs: turns.length ? turns[turns.length - 1].tsMs : parseIsoMs(null),
    };
}

function readSubagentStats(brainDir, cascadeId, pricing, bindingsMap) {
    const subDir = path.join(brainDir, cascadeId, '.system_generated', 'subagents');
    if (!fs.existsSync(subDir)) return [];
    const out = [];
    try {
        for (const f of fs.readdirSync(subDir)) {
            if (!f.endsWith('.json')) continue;
            const subId = f.slice(0, -5);
            try {
                const raw = JSON.parse(fs.readFileSync(path.join(subDir, f), 'utf8'));
                const subTPath = path.join(brainDir, subId, '.system_generated', 'logs', 'transcript.jsonl');
                const subSum = scanTranscriptSummary(subTPath, pricing);
                out.push({
                    subagentId: subId,
                    role: raw.subagentDescriptor?.role || raw.role || 'Subagent',
                    state: raw.state || 'DONE',
                    accountEmail: bindingsMap[subId] || bindingsMap[cascadeId] || null,
                    turns: subSum ? subSum.turns.length : 0,
                    tokens: subSum ? (subSum.totalInput + subSum.totalCache + subSum.totalOutput) : 0,
                    cacheHitPct: subSum ? subSum.cacheHitPct : 0,
                    costUsd: subSum ? Math.round(subSum.sessionCost * 1e6) / 1e6 : 0,
                });
            } catch (_) {}
        }
    } catch (_) {}
    return out;
}

function getActiveCascadeUsage(cascadeId) {
    const pricing = readCachedPrices();
    const brainDir = path.join(getHome(), '.gemini', 'antigravity', 'brain');
    const contextOverride = readContextTargetOverride();
    const bindingsMap = loadCascadeBindingsMap();

    const summary = {
        cascadeId: cascadeId || null,
        accountEmail: (cascadeId && bindingsMap[cascadeId]) || null,
        model: null,
        contextLimit: contextOverride || 200000,
        contextTarget: contextOverride,
        currentContextTokens: 0,
        contextPct: 0,
        totalInputTokens: 0,
        totalCacheReadTokens: 0,
        totalOutputTokens: 0,
        cacheHitPct: 0,
        sessionCostUsd: 0,
        lastTurnCostUsd: 0,
        cacheSavingsUsd: 0,
        turns: 0,
        ttftMs: 0,
        tokPerSec: 0,
        avgTokPerSec: 0,
        lastTurnDurationMs: 0,
        cacheAnomalies: [],
        turnsList: [],
        subagents: [],
        pricingSource: pricing.source,
    };

    const live = cascadeId ? _liveTurnStats.get(cascadeId) : null;
    if (!cascadeId || cascadeId === 'default' || cascadeId === '__default__') {
        if (live) {
            const rate = resolveModelRate(live.model || '', pricing);
            summary.model = live.model;
            summary.contextLimit = contextOverride || rate.context_limit || 200000;
            summary.currentContextTokens = live.promptTotal || 0;
            summary.contextPct = Math.min(100, Math.round((summary.currentContextTokens / summary.contextLimit) * 1000) / 10);
            summary.ttftMs = live.ttftMs || 0;
            summary.tokPerSec = live.tokPerSec || 0;
            summary.lastTurnDurationMs = live.lastTurnDurationMs || 0;
        }
        return summary;
    }

    const tPath = path.join(brainDir, cascadeId, '.system_generated', 'logs', 'transcript.jsonl');
    const scanned = scanTranscriptSummary(tPath, pricing, contextOverride);
    if (scanned) {
        summary.turns = scanned.turns.length;
        summary.totalInputTokens = scanned.totalInput;
        summary.totalCacheReadTokens = scanned.totalCache;
        summary.totalOutputTokens = scanned.totalOutput;
        summary.sessionCostUsd = Math.round(scanned.sessionCost * 1e6) / 1e6;
        summary.lastTurnCostUsd = Math.round(scanned.lastTurnCost * 1e6) / 1e6;
        summary.cacheSavingsUsd = Math.round(scanned.cacheSavings * 1e6) / 1e6;
        summary.cacheHitPct = scanned.cacheHitPct;
        summary.currentContextTokens = scanned.lastTurnContext;
        summary.model = scanned.lastModel;
        summary.contextLimit = scanned.contextLimit;
        summary.cacheAnomalies = scanned.cacheAnomalies;
        summary.turnsList = scanned.turns.slice(-40);
        const speedTurns = scanned.turns.filter((t) => t.tokPerSec > 0);
        if (speedTurns.length) {
            summary.avgTokPerSec = Math.round((speedTurns.reduce((a, b) => a + b.tokPerSec, 0) / speedTurns.length) * 10) / 10;
        }
    }

    if (live) {
        if (!summary.model && live.model) {
            summary.model = live.model;
            const rate = resolveModelRate(live.model, pricing);
            summary.contextLimit = contextOverride || rate.context_limit || 1048576;
        }
        if (live.promptTotal > 0 && (summary.currentContextTokens === 0 || live.updatedAt > Date.now() - 120000)) {
            summary.currentContextTokens = Math.max(summary.currentContextTokens, live.promptTotal);
        }
        summary.ttftMs = live.ttftMs || 0;
        summary.tokPerSec = live.tokPerSec || summary.avgTokPerSec || 0;
        summary.lastTurnDurationMs = live.lastTurnDurationMs || 0;
    } else if (summary.turnsList.length) {
        const lastT = summary.turnsList[summary.turnsList.length - 1];
        summary.tokPerSec = lastT.tokPerSec || summary.avgTokPerSec || 0;
        summary.lastTurnDurationMs = lastT.durationMs || 0;
    }

    summary.contextPct = summary.contextLimit > 0 ? Math.min(100, Math.round((summary.currentContextTokens / summary.contextLimit) * 1000) / 10) : 0;
    summary.subagents = readSubagentStats(brainDir, cascadeId, pricing, bindingsMap);
    return summary;
}

function getRangeCutoffMs(range) {
    const now = Date.now();
    const d = new Date(now);
    if (range === 'today') {
        d.setHours(0, 0, 0, 0);
        return d.getTime();
    }
    if (range === '24h') return now - 86400000;
    if (range === 'weeklyQuota' || range === '7d') return now - 7 * 86400000;
    if (range === '30d' || range === 'month') return now - 30 * 86400000;
    return 0;
}

function scanAllSessionsCached() {
    const now = Date.now();
    if (_dashboardCache && now - _dashboardCache.builtAt < 15000) {
        return _dashboardCache.sessions;
    }
    const pricing = readCachedPrices();
    const brainDir = path.join(getHome(), '.gemini', 'antigravity', 'brain');
    const bindingsMap = loadCascadeBindingsMap();
    const sessions = [];

    if (fs.existsSync(brainDir)) {
        for (const cid of fs.readdirSync(brainDir)) {
            const tPath = path.join(brainDir, cid, '.system_generated', 'logs', 'transcript.jsonl');
            if (!fs.existsSync(tPath)) continue;
            let mtimeMs = 0;
            try { mtimeMs = fs.statSync(tPath).mtimeMs; } catch (_) {}
            const scanned = scanTranscriptSummary(tPath, pricing, 0);
            if (!scanned || !scanned.turns.length) continue;
            sessions.push({
                cascadeId: cid,
                title: scanned.title || cid.slice(0, 8),
                accountEmail: bindingsMap[cid] || 'unbound',
                model: scanned.lastModel || 'unknown',
                mtimeMs,
                turns: scanned.turns,
                cacheAnomalies: scanned.cacheAnomalies,
            });
        }
    }
    _dashboardCache = { builtAt: now, sessions };
    return sessions;
}

function getMultiAccountDashboard({ range = '7d', account = 'all' } = {}) {
    const cutoff = getRangeCutoffMs(range);
    const sessions = scanAllSessionsCached();
    const accountSet = new Set();
    const byAccount = {};
    const byModel = {};
    const heatmap = {};
    const recentSessions = [];
    const anomalies = [];

    const ensureAcc = (em) => {
        if (!byAccount[em]) {
            byAccount[em] = { email: em, sessions: 0, turns: 0, inputTokens: 0, cacheReadTokens: 0, outputTokens: 0, costUsd: 0, cacheSavingsUsd: 0, anomalies: 0 };
        }
        return byAccount[em];
    };

    const totals = { sessions: 0, turns: 0, inputTokens: 0, cacheReadTokens: 0, outputTokens: 0, costUsd: 0, cacheSavingsUsd: 0, cacheHitPct: 0, anomalies: 0 };
    const pricing = readCachedPrices();
    const heatmapCutoff = Date.now() - 371 * 86400000;

    for (const s of sessions) {
        accountSet.add(s.accountEmail);
        const filteredTurns = s.turns.filter((t) => cutoff === 0 || (t.tsMs > 0 ? t.tsMs >= cutoff : s.mtimeMs >= cutoff));

        // Populate 53-week heatmap for selected account (independent of short range filter)
        if (account === 'all' || s.accountEmail === account) {
            for (const t of s.turns) {
                const ms = t.tsMs || s.mtimeMs;
                if (ms >= heatmapCutoff) {
                    const day = new Date(ms).toISOString().slice(0, 10);
                    if (!heatmap[day]) heatmap[day] = { tokens: 0, costUsd: 0, turns: 0 };
                    heatmap[day].tokens += t.inputTokens + t.cacheReadTokens + t.outputTokens;
                    heatmap[day].costUsd += t.costUsd;
                    heatmap[day].turns += 1;
                }
            }
        }

        if (!filteredTurns.length) continue;

        let sInp = 0, sCache = 0, sOut = 0, sCost = 0, sSave = 0;
        const sAnomCount = filteredTurns.filter((t) => t.anomaly).length;
        for (const t of filteredTurns) {
            sInp += t.inputTokens;
            sCache += t.cacheReadTokens;
            sOut += t.outputTokens;
            sCost += t.costUsd;
            const r = resolveModelRate(t.model, pricing);
            sSave += Math.max(0, (t.cacheReadTokens * Math.max(0, r.input - (r.cache_read ?? r.input))) / 1e6);

            if (account === 'all' || s.accountEmail === account) {
                if (!byModel[t.model]) {
                    byModel[t.model] = { model: t.model, turns: 0, inputTokens: 0, cacheReadTokens: 0, outputTokens: 0, costUsd: 0 };
                }
                const m = byModel[t.model];
                m.turns += 1;
                m.inputTokens += t.inputTokens;
                m.cacheReadTokens += t.cacheReadTokens;
                m.outputTokens += t.outputTokens;
                m.costUsd += t.costUsd;
            }
        }

        const acc = ensureAcc(s.accountEmail);
        acc.sessions += 1;
        acc.turns += filteredTurns.length;
        acc.inputTokens += sInp;
        acc.cacheReadTokens += sCache;
        acc.outputTokens += sOut;
        acc.costUsd += sCost;
        acc.cacheSavingsUsd += sSave;
        acc.anomalies += sAnomCount;

        if (account !== 'all' && s.accountEmail !== account) continue;

        totals.sessions += 1;
        totals.turns += filteredTurns.length;
        totals.inputTokens += sInp;
        totals.cacheReadTokens += sCache;
        totals.outputTokens += sOut;
        totals.costUsd += sCost;
        totals.cacheSavingsUsd += sSave;
        totals.anomalies += sAnomCount;

        const promptTot = sInp + sCache;
        recentSessions.push({
            cascadeId: s.cascadeId,
            title: s.title,
            accountEmail: s.accountEmail,
            model: s.model,
            turns: filteredTurns.length,
            totalTokens: sInp + sCache + sOut,
            cacheHitPct: promptTot > 0 ? Math.round((sCache / promptTot) * 1000) / 10 : 0,
            costUsd: Math.round(sCost * 1e6) / 1e6,
            anomalies: sAnomCount,
            updatedAt: s.mtimeMs,
        });
        for (const a of s.cacheAnomalies) {
            const ms = a.timestamp ? parseIsoMs(a.timestamp) : s.mtimeMs;
            if (cutoff === 0 || ms >= cutoff) {
                anomalies.push({ cascadeId: s.cascadeId, title: s.title, accountEmail: s.accountEmail, ...a });
            }
        }
    }

    const totalPrompt = totals.inputTokens + totals.cacheReadTokens;
    totals.cacheHitPct = totalPrompt > 0 ? Math.round((totals.cacheReadTokens / totalPrompt) * 1000) / 10 : 0;
    totals.costUsd = Math.round(totals.costUsd * 1e6) / 1e6;
    totals.cacheSavingsUsd = Math.round(totals.cacheSavingsUsd * 1e6) / 1e6;

    const accountsList = Object.values(byAccount).map((a) => {
        const pt = a.inputTokens + a.cacheReadTokens;
        return {
            ...a,
            totalTokens: pt + a.outputTokens,
            cacheHitPct: pt > 0 ? Math.round((a.cacheReadTokens / pt) * 1000) / 10 : 0,
            costUsd: Math.round(a.costUsd * 1e6) / 1e6,
            cacheSavingsUsd: Math.round(a.cacheSavingsUsd * 1e6) / 1e6,
        };
    }).sort((a, b) => b.costUsd - a.costUsd || b.totalTokens - a.totalTokens);

    const modelsList = Object.values(byModel).map((m) => {
        const pt = m.inputTokens + m.cacheReadTokens;
        return {
            ...m,
            totalTokens: pt + m.outputTokens,
            cacheHitPct: pt > 0 ? Math.round((m.cacheReadTokens / pt) * 1000) / 10 : 0,
            costUsd: Math.round(m.costUsd * 1e6) / 1e6,
        };
    }).sort((a, b) => b.costUsd - a.costUsd || b.totalTokens - a.totalTokens);

    recentSessions.sort((a, b) => b.updatedAt - a.updatedAt);
    return {
        range,
        accountFilter: account,
        availableAccounts: Array.from(accountSet).sort(),
        totals,
        accounts: accountsList,
        models: modelsList,
        heatmap,
        recentSessions: recentSessions.slice(0, 25),
        anomalies: anomalies.slice(-15).reverse(),
        pricingSource: pricing.source,
    };
}

function searchAllTranscripts(query, limit = 25) {
    const q = String(query || '').trim().toLowerCase();
    if (q.length < 2) return { query: q, results: [] };
    const brainDir = path.join(getHome(), '.gemini', 'antigravity', 'brain');
    if (!fs.existsSync(brainDir)) return { query: q, results: [] };

    const bindingsMap = loadCascadeBindingsMap();
    const candidates = [];
    for (const cid of fs.readdirSync(brainDir)) {
        const tPath = path.join(brainDir, cid, '.system_generated', 'logs', 'transcript.jsonl');
        if (!fs.existsSync(tPath)) continue;
        try {
            candidates.push({ cid, tPath, mtimeMs: fs.statSync(tPath).mtimeMs });
        } catch (_) {}
    }
    candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);

    const results = [];
    for (const item of candidates) {
        if (results.length >= limit) break;
        let text;
        try { text = fs.readFileSync(item.tPath, 'utf8'); } catch (_) { continue; }
        if (!text.toLowerCase().includes(q)) continue;

        let title = '';
        let match = null;
        for (const line of text.split('\n')) {
            if (!line.trim()) continue;
            let row;
            try { row = JSON.parse(line); } catch (_) { continue; }
            const role = String(row.role || row.type || 'message').toLowerCase();
            const bodyParts = [];
            for (const f of ['user_input', 'assistant_response', 'text', 'content', 'command', 'output']) {
                if (typeof row[f] === 'string' && row[f].trim()) bodyParts.push(row[f].trim());
            }
            if (Array.isArray(row.tool_calls)) {
                for (const tc of row.tool_calls) {
                    if (tc?.name) bodyParts.push(tc.name);
                    if (tc?.arguments) bodyParts.push(typeof tc.arguments === 'string' ? tc.arguments : JSON.stringify(tc.arguments));
                }
            }
            const joined = bodyParts.join(' ').replace(/\s+/g, ' ');
            if (!title && (role === 'user' || row.user_input) && joined && !joined.startsWith('<CONTEXT_SUMMARY>')) {
                title = joined.slice(0, 72);
            }
            if (!match) {
                const pos = joined.toLowerCase().indexOf(q);
                if (pos !== -1) {
                    const s = Math.max(0, pos - 48);
                    const e = Math.min(joined.length, pos + q.length + 96);
                    match = {
                        stepIndex: row.step_index ?? null,
                        role,
                        snippet: (s > 0 ? '...' : '') + joined.slice(s, e) + (e < joined.length ? '...' : ''),
                        timestamp: row.timestamp || row.created_at || null,
                    };
                }
            }
            if (title && match) break;
        }

        if (match) {
            results.push({
                cascadeId: item.cid,
                title: title || item.cid.slice(0, 8),
                accountEmail: bindingsMap[item.cid] || null,
                updatedAt: item.mtimeMs,
                ...match,
            });
        }
    }
    return { query: q, results };
}

module.exports = {
    recordStreamStart,
    recordStreamUsageChunk,
    recordStreamEnd,
    getActiveCascadeUsage,
    getMultiAccountDashboard,
    searchAllTranscripts,
};
