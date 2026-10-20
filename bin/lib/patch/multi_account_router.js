// ==============================================================================
// Antigravity Multi-Account Loopback Router & Real-Time Telemetry Provider
// ==============================================================================

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

const DEFAULT_PORT = 41999;
const UPSTREAM_HOST = 'daily-cloudcode-pa.googleapis.com';
const ACCOUNTS_DIR = process.env.ANTIGRAVITY_ACCOUNTS_DIR || path.join(os.homedir(), '.config', 'antigravity', 'accounts');
const BINDINGS_FILE = path.join(ACCOUNTS_DIR, 'bindings.json');
const TRAFFIC_LOG = path.join(ACCOUNTS_DIR, 'traffic.log');

let _server = null;
let _quotaCache = { timestamp: 0, accounts: [] };

function ensureAccountsDir() {
    try {
        if (!fs.existsSync(ACCOUNTS_DIR)) fs.mkdirSync(ACCOUNTS_DIR, { recursive: true });
    } catch (_) {}
}

function logTraffic(message) {
    try {
        ensureAccountsDir();
        const line = `[${new Date().toISOString()}] ${message}\n`;
        fs.appendFileSync(TRAFFIC_LOG, line, 'utf8');
    } catch (_) {}
}

function getBindings() {
    try {
        if (fs.existsSync(BINDINGS_FILE)) {
            return JSON.parse(fs.readFileSync(BINDINGS_FILE, 'utf8'));
        }
    } catch (_) {}
    return {};
}

let _activeAccountEmail = null;

function setActiveAccount(email) {
    if (!email) return;
    _activeAccountEmail = email;
    ensureAccountsDir();
    const b = getBindings();
    b.__active_account = email;
    try {
        const tmp = BINDINGS_FILE + '.tmp';
        fs.writeFileSync(tmp, JSON.stringify(b, null, 2), 'utf8');
        fs.renameSync(tmp, BINDINGS_FILE);
        logTraffic(`[ACTIVE] Active account set to: ${email}`);
    } catch (_) {}
}

function getActiveAccountEmail() {
    if (_activeAccountEmail) return _activeAccountEmail;
    const b = getBindings();
    if (b.__active_account) {
        _activeAccountEmail = b.__active_account;
        return _activeAccountEmail;
    }
    const accounts = Object.keys(loadAllAccounts());
    return accounts[0] || null;
}

function setBinding(cascadeId, email, model = '') {
    ensureAccountsDir();
    const b = getBindings();
    b[cascadeId] = { cascade_id: cascadeId, email, model, updated_at: new Date().toISOString() };
    b.__active_account = email;
    _activeAccountEmail = email;
    try {
        const tmp = BINDINGS_FILE + '.tmp';
        fs.writeFileSync(tmp, JSON.stringify(b, null, 2), 'utf8');
        fs.renameSync(tmp, BINDINGS_FILE);
        logTraffic(`[BIND] Chat: ${cascadeId} bound to account: ${email}`);
    } catch (e) {
        console.error('[MultiAccountRouter] Failed to write bindings:', e.message);
    }
}

function findPrimaryTokenFiles() {
    const home = os.homedir();
    const files = [];
    try {
        const entries = fs.readdirSync(home, { withFileTypes: true });
        for (const ent of entries) {
            if (ent.isDirectory() && ent.name.startsWith('.')) {
                const p = path.join(home, ent.name, 'jetski-standalone-oauth-token');
                if (fs.existsSync(p)) files.push(p);
            }
        }
    } catch (_) {}
    return files;
}

function loadAllAccounts() {
    ensureAccountsDir();
    const accounts = {};
    try {
        const files = fs.readdirSync(ACCOUNTS_DIR);
        for (const f of files) {
            if (f.endsWith('.json') && f !== 'bindings.json' && f !== 'oauth_credentials.json') {
                try {
                    const data = JSON.parse(fs.readFileSync(path.join(ACCOUNTS_DIR, f), 'utf8'));
                    if (data && data.email) accounts[data.email] = data;
                } catch (_) {}
            }
        }
    } catch (_) {}

    for (const tokenFile of findPrimaryTokenFiles()) {
        try {
            const data = JSON.parse(fs.readFileSync(tokenFile, 'utf8'));
            let email = data.email;
            if (!email && data.id_token) {
                const parts = data.id_token.split('.');
                if (parts[1]) {
                    const claims = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf8'));
                    email = claims.email;
                }
            }
            if (email) {
                data.email = email;
                data.is_primary = true;
                if (!accounts[email]) accounts[email] = data;
                else accounts[email].is_primary = true;
            }
        } catch (_) {}
    }
    return accounts;
}

function findLanguageServerInfo() {
    try {
        const pgrep = execSync('pgrep -a language_server', { encoding: 'utf8' });
        const mPid = pgrep.match(/^(\d+)/m);
        const mCsrf = pgrep.match(/--csrf_token(?:=|\s+)([0-9a-fA-F-]+)/);
        if (!mPid || !mCsrf) return null;
        const pid = mPid[1];
        const csrf = mCsrf[1];
        const ss = execSync('ss -tlpn', { encoding: 'utf8' });
        const lines = ss.split('\n').filter(l => l.includes('pid=' + pid));
        for (const l of lines) {
            const mPort = l.match(/127\.0\.0\.1:(\d+)/);
            if (mPort) return { port: parseInt(mPort[1], 10), csrf };
        }
    } catch (_) {}
    return null;
}

function parseGroupsToBuckets(groups) {
    const buckets = [];
    for (const g of groups || []) {
        const isGemini = (g.displayName || '').includes('Gemini');
        const isClaude = (g.displayName || '').includes('Claude') || (g.displayName || '').includes('GPT');
        const family = isGemini ? 'gemini' : (isClaude ? 'claude' : 'other');
        for (const b of g.buckets || []) {
            const win = (b.window || '').toLowerCase();
            const tagWin = win.includes('5h') ? '5h' : 'weekly';
            const frac = typeof b.remainingFraction === 'number' ? b.remainingFraction : 1.0;
            buckets.push({
                family,
                window: tagWin,
                label: b.displayName || (tagWin === '5h' ? 'Five Hour Limit' : 'Weekly Limit'),
                fraction: frac,
                percent: Math.round(frac * 100),
                reset_time: b.resetTime || '',
                description: b.description || '',
            });
        }
    }
    return buckets;
}

async function fetchLanguageServerTelemetry() {
    const ls = findLanguageServerInfo();
    if (!ls) return null;

    return new Promise((resolve) => {
        const req = https.request({
            hostname: '127.0.0.1',
            port: ls.port,
            path: '/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary',
            method: 'POST',
            rejectUnauthorized: false,
            headers: {
                'Content-Type': 'application/json',
                'x-codeium-csrf-token': ls.csrf,
                'Content-Length': 2,
            },
            timeout: 2500,
        }, (res) => {
            let body = '';
            res.on('data', c => body += c);
            res.on('end', () => {
                try {
                    const d = JSON.parse(body);
                    const groups = d?.response?.groups || [];
                    resolve({ groups, buckets: parseGroupsToBuckets(groups) });
                } catch (_) { resolve(null); }
            });
        });
        req.on('error', () => resolve(null));
        req.write('{}');
        req.end();
    });
}

function findLanguageServerBinary() {
    if (process.env.ANTIGRAVITY_LS_BINARY && fs.existsSync(process.env.ANTIGRAVITY_LS_BINARY)) {
        return process.env.ANTIGRAVITY_LS_BINARY;
    }
    if (process.resourcesPath) {
        const cand = path.join(process.resourcesPath, 'bin', 'language_server');
        if (fs.existsSync(cand)) return cand;
    }
    const searchDirs = ['/opt', os.homedir()];
    for (const base of searchDirs) {
        try {
            if (fs.existsSync(base)) {
                for (const sub of fs.readdirSync(base)) {
                    const cand = path.join(base, sub, 'resources', 'bin', 'language_server');
                    if (fs.existsSync(cand)) return cand;
                }
            }
        } catch (_) {}
    }
    return null;
}

function getOAuthClientCredentials() {
    const home = os.homedir();
    try {
        const entries = fs.readdirSync(home, { withFileTypes: true });
        for (const ent of entries) {
            if (ent.isDirectory() && ent.name.startsWith('.')) {
                const p = path.join(home, ent.name, 'oauth_credentials.json');
                if (fs.existsSync(p)) {
                    const d = JSON.parse(fs.readFileSync(p, 'utf8'));
                    if (d.client_id && d.client_secret) return { clientId: d.client_id, clientSecret: d.client_secret };
                }
            }
        }
    } catch (_) {}

    const binCand = findLanguageServerBinary();
    if (binCand && fs.existsSync(binCand)) {
        try {
            const raw = fs.readFileSync(binCand);
            const mSec = raw.toString('binary').match(/GOCSPX-[a-zA-Z0-9_\-]+/);
            const mCid = raw.toString('binary').match(/\d+-[a-z0-9]+\.apps\.googleusercontent\.com/);
            if (mSec && mCid) return { clientId: mCid[0], clientSecret: mSec[0] };
        } catch (_) {}
    }
    return { clientId: '', clientSecret: '' };
}

async function refreshGoogleToken(account) {
    if (!account || !account.token || !account.token.refresh_token) return account?.token?.access_token;
    const creds = getOAuthClientCredentials();
    if (!creds.clientId || !creds.clientSecret) return account?.token?.access_token;
    const postData = new URLSearchParams({
        client_id: creds.clientId,
        client_secret: creds.clientSecret,
        refresh_token: account.token.refresh_token,
        grant_type: 'refresh_token',
    }).toString();

    return new Promise((resolve) => {
        const req = https.request({
            hostname: 'oauth2.googleapis.com',
            path: '/token',
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Content-Length': Buffer.byteLength(postData),
            },
            timeout: 5000,
        }, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try {
                    const d = JSON.parse(body);
                    if (d.access_token) {
                        account.token.access_token = d.access_token;
                        if (d.expires_in) {
                            account.token.expiry = new Date(Date.now() + d.expires_in * 1000).toISOString();
                        }
                        if (account.email) {
                            const p = path.join(ACCOUNTS_DIR, `${account.email}.json`);
                            fs.writeFileSync(p, JSON.stringify(account, null, 2), 'utf8');
                        }
                        resolve(d.access_token);
                        return;
                    }
                } catch (_) {}
                resolve(account.token.access_token);
            });
        });
        req.on('error', () => resolve(account.token.access_token));
        req.write(postData);
        req.end();
    });
}

async function fetchDirectAccountQuotas(account) {
    if (!account || !account.token) return { status: 'no_token', buckets: [] };
    const token = await refreshGoogleToken(account);
    if (!token) return { status: 'auth_failed', buckets: [] };

    return new Promise((resolve) => {
        const req = https.request({
            hostname: 'cloudcode-pa.googleapis.com',
            port: 443,
            path: '/v1internal:retrieveUserQuotaSummary',
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'Content-Length': 2,
            },
            timeout: 4000,
        }, (res) => {
            let body = '';
            res.on('data', c => body += c);
            res.on('end', () => {
                try {
                    if (res.statusCode === 200) {
                        const d = JSON.parse(body);
                        return resolve({ status: 'ok', buckets: parseGroupsToBuckets(d.groups || []) });
                    }
                    if (res.statusCode === 403) {
                        return resolve({ status: 'no_license', message: 'Subscription Required', buckets: [] });
                    }
                    if (res.statusCode === 429) {
                        return resolve({ status: 'exhausted', message: 'Resource Exhausted', buckets: [] });
                    }
                } catch (_) {}
                resolve({ status: 'unknown', code: res.statusCode, buckets: [] });
            });
        });
        req.on('error', () => resolve({ status: 'network_error', buckets: [] }));
        req.write('{}');
        req.end();
    });
}

async function loadAllAccountsWithQuotas() {
    const now = Date.now();
    if (_quotaCache.accounts.length > 0 && (now - _quotaCache.timestamp < 30000)) {
        return _quotaCache.accounts;
    }

    const accountsMap = loadAllAccounts();
    const accountsList = Object.values(accountsMap);

    // 1. Fetch live quotas from active Language Server
    const lsTelemetry = await fetchLanguageServerTelemetry();

    // 2. Populate quotas for each account
    for (const acc of accountsList) {
        if (acc.is_primary && lsTelemetry && lsTelemetry.buckets && lsTelemetry.buckets.length > 0) {
            acc.quotas = lsTelemetry.buckets;
            acc.license_status = 'ok';
            acc.tier = acc.tier || 'TEAMS_TIER_PRO';
        } else {
            const direct = await fetchDirectAccountQuotas(acc);
            acc.license_status = direct.status;
            acc.license_message = direct.message || '';
            acc.quotas = direct.buckets || [];
            if (direct.status === 'no_license') {
                acc.tier = 'No License (Subscription Required)';
            } else if (direct.status === 'exhausted') {
                acc.tier = 'Resource Exhausted';
            }
        }
    }

    _quotaCache = { timestamp: now, accounts: accountsList };
    return accountsList;
}

async function resolveTokenForAccount(email) {
    if (!email) return null;
    const accounts = loadAllAccounts();
    const target = accounts[email];
    if (!target) return null;
    if (target.is_primary) {
        return null; // Primary account uses its own native token
    }
    if (!target.token) return null;

    let expiryMs = target.token.expiry ? new Date(target.token.expiry).getTime() : 0;
    if (!expiryMs || expiryMs - Date.now() < 300000) {
        return await refreshGoogleToken(target);
    }
    return target.token.access_token || null;
}

async function resolveTokenForCascade(cascadeId) {
    let email = null;
    if (cascadeId) {
        const bindings = getBindings();
        if (bindings[cascadeId] && bindings[cascadeId].email) {
            email = bindings[cascadeId].email;
        }
    }
    if (!email) {
        email = getActiveAccountEmail();
    }
    return await resolveTokenForAccount(email);
}

function startMultiAccountRouter(port = DEFAULT_PORT) {
    if (_server) return _server;

    _server = http.createServer((req, res) => {
        if (req.url === '/healthz') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ status: 'ok', proxy: 'antigravity-multi-account-node' }));
            return;
        }

        const chunks = [];
        req.on('data', chunk => chunks.push(chunk));
        req.on('end', async () => {
            const body = Buffer.concat(chunks);
            let cascadeId = null;
            try {
                const parsed = JSON.parse(body.toString('utf8'));
                cascadeId = parsed.cascadeId || parsed.conversationId || parsed.trajectoryId;
            } catch (_) {
                const match = body.toString('utf8').match(/"(?:cascadeId|conversationId)":\s*"([a-zA-Z0-9_\-]+)"/);
                if (match) cascadeId = match[1];
            }

            const bindings = getBindings();
            const boundEmail = (cascadeId && bindings[cascadeId] && bindings[cascadeId].email) || getActiveAccountEmail() || 'Primary (Native)';
            const token = await resolveTokenForCascade(cascadeId);
            const tokenFingerprint = token ? `token: ...${token.slice(-6)}` : 'token: [Native LS Session]';
            logTraffic(`Chat: [${cascadeId || 'general'}] -> Account: [${boundEmail}] | ${tokenFingerprint} | Path: ${req.url}`);

            const headers = { ...req.headers };
            headers.host = UPSTREAM_HOST;

            // Only override Authorization if explicitly bound to a secondary account
            if (token) {
                headers.authorization = `Bearer ${token}`;
            }

            // Explicit Content-Length to avoid chunked rejection
            if (body.length > 0) {
                headers['content-length'] = Buffer.byteLength(body);
            }
            delete headers['transfer-encoding'];
            delete headers['connection'];

            const upReq = https.request({
                hostname: UPSTREAM_HOST,
                port: 443,
                path: req.url,
                method: req.method,
                headers: headers,
                timeout: 0,
            }, (upRes) => {
                logTraffic(`Chat: [${cascadeId || 'general'}] <- Upstream Response: ${upRes.statusCode}`);
                res.writeHead(upRes.statusCode, upRes.headers);
                upRes.pipe(res);
            });

            req.on('aborted', () => upReq.destroy());

            upReq.on('error', (err) => {
                logTraffic(`Chat: [${cascadeId || 'general'}] !! Upstream Error: ${err.message}`);
                console.error('[MultiAccountRouter] Upstream error:', err.message);
                if (!res.headersSent) {
                    res.writeHead(502, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: err.message }));
                }
            });

            if (body.length > 0) upReq.write(body);
            upReq.end();
        });
    });

    _server.on('error', (err) => {
        if (err.code === 'EADDRINUSE') {
            console.log(`[MultiAccountRouter] Port ${port} in use (external/existing daemon).`);
        } else {
            console.error('[MultiAccountRouter] Server error:', err.message);
        }
    });

    _server.listen(port, '127.0.0.1', () => {
        console.log(`[MultiAccountRouter] Loopback proxy active on http://127.0.0.1:${port}`);
        logTraffic(`MultiAccountRouter started on port ${port}`);
    });

    return _server;
}

module.exports = {
    startMultiAccountRouter,
    loadAllAccounts,
    loadAllAccountsWithQuotas,
    getBindings,
    setBinding,
    setActiveAccount,
    getActiveAccountEmail,
};

