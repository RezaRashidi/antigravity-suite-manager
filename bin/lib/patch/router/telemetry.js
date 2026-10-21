// Multi-Account Router: Telemetry & Live Quota Summaries
const http = require('http'), https = require('https'), fs = require('fs');
const { refreshGoogleToken } = require('./oauth.js');
const { getProxyAgent } = require('./proxy_agent.js');
const { logTraffic } = require('./bindings.js');
let _quotaCache = { timestamp: 0, accounts: [] }, _cachedLs = null, _dirCache = {};

function findLanguageServerInfo() {
    if (_cachedLs && (Date.now() - _cachedLs.ts < 300000)) return _cachedLs;
    try {
        for (const pid of fs.readdirSync('/proc')) {
            if (!/^\d+$/.test(pid)) continue;
            try {
                const cmd = fs.readFileSync('/proc/' + pid + '/cmdline', 'utf8');
                if (cmd.includes('language_server') && cmd.includes('--csrf_token')) {
                    const mCsrf = cmd.match(/--csrf_token\0([0-9a-fA-F-]+)/) || cmd.match(/--csrf_token=([0-9a-fA-F-]+)/);
                    if (!mCsrf) continue;
                    const net = fs.readFileSync('/proc/' + pid + '/net/tcp', 'utf8'), ports = [];
                    for (const line of net.split('\n')) {
                        const m = line.trim().split(/\s+/);
                        if (m[1] && m[1].startsWith('0100007F:')) {
                            const p = parseInt(m[1].split(':')[1], 16);
                            if (p && !ports.includes(p)) ports.push(p);
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
        const fam = (g.displayName || '').includes('Gemini') ? 'gemini' : (((g.displayName || '').includes('Claude') || (g.displayName || '').includes('GPT')) ? 'claude' : 'other');
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
            if (res) return res;
        }
    }
    return null;
}

async function fetchDirectAccountQuotas(account) {
    if (!account?.token) return { status: 'no_token', buckets: [] };
    const em = account.email;
    if (_dirCache[em] && (Date.now() - _dirCache[em].ts < 60000)) return _dirCache[em].data;
    const token = await refreshGoogleToken(account);
    if (!token) {
        logTraffic(`[QUOTA] [${em}] Auth token resolution failed`);
        return { status: 'auth_failed', buckets: [] };
    }
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
                'User-Agent': 'Antigravity/2.23.1',
                'Content-Length': 2
            },
            timeout: 7000
        };
        if (agent) reqOpts.agent = agent;
        const req = https.request(reqOpts, (res) => {
            let body = ''; res.on('data', c => body += c);
            res.on('end', () => {
                let data = { status: 'unknown', buckets: [] };
                try {
                    if (res.statusCode === 200) {
                        data = { status: 'ok', buckets: parseGroupsToBuckets(JSON.parse(body).groups || []) };
                        logTraffic(`[QUOTA] [${em}] HTTP 200 | Buckets: ${data.buckets.length}`);
                    } else if (res.statusCode === 403) {
                        data = { status: 'no_license', message: 'Subscription Required', buckets: [] };
                        logTraffic(`[QUOTA] [${em}] HTTP 403 (No License) | Body: ${body.slice(0, 150)}`);
                    } else if (res.statusCode === 429) {
                        const prevBuckets = _dirCache[em]?.data?.buckets || [];
                        data = { status: prevBuckets.length ? 'ok' : 'exhausted', message: 'Resource Exhausted', buckets: prevBuckets };
                        logTraffic(`[QUOTA] [${em}] HTTP 429 (Rate Limited) | Preserving ${prevBuckets.length} cached buckets`);
                    } else {
                        logTraffic(`[QUOTA] [${em}] HTTP ${res.statusCode} | Body: ${body.slice(0, 150)}`);
                    }
                } catch (_) {}
                if (data.status === 'ok' || !_dirCache[em]?.data?.buckets?.length) {
                    _dirCache[em] = { ts: Date.now(), data };
                }
                resolve(data);
            });
        });
        req.on('error', (err) => {
            logTraffic(`[QUOTA] [${em}] Network Error: ${err.message}`);
            resolve({ status: 'network_error', buckets: [] });
        });
        req.write('{}'); req.end();
    });
}

module.exports = { _quotaCache, parseGroupsToBuckets, fetchLanguageServerTelemetry, fetchDirectAccountQuotas };
