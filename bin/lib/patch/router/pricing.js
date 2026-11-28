'use strict';

const fs = require('fs');
const https = require('https');
const os = require('os');
const path = require('path');

const PRICES_URL = 'https://models.dev/api.json';
const CACHE_TTL_MS = 24 * 3600 * 1000;
const RETRY_MS = 3600 * 1000;

// Fallback USD per 1M tokens + context window limits (matches Python usage/pricing.py)
const FALLBACK_RATES = {
    'gemini-2.5-pro': { name: 'Gemini 2.5 Pro', input: 1.25, output: 10.0, cache_read: 0.3125, context_limit: 1048576 },
    'gemini-2.5-flash': { name: 'Gemini 2.5 Flash', input: 0.3, output: 2.5, cache_read: 0.075, context_limit: 1048576 },
    'gemini-2.5-flash-lite': { name: 'Gemini 2.5 Flash Lite', input: 0.1, output: 0.4, cache_read: 0.025, context_limit: 1048576 },
    'gemini-3-pro': { name: 'Gemini 3 Pro', input: 2.0, output: 12.0, cache_read: 0.2, context_limit: 1048576 },
    'gemini-3.5-flash': { name: 'Gemini 3.5 Flash', input: 0.5, output: 3.0, cache_read: 0.05, context_limit: 1048576 },
    'gemini-3.8-flash': { name: 'Gemini 3.8 Flash', input: 0.5, output: 3.0, cache_read: 0.05, context_limit: 1048576 },
    'gemini-4-carbon': { name: 'Gemini 4 Carbon', input: 0.5, output: 3.0, cache_read: 0.05, context_limit: 1048576 },
    'gemini-4-argon': { name: 'Gemini 4 Argon', input: 0.5, output: 3.0, cache_read: 0.05, context_limit: 1048576 },
    'gemini-4-hydrogen': { name: 'Gemini 4 Hydrogen', input: 2.0, output: 12.0, cache_read: 0.2, context_limit: 1048576 },
    'gemini-4-neon': { name: 'Gemini 4 Neon', input: 2.0, output: 12.0, cache_read: 0.2, context_limit: 1048576 },
    'claude-sonnet-4-5': { name: 'Claude Sonnet 4.5', input: 3.0, output: 15.0, cache_read: 0.3, context_limit: 200000 },
    'claude-sonnet-4-6': { name: 'Claude Sonnet 4.6', input: 3.0, output: 15.0, cache_read: 0.3, context_limit: 200000 },
    'claude-sonnet-5-5': { name: 'Claude Sonnet 5.5', input: 3.0, output: 15.0, cache_read: 0.3, context_limit: 200000 },
    'claude-opus-4-5': { name: 'Claude Opus 4.5', input: 5.0, output: 25.0, cache_read: 0.5, context_limit: 200000 },
    'claude-opus-4-6': { name: 'Claude Opus 4.6', input: 5.0, output: 25.0, cache_read: 0.5, context_limit: 200000 },
    'claude-haiku-4-5': { name: 'Claude Haiku 4.5', input: 1.0, output: 5.0, cache_read: 0.1, context_limit: 200000 },
    'gpt-oss-120b': { name: 'GPT OSS 120B', input: 0.15, output: 0.6, cache_read: 0.15, context_limit: 131072 },
};

function getCacheFile() {
    const rh = process.env.REAL_HOME || os.homedir();
    return path.join(rh, '.config', 'antigravity', 'model_prices.json');
}

function normalizeModelKey(name) {
    if (typeof name !== 'string' || !name) return 'unknown';
    let s = name.trim().toLowerCase();
    s = s.replace(/^.*\//, '').replace(/@.*$/, '');
    while (true) {
        const next = s.replace(/\s*\([^()]*\)\s*$/, '');
        if (next === s) break;
        s = next;
    }
    s = s.replace(/^model_(?:vertex|anthropic|openai|google)_/, '').replace(/^model_/, '');
    s = s.replace(/[^a-z0-9.\-]+/g, '-').replace(/^-+|-+$/g, '');
    s = s.replace(/^model-(?:vertex|anthropic|openai|google)-/, '').replace(/^model-/, '');
    while (true) {
        const next = s.replace(/-(?:minimal|low|medium|high|xhigh|thinking|preview|latest|tiered|maas)$/, '');
        if (next === s) break;
        s = next;
    }
    return s || 'unknown';
}

function safeNum(v) {
    return typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1000 ? v : null;
}

function extractModelsDevRates(api) {
    const out = {};
    if (!api || typeof api !== 'object') return out;
    for (const provider of ['google-vertex', 'google', 'anthropic', 'google-vertex-anthropic']) {
        const models = api[provider] && api[provider].models;
        if (!models || typeof models !== 'object') continue;
        for (const [id, info] of Object.entries(models)) {
            if (!info || typeof info !== 'object' || !info.cost) continue;
            const input = safeNum(info.cost.input);
            const output = safeNum(info.cost.output);
            if (input === null || output === null || (input === 0 && output === 0)) continue;
            const cr = safeNum(info.cost.cache_read);
            const ctx = safeNum(info.limit && info.limit.context) || (id.toLowerCase().includes('claude') ? 200000 : 1048576);
            const key = normalizeModelKey(id);
            if (!out[key]) {
                out[key] = {
                    name: String(info.name || id).slice(0, 80),
                    input,
                    output,
                    cache_read: cr !== null ? cr : input,
                    context_limit: ctx,
                };
            }
        }
    }
    return out;
}

let _inFlightRefresh = null;
let _lastAttemptTs = 0;

function readCachedPrices() {
    const file = getCacheFile();
    let cached = {};
    let fetchedAt = 0;
    let source = 'fallback';
    try {
        if (fs.existsSync(file)) {
            const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
            if (parsed && parsed.models && typeof parsed.models === 'object') {
                cached = parsed.models;
                fetchedAt = Number(parsed.fetchedAt || 0);
                if (Object.keys(cached).length > 0) source = 'models.dev (cached)';
            }
        }
    } catch (_) {}
    const models = { ...FALLBACK_RATES, ...cached };
    return { source, fetchedAt, models };
}

function triggerBackgroundRefresh(force = false) {
    if (process.env.ANTIGRAVITY_NO_PRICE_FETCH === '1') return Promise.resolve(false);
    const now = Date.now();
    const cur = readCachedPrices();
    const ageMs = cur.fetchedAt > 1e12 ? (now - cur.fetchedAt) : (now - cur.fetchedAt * 1000);
    if (!force && cur.fetchedAt > 0 && ageMs < CACHE_TTL_MS) return Promise.resolve(false);
    if (!force && (now - _lastAttemptTs) < RETRY_MS) return Promise.resolve(false);
    if (_inFlightRefresh) return _inFlightRefresh;

    _lastAttemptTs = now;
    _inFlightRefresh = new Promise((resolve) => {
        const req = https.get(PRICES_URL, { headers: { Accept: 'application/json', 'User-Agent': 'antigravity-suite-manager' }, timeout: 5000 }, (res) => {
            if (res.statusCode !== 200) {
                res.resume();
                resolve(false);
                return;
            }
            const chunks = [];
            let size = 0;
            res.on('data', (c) => {
                size += c.length;
                if (size > 32 * 1024 * 1024) {
                    req.destroy();
                    resolve(false);
                    return;
                }
                chunks.push(c);
            });
            res.on('end', () => {
                try {
                    const raw = JSON.parse(Buffer.concat(chunks).toString('utf8'));
                    const extracted = extractModelsDevRates(raw);
                    if (Object.keys(extracted).length > 0) {
                        const file = getCacheFile();
                        fs.mkdirSync(path.dirname(file), { recursive: true });
                        const tmp = `${file}.${process.pid}.tmp`;
                        fs.writeFileSync(tmp, JSON.stringify({ source: PRICES_URL, fetchedAt: Math.floor(Date.now() / 1000), models: extracted }, null, 2));
                        fs.renameSync(tmp, file);
                        resolve(true);
                        return;
                    }
                } catch (_) {}
                resolve(false);
            });
        });
        req.on('timeout', () => { req.destroy(); resolve(false); });
        req.on('error', () => resolve(false));
    }).finally(() => { _inFlightRefresh = null; });

    return _inFlightRefresh;
}

function buildCompactTable(priceData = readCachedPrices()) {
    const rows = {};
    for (const [k, row] of Object.entries(priceData.models || {})) {
        if (!row || typeof row.input !== 'number' || typeof row.output !== 'number') continue;
        const cr = typeof row.cache_read === 'number' ? row.cache_read : (typeof row.cacheRead === 'number' ? row.cacheRead : row.input);
        rows[k] = [row.input, row.output, cr];
    }
    return rows;
}

function resolveModelRate(modelName, priceData = readCachedPrices()) {
    const models = priceData.models || FALLBACK_RATES;
    const norm = normalizeModelKey(modelName);
    if (models[norm]) return { ...models[norm], normalized: norm };
    for (const k of Object.keys(models).sort((a, b) => b.length - a.length)) {
        if (norm.startsWith(k) || k.startsWith(norm)) return { ...models[k], normalized: norm };
    }
    if (norm.includes('opus')) return { ...FALLBACK_RATES['claude-opus-4-6'], normalized: norm };
    if (norm.includes('claude') || norm.includes('sonnet')) return { ...FALLBACK_RATES['claude-sonnet-4-6'], normalized: norm };
    if (norm.includes('haiku')) return { ...FALLBACK_RATES['claude-haiku-4-5'], normalized: norm };
    if (norm.includes('flash') || norm.includes('carbon') || norm.includes('argon')) return { ...FALLBACK_RATES['gemini-3.8-flash'], normalized: norm };
    if (norm.includes('gemini') || norm.includes('hydrogen') || norm.includes('neon')) return { ...FALLBACK_RATES['gemini-4-hydrogen'], normalized: norm };
    return { name: modelName || 'Unknown', input: 0, output: 0, cache_read: 0, context_limit: 200000, normalized: norm };
}

module.exports = {
    FALLBACK_RATES,
    getCacheFile,
    normalizeModelKey,
    readCachedPrices,
    triggerBackgroundRefresh,
    buildCompactTable,
    resolveModelRate,
};
