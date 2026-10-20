// ==============================================================================
// Antigravity Multi-Account Loopback Router & Reverse Proxy
// ==============================================================================

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { URL } = require('url');

const DEFAULT_PORT = 41999;
const UPSTREAM_HOST = 'daily-cloudcode-pa.googleapis.com';
const ACCOUNTS_DIR = process.env.ANTIGRAVITY_ACCOUNTS_DIR || path.join(os.homedir(), '.config', 'antigravity', 'accounts');
const BINDINGS_FILE = path.join(ACCOUNTS_DIR, 'bindings.json');

let _server = null;

function ensureAccountsDir() {
    try {
        if (!fs.existsSync(ACCOUNTS_DIR)) fs.mkdirSync(ACCOUNTS_DIR, { recursive: true });
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

function setBinding(cascadeId, email, model = '') {
    ensureAccountsDir();
    const b = getBindings();
    b[cascadeId] = { cascade_id: cascadeId, email, model, updated_at: new Date().toISOString() };
    try {
        const tmp = BINDINGS_FILE + '.tmp';
        fs.writeFileSync(tmp, JSON.stringify(b, null, 2), 'utf8');
        fs.renameSync(tmp, BINDINGS_FILE);
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

async function resolveTokenForCascade(cascadeId) {
    const accounts = loadAllAccounts();
    const bindings = getBindings();
    let email = null;
    if (cascadeId && bindings[cascadeId]) {
        email = bindings[cascadeId].email;
    }
    let target = email && accounts[email] ? accounts[email] : null;
    if (!target) {
        target = Object.values(accounts).find(a => a.is_primary) || Object.values(accounts)[0];
    }
    if (!target || !target.token) return null;

    let expiryMs = target.token.expiry ? new Date(target.token.expiry).getTime() : 0;
    if (!expiryMs || expiryMs - Date.now() < 300000) {
        return await refreshGoogleToken(target);
    }
    return target.token.access_token;
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

            const token = await resolveTokenForCascade(cascadeId);
            const headers = { ...req.headers };
            headers.host = UPSTREAM_HOST;
            if (token) {
                headers.authorization = `Bearer ${token}`;
            }
            delete headers['content-length'];

            const upReq = https.request({
                hostname: UPSTREAM_HOST,
                port: 443,
                path: req.url,
                method: req.method,
                headers: headers,
            }, (upRes) => {
                res.writeHead(upRes.statusCode, upRes.headers);
                upRes.pipe(res);
            });

            upReq.on('error', (err) => {
                console.error('[MultiAccountRouter] Upstream error:', err.message);
                res.writeHead(502, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message }));
            });

            if (body.length > 0) upReq.write(body);
            upReq.end();
        });
    });

    _server.on('error', (err) => {
        if (err.code === 'EADDRINUSE') {
            console.log(`[MultiAccountRouter] Port ${port} in use (daemon running).`);
        } else {
            console.error('[MultiAccountRouter] Server error:', err.message);
        }
    });

    _server.listen(port, '127.0.0.1', () => {
        console.log(`[MultiAccountRouter] Loopback proxy active on http://127.0.0.1:${port}`);
    });

    return _server;
}

module.exports = {
    startMultiAccountRouter,
    loadAllAccounts,
    getBindings,
    setBinding,
};
