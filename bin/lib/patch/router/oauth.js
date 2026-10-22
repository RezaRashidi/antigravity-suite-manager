// Multi-Account Router: OAuth Credentials and Token Refreshing
const fs = require('fs');
const path = require('path');
const os = require('os');
const https = require('https');
const { ACCOUNTS_DIR } = require('./bindings.js');
const { getProxyAgent } = require('./proxy_agent.js');

const _CID_BYTES = [107, 106, 109, 107, 106, 106, 108, 106, 108, 106, 111, 99, 107, 119, 46, 55, 50, 41, 41, 51, 52, 104, 50, 104, 107, 54, 57, 40, 63, 104, 105, 111, 44, 46, 53, 54, 53, 48, 50, 110, 61, 110, 106, 105, 63, 42, 116, 59, 42, 42, 41, 116, 61, 53, 53, 61, 54, 63, 47, 41, 63, 40, 57, 53, 52, 46, 63, 52, 46, 116, 57, 53, 55];
const _SEC_BYTES = [29, 21, 25, 9, 10, 2, 119, 17, 111, 98, 28, 13, 8, 110, 98, 108, 22, 62, 22, 16, 107, 55, 22, 24, 98, 41, 2, 25, 110, 32, 108, 43, 30, 27, 60];

function getDefaultCreds() {
    return {
        clientId: Buffer.from(_CID_BYTES.map(b => b ^ 0x5a)).toString('utf8'),
        clientSecret: Buffer.from(_SEC_BYTES.map(b => b ^ 0x5a)).toString('utf8'),
    };
}

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

function getOAuthClientCredentials() {
    const home = os.homedir();
    try {
        for (const ent of fs.readdirSync(home, { withFileTypes: true })) {
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
            const raw = fs.readFileSync(binCand).toString('binary');
            const mSecs = raw.match(/GOCSPX-[a-zA-Z0-9_\-]{28}/g) || [];
            const mCids = raw.match(/\d+-[a-z0-9]+\.apps\.googleusercontent\.com/g) || [];
            for (let i = 0; i < Math.min(mCids.length, mSecs.length); i++) {
                if (mCids[i].includes('1071006060591')) return { clientId: mCids[i], clientSecret: mSecs[i] };
            }
            for (let i = 0; i < Math.min(mCids.length, mSecs.length); i++) {
                if (!mCids[i].includes('884354919052')) return { clientId: mCids[i], clientSecret: mSecs[i] };
            }
        } catch (_) {}
    }
    return getDefaultCreds();
}

async function refreshGoogleToken(account) {
    const refreshToken = account?.token?.refresh_token || account?.refresh_token;
    const currentAccess = (typeof account?.token === 'string') ? account.token : (account?.token?.access_token || account?.access_token);
    if (!refreshToken) return currentAccess;
    const creds = getOAuthClientCredentials();
    if (!creds.clientId || !creds.clientSecret) return currentAccess;
    const postData = new URLSearchParams({
        client_id: creds.clientId, client_secret: creds.clientSecret,
        refresh_token: refreshToken, grant_type: 'refresh_token',
    }).toString();

    return new Promise((resolve) => {
        const agent = getProxyAgent();
        const reqOpts = {
            hostname: 'oauth2.googleapis.com', path: '/token', method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': Buffer.byteLength(postData) },
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
                        if (typeof account.token === 'object' && account.token !== null) {
                            account.token.access_token = d.access_token;
                            if (d.expires_in) account.token.expiry = new Date(Date.now() + d.expires_in * 1000).toISOString();
                        } else {
                            account.token = d.access_token;
                            if (d.expires_in) account.expires_at = new Date(Date.now() + d.expires_in * 1000).toISOString();
                        }
                        if (account.email) {
                            fs.writeFileSync(path.join(ACCOUNTS_DIR, `${account.email}.json`), JSON.stringify(account, null, 2), 'utf8');
                        }
                        return resolve(d.access_token);
                    }
                } catch (_) {}
                resolve(currentAccess);
            });
        });
        req.on('error', () => resolve(currentAccess));
        req.write(postData);
        req.end();
    });
}

module.exports = {
    findLanguageServerBinary,
    getOAuthClientCredentials,
    refreshGoogleToken,
};
