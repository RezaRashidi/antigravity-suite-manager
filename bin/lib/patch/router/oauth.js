// Multi-Account Router: OAuth Credentials and Token Refreshing
const fs = require('fs');
const path = require('path');
const os = require('os');
const https = require('https');
const { ACCOUNTS_DIR } = require('./bindings');

function findLanguageServerBinary() {
    if (process.env.ANTIGRAVITY_LS_BINARY && fs.existsSync(process.env.ANTIGRAVITY_LS_BINARY)) {
        return process.env.ANTIGRAVITY_LS_BINARY;
    }
    if (process.resourcesPath) {
        const cand = path.join(process.resourcesPath, 'bin', 'language_server');
        if (fs.existsSync(cand)) return cand;
    }
    for (const base of ['/opt', os.homedir()]) {
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
            const mSec = raw.match(/GOCSPX-[a-zA-Z0-9_\-]+/);
            const mCid = raw.match(/\d+-[a-z0-9]+\.apps\.googleusercontent\.com/);
            if (mSec && mCid) return { clientId: mCid[0], clientSecret: mSec[0] };
        } catch (_) {}
    }
    return { clientId: '', clientSecret: '' };
}

async function refreshGoogleToken(account) {
    if (!account?.token?.refresh_token) return account?.token?.access_token;
    const creds = getOAuthClientCredentials();
    if (!creds.clientId || !creds.clientSecret) return account?.token?.access_token;
    const postData = new URLSearchParams({
        client_id: creds.clientId, client_secret: creds.clientSecret,
        refresh_token: account.token.refresh_token, grant_type: 'refresh_token',
    }).toString();

    return new Promise((resolve) => {
        const req = https.request({
            hostname: 'oauth2.googleapis.com', path: '/token', method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': Buffer.byteLength(postData) },
            timeout: 5000,
        }, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try {
                    const d = JSON.parse(body);
                    if (d.access_token) {
                        account.token.access_token = d.access_token;
                        if (d.expires_in) account.token.expiry = new Date(Date.now() + d.expires_in * 1000).toISOString();
                        if (account.email) {
                            fs.writeFileSync(path.join(ACCOUNTS_DIR, `${account.email}.json`), JSON.stringify(account, null, 2), 'utf8');
                        }
                        return resolve(d.access_token);
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

module.exports = {
    findLanguageServerBinary,
    getOAuthClientCredentials,
    refreshGoogleToken,
};
