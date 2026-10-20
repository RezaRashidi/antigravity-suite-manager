// Multi-Account Router: Account Discovery and Primary Credentials
const fs = require('fs');
const path = require('path');
const os = require('os');
const { ACCOUNTS_DIR, ensureAccountsDir } = require('./bindings');

function findPrimaryTokenFiles() {
    const home = os.homedir();
    const files = [];
    const direct = [
        path.join(home, '.gemini', 'jetski-standalone-oauth-token'),
        path.join(home, '.gemide', 'jetski-standalone-oauth-token'),
        path.join(home, '.config', 'antigravity', 'jetski-standalone-oauth-token'),
        path.join(home, '.config', 'Antigravity', 'jetski-standalone-oauth-token'),
    ];
    for (const p of direct) {
        if (fs.existsSync(p) && !files.includes(p)) files.push(p);
    }
    try {
        const entries = fs.readdirSync(home, { withFileTypes: true });
        for (const ent of entries) {
            if (ent.isDirectory() && ent.name.startsWith('.')) {
                for (const sub of ['jetski-standalone-oauth-token', path.join('.gemini', 'jetski-standalone-oauth-token')]) {
                    const p = path.join(home, ent.name, sub);
                    if (fs.existsSync(p) && !files.includes(p)) files.push(p);
                }
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

module.exports = {
    findPrimaryTokenFiles,
    loadAllAccounts,
};
