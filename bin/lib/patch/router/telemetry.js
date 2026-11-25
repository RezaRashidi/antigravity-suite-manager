// Multi-Account Router: Telemetry & Live Quota Summaries
const http = require('http'), https = require('https'), fs = require('fs');
const { refreshGoogleToken } = require('./oauth.js');
const { getProxyAgent } = require('./proxy_agent.js');
const { getAuthenticUserAgent } = require('./ua.js');
const { logTraffic } = require('./bindings.js');
const { classifyHttpError, markAccountUnhealthy, clearAccountUnhealthy } = require('./accounts.js');
let _quotaCache = { timestamp: 0, accounts: [] }, _cachedLs = null, _dirCache = {};

function findLanguageServerInfo() {
    if (_cachedLs && (Date.now() - _cachedLs.ts < 300000)) return _cachedLs;
    try {
        let lsPort = null;
        try {
            const ls = require('../languageServer');
            if (typeof ls?.getLsPort === 'function') lsPort = ls.getLsPort();
        } catch (_) {}

        for (const pid of fs.readdirSync('/proc')) {
            if (!/^\d+$/.test(pid)) continue;
            try {
                const cmd = fs.readFileSync('/proc/' + pid + '/cmdline', 'utf8');
                if (cmd.includes('language_server') && cmd.includes('--csrf_token')) {
                    const mCsrf = cmd.match(/--csrf_token\0([0-9a-fA-F-]+)/) || cmd.match(/--csrf_token=([0-9a-fA-F-]+)/);
                    if (!mCsrf) continue;

                    if (lsPort && typeof lsPort === 'number') {
                        _cachedLs = { ports: [lsPort], csrf: mCsrf[1], ts: Date.now() };
                        return _cachedLs;
                    }

                    const mBridge = cmd.match(/--host_bridge_url=https?:\/\/127\.0\.0\.1:(\d+)/);
                    const bridgePort = mBridge ? parseInt(mBridge[1], 10) : null;

                    const net = fs.readFileSync('/proc/' + pid + '/net/tcp', 'utf8'), ports = [];
                    for (const line of net.split('\n')) {
                        const m = line.trim().split(/\s+/);
                        if (m[1] && m[1].startsWith('0100007F:') && m[3] === '0A') {
                            const p = parseInt(m[1].split(':')[1], 16);
                            if (p && p !== bridgePort && p > 1024 && p !== 6379 && p !== 27017 && !ports.includes(p)) {
                                ports.push(p);
                            }
                        }
                    }
                    if (ports.length) { _cachedLs = { ports, csrf: mCsrf[1], ts: Date.now() }; return _cachedLs; }
                }
            } catch (_) {}
        }
    } catch (_) {}
    return _cachedLs;
}

function parseGroupsToBuckets(groups) {
    const buckets = [], seen = new Set();
    for (const g of groups || []) {
        const dn = g.displayName || '';
        const fam = dn.includes('Argon') ? 'argon' : (dn.includes('Gemini') ? 'gemini' : ((dn.includes('Claude') || dn.includes('GPT')) ? 'claude' : 'other'));
        for (const b of g.buckets || []) {
            const win = (b.window || '').toLowerCase().includes('5h') ? '5h' : 'weekly', frac = typeof b.remainingFraction === 'number' ? b.remainingFraction : 1.0;
            const k = `${fam}:${win}`;
            if (seen.has(k)) continue;
            seen.add(k);
            buckets.push({ family: fam, window: win, fraction: frac, percent: Math.round(frac * 100), label: b.displayName || (win === '5h' ? 'Five Hour Limit' : 'Weekly Limit'), reset_time: b.resetTime || '', description: b.description || '' });
        }
    }
    return buckets;
}

async function fetchLanguageServerTelemetry() {
    const ls = findLanguageServerInfo();
    if (!ls?.ports?.length) return null;
    for (const port of ls.ports) {
        for (const client of [http, https]) {
            const res = await new Promise((resolve) => {
                const req = client.request({ hostname: '127.0.0.1', port, method: 'POST', rejectUnauthorized: false, path: '/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary', headers: { 'Content-Type': 'application/json', 'x-codeium-csrf-token': ls.csrf, 'Content-Length': 2 }, timeout: 800 }, (r) => {
                    let d = ''; r.on('data', c => d += c);
                    r.on('end', () => {
                        try {
                            const groups = JSON.parse(d)?.response?.groups || [];
                            resolve(groups.length ? { groups, buckets: parseGroupsToBuckets(groups) } : null);
                        } catch (_) { resolve(null); }
                    });
                });
                req.on('error', () => resolve(null));
                req.write('{}'); req.end();
            });
            if (res) {
                try {
                    const lca = await new Promise((resolveLca) => {
                        const lcaReq = client.request({ hostname: '127.0.0.1', port, method: 'POST', rejectUnauthorized: false, path: '/exa.language_server_pb.LanguageServerService/GetLoadCodeAssist', headers: { 'Content-Type': 'application/json', 'x-codeium-csrf-token': ls.csrf, 'Content-Length': 2 }, timeout: 800 }, (r) => {
                            let d = ''; r.on('data', c => d += c);
                            r.on('end', () => {
                                try { resolveLca(JSON.parse(d)?.response || null); } catch (_) { resolveLca(null); }
                            });
                        });
                        lcaReq.on('error', () => resolveLca(null));
                        lcaReq.write('{}'); lcaReq.end();
                    });
                    if (lca) {
                        const paid = lca.paidTier || lca.g1Tier || lca.currentTier;
                        if (paid?.name) res.plan = paid.name;
                        if (paid?.id) res.tierId = paid.id;
                    }
                } catch (_) {}
                return res;
            }
        }
    }
    return null;
}

function classifyAccountTier(models = {}) {
    const modelIds = Object.keys(models || {}).filter(Boolean);
    const hasFreeNotice = modelIds.some(k => {
        const m = models[k] || {};
        const tt = String(m.tagTitle || '').toLowerCase();
        const td = String(m.tagDescription || '').toLowerCase();
        return k.endsWith('-disabled') ||
            tt === 'paid pro' ||
            td.includes('not included with your current plan') ||
            td.includes('available on paid');
    });
    const enabledIds = modelIds.filter(k => !k.endsWith('-disabled') && !models[k]?.disabled);
    const modelList = enabledIds.map(k => models[k]?.displayName || k).filter(Boolean);
    const hasPaidExclusive = !hasFreeNotice && enabledIds.some(k =>
        k.includes('5-5') || k.includes('gemini-4-neon') || k.includes('gemini-4-carbon')
    );
    const tierType = hasPaidExclusive ? 'Paid Pro' : ((hasFreeNotice || enabledIds.length >= 15) ? 'Free Pro' : 'Free');
    return { tierType, models: modelList, modelIds: enabledIds, modelCount: enabledIds.length };
}

async function fetchAccountModels(token) {
    return new Promise((resolve) => {
        const agent = getProxyAgent();
        const body = JSON.stringify({ project: "aicode-consumers" });
        const reqOpts = {
            hostname: 'daily-cloudcode-pa.googleapis.com',
            port: 443,
            method: 'POST',
            path: '/v1internal:fetchAvailableModels',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'User-Agent': getAuthenticUserAgent(),
                'Content-Length': Buffer.byteLength(body)
            },
            timeout: 5000
        };
        if (agent) reqOpts.agent = agent;
        const req = https.request(reqOpts, (res) => {
            let data = ''; res.on('data', c => data += c);
            res.on('error', () => resolve({ tierType: null, models: [], modelIds: [], modelCount: 0 }));
            res.on('end', () => {
                try {
                    if (res.statusCode === 200) {
                        const parsed = JSON.parse(data);
                        const models = parsed.models || {};
                        try { require('./server.js').updateModelCatalogCache?.(models); } catch (_) {}
                        return resolve(classifyAccountTier(models));
                    }
                } catch (_) {}
                resolve({ tierType: null, models: [], modelIds: [], modelCount: 0 });
            });
        });
        req.on('timeout', () => req.destroy(new Error('timeout')));
        req.on('error', () => resolve({ tierType: null, models: [], modelIds: [], modelCount: 0 }));
        req.write(body); req.end();
    });
}

function warmUpCodeAssist(token) {
    return new Promise((resolve) => {
        const agent = getProxyAgent();
        const reqOpts = {
            hostname: 'daily-cloudcode-pa.googleapis.com',
            port: 443,
            method: 'POST',
            path: '/v1internal:loadCodeAssist',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'User-Agent': getAuthenticUserAgent(),
                'Content-Length': 2
            },
            timeout: 5000
        };
        if (agent) reqOpts.agent = agent;
        const req = https.request(reqOpts, (res) => {
            let d = ''; res.on('data', c => d += c);
            res.on('error', () => resolve(false));
            res.on('end', () => resolve(res.statusCode === 200));
        });
        req.on('timeout', () => req.destroy(new Error('timeout')));
        req.on('error', () => resolve(false));
        req.write('{}'); req.end();
    });
}

async function fetchDirectAccountQuotas(account, force = false) {
    if (!account?.token) return { status: 'no_token', buckets: [] };
    const em = account.email;
    const cached = _dirCache[em];
    const cacheComplete = Boolean(cached && cached.data?.buckets?.length > 0 && cached.data?.tier_type && cached.data?.model_count > 0);
    if (!force && cached && (Date.now() - cached.ts < (cacheComplete ? 60000 : 15000))) return cached.data;
    const token = await refreshGoogleToken(account);
    if (!token) {
        const oauthErr = account._oauthError;
        if (oauthErr === 'invalid_grant' || (!account.refresh_token && !account.token?.refresh_token)) {
            logTraffic(`[QUOTA] [${em}] Auth token resolution failed (${oauthErr || 'missing'})`);
            markAccountUnhealthy(em, 'auth_failed', 'Logged out or token revoked (invalid_grant). Please log in again.', 10 * 60 * 1000, account);
            return { status: 'auth_failed', message: 'Logged out or token revoked (invalid_grant). Please log in again.', buckets: [] };
        }
        return { status: 'refresh_failed', message: `OAuth refresh failed (${oauthErr || 'network error'})`, buckets: [] };
    }
    const modelInfoPromise = fetchAccountModels(token).catch(() => ({ tierType: null, models: [], modelIds: [], modelCount: 0 }));
    return new Promise((resolve) => {
        const agent = getProxyAgent();
        const reqOpts = {
            hostname: 'daily-cloudcode-pa.googleapis.com',
            port: 443,
            method: 'POST',
            path: '/v1internal:retrieveUserQuotaSummary',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'User-Agent': getAuthenticUserAgent(),
                'Content-Length': 2
            },
            timeout: 7000
        };
        if (agent) reqOpts.agent = agent;
        const req = https.request(reqOpts, (res) => {
            let body = ''; res.on('data', c => body += c);
            res.on('error', (err) => {
                logTraffic(`[QUOTA] [${em}] Response Error: ${err.message}`);
                resolve({ status: 'network_error', message: `Refresh failed: ${err.message || 'response error'}`, buckets: [] });
            });
            res.on('end', async () => {
                let data = { status: 'unknown', buckets: [] };
                const mapQuota403Reason = (status, rawText) => {
                    const classified = classifyHttpError(status, rawText);
                    if (classified.reason === 'verify_required' || classified.reason === 'no_license' || classified.reason === 'auth_failed') {
                        return classified;
                    }
                    if (/PERMISSION_DENIED|"error"\s*:/i.test(String(rawText || ''))) {
                        return { reason: 'no_license', message: 'Subscription Required', persist: true };
                    }
                    return classified;
                };
                try {
                    if (res.statusCode === 200) {
                        clearAccountUnhealthy(em);
                        data = { status: 'ok', buckets: parseGroupsToBuckets(JSON.parse(body).groups || []) };
                        logTraffic(`[QUOTA] [${em}] HTTP 200 | Buckets: ${data.buckets.length}`);
                    } else if (res.statusCode === 403) {
                        const preClassified = classifyHttpError(403, body);
                        const needsWarmup = preClassified.reason === 'forbidden_transient';
                        const warmed = needsWarmup ? await warmUpCodeAssist(token) : false;
                        if (warmed) {
                            try {
                                const retryRes = await new Promise((resRetry) => {
                                    const r = https.request(reqOpts, (rs) => {
                                        let b = ''; rs.on('data', c => b += c);
                                        rs.on('error', () => resRetry(null));
                                        rs.on('end', () => resRetry({ statusCode: rs.statusCode, body: b }));
                                    });
                                    if (agent) r.agent = agent;
                                    r.on('timeout', () => r.destroy(new Error('timeout')));
                                    r.on('error', () => resRetry(null));
                                    r.write('{}'); r.end();
                                });
                                if (retryRes && retryRes.statusCode === 200) {
                                    clearAccountUnhealthy(em);
                                    data = { status: 'ok', buckets: parseGroupsToBuckets(JSON.parse(retryRes.body).groups || []) };
                                    logTraffic(`[QUOTA] [${em}] Recovered 403 via loadCodeAssist warmup | Buckets: ${data.buckets.length}`);
                                } else {
                                    const classified = mapQuota403Reason(retryRes?.statusCode || 403, retryRes?.body || body);
                                    markAccountUnhealthy(em, classified.reason, classified.message, undefined, account, { persist: classified.persist, verifyUrl: classified.verifyUrl });
                                    data = { status: classified.reason, message: classified.message, verify_url: classified.verifyUrl || '', buckets: [] };
                                    logTraffic(`[QUOTA] [${em}] HTTP 403 (${classified.reason}) after warmup | Body: ${body.slice(0, 150)}`);
                                }
                            } catch (_) {
                                const classified = mapQuota403Reason(403, body);
                                markAccountUnhealthy(em, classified.reason, classified.message, undefined, account, { persist: classified.persist, verifyUrl: classified.verifyUrl });
                                data = { status: classified.reason, message: classified.message, verify_url: classified.verifyUrl || '', buckets: [] };
                            }
                        } else {
                            const classified = mapQuota403Reason(403, body);
                            markAccountUnhealthy(em, classified.reason, classified.message, undefined, account, { persist: classified.persist, verifyUrl: classified.verifyUrl });
                            data = { status: classified.reason, message: classified.message, verify_url: classified.verifyUrl || '', buckets: [] };
                            logTraffic(`[QUOTA] [${em}] HTTP 403 (${classified.reason}) | Body: ${body.slice(0, 150)}`);
                        }
                    } else if (res.statusCode === 401) {
                        markAccountUnhealthy(em, 'auth_failed', 'Logged out or HTTP 401 Unauthorized. Please log in again.', 10 * 60 * 1000, account);
                        data = { status: 'auth_failed', message: 'Logged out or HTTP 401 Unauthorized. Please log in again.', buckets: [] };
                        logTraffic(`[QUOTA] [${em}] HTTP 401 (Auth Failed) | Body: ${body.slice(0, 150)}`);
                    } else if (res.statusCode === 429) {
                        const prevBuckets = _dirCache[em]?.data?.buckets || [];
                        data = { status: prevBuckets.length ? 'ok' : 'exhausted', message: 'Resource Exhausted (HTTP 429)', buckets: prevBuckets };
                        logTraffic(`[QUOTA] [${em}] HTTP 429 (Rate Limited) | Preserving ${prevBuckets.length} cached buckets`);
                    } else {
                        data = { status: 'refresh_failed', message: `Refresh failed (HTTP ${res.statusCode})`, buckets: [] };
                        logTraffic(`[QUOTA] [${em}] HTTP ${res.statusCode} | Body: ${body.slice(0, 150)}`);
                    }
                } catch (_) {}
                try {
                    const minfo = await modelInfoPromise;
                    data.tier_type = minfo.tierType;
                    data.available_models = minfo.models;
                    data.available_model_ids = minfo.modelIds || [];
                    data.model_count = minfo.modelCount;
                } catch (_) {}
                if (account.is_bypassed) {
                    data.is_bypassed = true;
                }
                if (data.status === 'ok' || !_dirCache[em]?.data?.buckets?.length) {
                    _dirCache[em] = { ts: Date.now(), data };
                }
                resolve(data);
            });
        });
        req.on('timeout', () => req.destroy(new Error('timeout')));
        req.on('error', (err) => {
            logTraffic(`[QUOTA] [${em}] Network Error: ${err.message}`);
            resolve({ status: 'network_error', message: `Refresh failed: ${err.message || 'network error'}`, buckets: [] });
        });
        req.write('{}'); req.end();
    });
}

async function forceRefreshLanguageServerQuota() {
    const ls = findLanguageServerInfo();
    if (!ls?.ports?.length) return false;
    for (const port of ls.ports) {
        for (const client of [http, https]) {
            try {
                await new Promise((resolve) => {
                    const req = client.request({
                        hostname: '127.0.0.1',
                        port,
                        method: 'POST',
                        rejectUnauthorized: false,
                        path: '/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary',
                        headers: {
                            'Content-Type': 'application/json',
                            'Connect-Protocol-Version': '1',
                            'x-codeium-csrf-token': ls.csrf,
                        },
                        timeout: 1200
                    }, (r) => {
                        r.on('data', () => {});
                        r.on('end', resolve);
                    });
                    req.on('error', resolve);
                    req.write(JSON.stringify({ forceRefresh: true }));
                    req.end();
                });
            } catch (_) {}
        }
    }
    return true;
}

module.exports = { _quotaCache, classifyAccountTier, fetchAccountModels, parseGroupsToBuckets, fetchLanguageServerTelemetry, fetchDirectAccountQuotas, forceRefreshLanguageServerQuota, findLanguageServerInfo };
