// Multi-Account Router: Telemetry & Live Quota Summaries
const http = require('http'), https = require('https');
const { execSync } = require('child_process'), { refreshGoogleToken } = require('./oauth');
let _quotaCache = { timestamp: 0, accounts: [] };

function findLanguageServerInfo() {
    try {
        const pgrep = execSync('pgrep -a language_server', { encoding: 'utf8' });
        const mPid = pgrep.match(/^(\d+)/m), mCsrf = pgrep.match(/--csrf_token(?:=|\s+)([0-9a-fA-F-]+)/);
        if (!mPid || !mCsrf) return null;
        const ss = execSync('ss -tlpn', { encoding: 'utf8' }), ports = [];
        for (const l of ss.split('\n').filter(l => l.includes('pid=' + mPid[1]))) {
            const m = l.match(/127\.0\.0\.1:(\d+)/);
            if (m && !ports.includes(parseInt(m[1], 10))) ports.push(parseInt(m[1], 10));
        }
        return { ports, csrf: mCsrf[1] };
    } catch (_) { return null; }
}

function parseGroupsToBuckets(groups) {
    const buckets = [];
    for (const g of groups || []) {
        const fam = (g.displayName || '').includes('Gemini') ? 'gemini' :
            (((g.displayName || '').includes('Claude') || (g.displayName || '').includes('GPT')) ? 'claude' : 'other');
        for (const b of g.buckets || []) {
            const win = (b.window || '').toLowerCase().includes('5h') ? '5h' : 'weekly';
            const frac = typeof b.remainingFraction === 'number' ? b.remainingFraction : 1.0;
            buckets.push({
                family: fam, window: win, fraction: frac, percent: Math.round(frac * 100),
                label: b.displayName || (win === '5h' ? 'Five Hour Limit' : 'Weekly Limit'),
                reset_time: b.resetTime || '', description: b.description || '',
            });
        }
    }
    return buckets;
}

async function fetchLanguageServerTelemetry() {
    const ls = findLanguageServerInfo();
    if (!ls || !ls.ports?.length) return null;
    for (const port of ls.ports) {
        for (const client of [http, https]) {
            const res = await new Promise((resolve) => {
                const req = client.request({
                    hostname: '127.0.0.1', port, method: 'POST', rejectUnauthorized: false,
                    path: '/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary',
                    headers: { 'Content-Type': 'application/json', 'x-codeium-csrf-token': ls.csrf, 'Content-Length': 2 },
                    timeout: 800,
                }, (r) => {
                    let d = ''; r.on('data', c => d += c);
                    r.on('end', () => {
                        try {
                            const groups = JSON.parse(d)?.response?.groups || [];
                            resolve(groups.length > 0 ? { groups, buckets: parseGroupsToBuckets(groups) } : null);
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
    const token = await refreshGoogleToken(account);
    if (!token) return { status: 'auth_failed', buckets: [] };
    return new Promise((resolve) => {
        const req = https.request({
            hostname: 'daily-cloudcode-pa.googleapis.com', port: 443, method: 'POST',
            path: '/v1internal:retrieveUserQuotaSummary',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json', 'Content-Length': 2 },
            timeout: 4000,
        }, (res) => {
            let body = ''; res.on('data', c => body += c);
            res.on('end', () => {
                try {
                    if (res.statusCode === 200) return resolve({ status: 'ok', buckets: parseGroupsToBuckets(JSON.parse(body).groups || []) });
                    if (res.statusCode === 403) return resolve({ status: 'no_license', message: 'Subscription Required', buckets: [] });
                    if (res.statusCode === 429) return resolve({ status: 'exhausted', message: 'Resource Exhausted', buckets: [] });
                } catch (_) {}
                resolve({ status: 'unknown', code: res.statusCode, buckets: [] });
            });
        });
        req.on('error', () => resolve({ status: 'network_error', buckets: [] }));
        req.write('{}'); req.end();
    });
}

module.exports = { _quotaCache, parseGroupsToBuckets, fetchLanguageServerTelemetry, fetchDirectAccountQuotas };
