// Multi-Account Router: OAuth Credentials and Token Refreshing
const fs = require('fs');
const path = require('path');
const os = require('os');
const https = require('https');
const { ACCOUNTS_DIR } = require('./bindings.js');
const { getProxyAgent } = require('./proxy_agent.js');

// Consumer Antigravity Client ID & Secret
const _CID_BYTES = [107, 106, 109, 107, 106, 106, 108, 106, 108, 106, 111, 99, 107, 119, 46, 55, 50, 41, 41, 51, 52, 104, 50, 104, 107, 54, 57, 40, 63, 104, 105, 111, 44, 46, 53, 54, 53, 48, 50, 110, 61, 110, 106, 105, 63, 42, 116, 59, 42, 42, 41, 116, 61, 53, 53, 61, 54, 63, 47, 41, 63, 40, 57, 53, 52, 46, 63, 52, 46, 116, 57, 53, 55];
const _SEC_BYTES = [29, 21, 25, 9, 10, 2, 119, 17, 111, 98, 28, 13, 8, 110, 98, 108, 22, 62, 22, 16, 107, 55, 22, 24, 98, 41, 2, 25, 110, 32, 108, 43, 30, 27, 60];

function getDefaultCreds() {
    return {
        clientId: Buffer.from(_CID_BYTES.map(b => b ^ 0x5a)).toString('utf8'),
        clientSecret: Buffer.from(_SEC_BYTES.map(b => b ^ 0x5a)).toString('utf8'),
    };
}

const _KNOWN_PAIRS_BYTES = [
    [
        [107, 106, 109, 107, 106, 106, 108, 106, 108, 106, 111, 99, 107, 119, 46, 55, 50, 41, 41, 51, 52, 104, 50, 104, 107, 54, 57, 40, 63, 104, 105, 111, 44, 46, 53, 54, 53, 48, 50, 110, 61, 110, 106, 105, 63, 42, 116, 59, 42, 42, 41, 116, 61, 53, 53, 61, 54, 63, 47, 41, 63, 40, 57, 53, 52, 46, 63, 52, 46, 116, 57, 53, 55],
        [29, 21, 25, 9, 10, 2, 119, 17, 111, 98, 28, 13, 8, 110, 98, 108, 22, 62, 22, 16, 107, 55, 22, 24, 98, 41, 2, 25, 110, 32, 108, 43, 30, 27, 60],
    ],
    [
        [98, 98, 110, 105, 111, 110, 99, 107, 99, 106, 111, 104, 119, 105, 108, 46, 40, 57, 107, 48, 48, 56, 105, 46, 61, 47, 51, 59, 57, 105, 104, 53, 44, 108, 57, 53, 62, 104, 108, 98, 57, 111, 56, 54, 50, 116, 59, 42, 42, 41, 116, 61, 53, 53, 61, 54, 63, 47, 41, 63, 40, 57, 53, 52, 46, 63, 52, 46, 116, 57, 53, 55],
        [29, 21, 25, 9, 10, 2, 119, 48, 109, 8, 52, 110, 42, 44, 42, 45, 19, 99, 119, 56, 49, 119, 16, 106, 56, 61, 31, 35, 109, 106, 10, 13, 110, 119, 111],
    ],
    [
        [107, 106, 99, 98, 99, 99, 107, 107, 109, 111, 109, 104, 111, 119, 55, 62, 47, 107, 53, 63, 111, 57, 56, 56, 63, 107, 57, 49, 61, 61, 41, 63, 56, 53, 56, 50, 99, 110, 46, 53, 51, 59, 42, 108, 111, 109, 116, 59, 42, 42, 41, 116, 61, 53, 53, 61, 54, 63, 47, 41, 63, 40, 57, 53, 52, 46, 63, 52, 46, 116, 57, 53, 55],
        [29, 21, 25, 9, 10, 2, 119, 99, 3, 11, 13, 42, 28, 109, 8, 13, 30, 25, 106, 11, 14, 62, 48, 119, 3, 34, 17, 23, 45, 8, 106, 0, 46, 41, 2],
    ],
];

const KNOWN_CREDENTIAL_PAIRS = _KNOWN_PAIRS_BYTES.map(([c, s]) => ({
    clientId: Buffer.from(c.map(b => b ^ 0x5a)).toString('utf8'),
    clientSecret: Buffer.from(s.map(b => b ^ 0x5a)).toString('utf8'),
}));

function findLanguageServerBinary() {
    if (process.env.ANTIGRAVITY_LS_BINARY && fs.existsSync(process.env.ANTIGRAVITY_LS_BINARY)) {
        return process.env.ANTIGRAVITY_LS_BINARY;
    }
    if (process.resourcesPath) {
        for (const sub of [
            path.join('bin', 'language_server'),
            path.join('app', 'extensions', 'antigravity', 'bin', 'language_server_linux_x64.bin'),
            path.join('app', 'extensions', 'antigravity', 'bin', 'language_server_linux_x64'),
        ]) {
            const cand = path.join(process.resourcesPath, sub);
            if (fs.existsSync(cand)) return cand;
        }
    }
    const bases = ['/opt', path.join(os.homedir(), '.local', 'share'), os.homedir()];
    for (const base of bases) {
        try {
            if (fs.existsSync(base)) {
                for (const sub of fs.readdirSync(base)) {
                    for (const rel of [
                        path.join(base, sub, 'resources', 'bin', 'language_server'),
                        path.join(base, sub, 'resources', 'app', 'extensions', 'antigravity', 'bin', 'language_server_linux_x64.bin'),
                        path.join(base, sub, 'resources', 'app', 'extensions', 'antigravity', 'bin', 'language_server_linux_x64'),
                    ]) {
                        if (fs.existsSync(rel)) return rel;
                    }
                }
            }
        } catch (_) {}
    }
    return null;
}

function getAllOAuthCredentials(preferredClientId = null) {
    const list = [];
    const seen = new Set();
    const addCred = (cid, sec) => {
        if (!cid || !sec || seen.has(cid)) return;
        seen.add(cid);
        list.push({ clientId: cid, clientSecret: sec });
    };

    const home = os.homedir();
    try {
        for (const ent of fs.readdirSync(home, { withFileTypes: true })) {
            if (ent.isDirectory() && ent.name.startsWith('.')) {
                const p = path.join(home, ent.name, 'oauth_credentials.json');
                if (fs.existsSync(p)) {
                    const d = JSON.parse(fs.readFileSync(p, 'utf8'));
                    if (d.client_id && d.client_secret) addCred(d.client_id, d.client_secret);
                }
            }
        }
    } catch (_) {}

    const binCand = findLanguageServerBinary();
    if (binCand && fs.existsSync(binCand)) {
        try {
            const raw = fs.readFileSync(binCand).toString('binary');
            const mSecs = raw.match(/GOCSPX-[a-zA-Z0-9_\-]{28}/g) || [];
            const mCids = raw.match(/\d+-[a-z0-9]+\.apps\.googleusercontent\.com/g) || [];
            for (let i = 0; i < Math.min(mCids.length, mSecs.length); i++) {
                addCred(mCids[i], mSecs[i]);
            }
        } catch (_) {}
    }

    for (const pair of KNOWN_CREDENTIAL_PAIRS) {
        addCred(pair.clientId, pair.clientSecret);
    }
    const def = getDefaultCreds();
    addCred(def.clientId, def.clientSecret);

    if (preferredClientId) {
        list.sort((a, b) => (a.clientId === preferredClientId ? -1 : (b.clientId === preferredClientId ? 1 : 0)));
    } else {
        list.sort((a, b) => {
            const aIsConsumer = a.clientId.includes('1071006060591');
            const bIsConsumer = b.clientId.includes('1071006060591');
            if (aIsConsumer && !bIsConsumer) return -1;
            if (!aIsConsumer && bIsConsumer) return 1;
            const aIsEnt = a.clientId.includes('884354919052');
            const bIsEnt = b.clientId.includes('884354919052');
            if (aIsEnt && !bIsEnt) return 1;
            if (!aIsEnt && bIsEnt) return -1;
            return 0;
        });
    }
    return list;
}

function getOAuthClientCredentials() {
    const all = getAllOAuthCredentials();
    return all[0] || getDefaultCreds();
}

async function requestTokenRefresh(clientId, clientSecret, refreshToken) {
    const postData = new URLSearchParams({
        client_id: clientId,
        client_secret: clientSecret,
        refresh_token: refreshToken,
        grant_type: 'refresh_token',
    }).toString();

    return new Promise((resolve) => {
        const agent = getProxyAgent();
        const reqOpts = {
            hostname: 'oauth2.googleapis.com',
            path: '/token',
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Content-Length': Buffer.byteLength(postData),
            },
            timeout: 7000,
        };
        if (agent) reqOpts.agent = agent;
        const req = https.request(reqOpts, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try {
                    const d = JSON.parse(body);
                    if (d.access_token) {
                        return resolve({ ok: true, data: d });
                    }
                    return resolve({ ok: false, error: d.error || 'no_access_token', status: res.statusCode });
                } catch (e) {
                    return resolve({ ok: false, error: 'json_parse_error', status: res.statusCode });
                }
            });
        });
        req.on('error', err => resolve({ ok: false, error: err.message }));
        req.write(postData);
        req.end();
    });
}

async function refreshGoogleToken(account) {
    const refreshToken = account?.token?.refresh_token || account?.refresh_token;
    const currentAccess = (typeof account?.token === 'string') ? account.token : (account?.token?.access_token || account?.access_token);
    if (!refreshToken) return currentAccess;

    const preferred = account.client_id || (account.token && account.token.client_id) || null;
    const candidates = getAllOAuthCredentials(preferred);

    for (const cred of candidates) {
        const result = await requestTokenRefresh(cred.clientId, cred.clientSecret, refreshToken);
        if (result.ok && result.data?.access_token) {
            const d = result.data;
            account.client_id = cred.clientId;
            if (typeof account.token === 'object' && account.token !== null) {
                account.token.access_token = d.access_token;
                account.token.client_id = cred.clientId;
                if (d.expires_in) account.token.expiry = new Date(Date.now() + d.expires_in * 1000).toISOString();
            } else {
                account.token = d.access_token;
                if (d.expires_in) account.expires_at = new Date(Date.now() + d.expires_in * 1000).toISOString();
            }
            if (account.license_status === 'auth_failed' || account.tier === 'Auth Required') {
                account.license_status = 'ok';
                delete account.license_message;
                delete account.unhealthy_at;
                delete account.unhealthy_until;
                delete account.unhealthy_token_fp;
                if (account.tier === 'Auth Required') account.tier = account.tier_type || 'PRO';
                try { require('./accounts.js')._unhealthyAccounts?.delete(String(account.email || '').toLowerCase()); } catch (_) {}
            }
            if (account.email) {
                try {
                    const fp = path.join(ACCOUNTS_DIR, `${account.email}.json`);
                    const tmp = `${fp}.tmp.${process.pid}.${Date.now()}`;
                    fs.writeFileSync(tmp, JSON.stringify(account, null, 2), 'utf8');
                    fs.renameSync(tmp, fp);
                } catch (_) {}
            }
            if (account.is_primary) {
                try {
                    for (const pFile of [
                        path.join(os.homedir(), '.gemini', 'jetski-standalone-oauth-token'),
                        path.join(os.homedir(), '.gemide', 'jetski-standalone-oauth-token'),
                    ]) {
                        if (fs.existsSync(pFile)) {
                            const cur = JSON.parse(fs.readFileSync(pFile, 'utf8'));
                            if (cur.token && typeof cur.token === 'object') {
                                cur.token.access_token = d.access_token;
                                if (d.expires_in) cur.token.expiry = new Date(Date.now() + d.expires_in * 1000).toISOString();
                            } else {
                                cur.token = d.access_token;
                            }
                            fs.writeFileSync(pFile, JSON.stringify(cur, null, 2), 'utf8');
                        }
                    }
                } catch (_) {}
            }
            return d.access_token;
        }
    }
    return currentAccess;
}

module.exports = {
    findLanguageServerBinary,
    getAllOAuthCredentials,
    getOAuthClientCredentials,
    refreshGoogleToken,
};
