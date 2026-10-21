// Multi-Account Router: Account Discovery and Primary Credentials
const fs = require('fs');
const path = require('path');
const os = require('os');
const { ACCOUNTS_DIR, ensureAccountsDir } = require('./bindings');

function findPrimaryTokenFiles() {
    const homes = [os.homedir()];
    if (process.env.REAL_HOME && process.env.REAL_HOME !== os.homedir()) homes.push(process.env.REAL_HOME);
    const files = [];
    for (const home of homes) {
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
    }
    return files;
}

function loadAllAccounts() {
    ensureAccountsDir();
    const accounts = {}, primary = path.join(os.homedir(), '.gemini', 'jetski-standalone-oauth-token');
    try {
        for (const f of fs.readdirSync(ACCOUNTS_DIR)) {
            if (f.endsWith('.json') && f !== 'bindings.json' && f !== 'oauth_credentials.json') {
                try {
                    const d = JSON.parse(fs.readFileSync(path.join(ACCOUNTS_DIR, f), 'utf8'));
                    if (d && d.email) { d.is_primary = false; accounts[d.email.toLowerCase()] = d; }
                } catch (_) {}
            }
        }
    } catch (_) {}
    for (const f of findPrimaryTokenFiles()) {
        try {
            const d = JSON.parse(fs.readFileSync(f, 'utf8'));
            let em = d.email;
            if (!em && d.id_token) {
                const parts = d.id_token.split('.');
                if (parts[1]) em = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf8')).email;
            }
            if (em) {
                const k = em.toLowerCase(), isPrim = (f === primary);
                d.email = em; d.is_primary = isPrim;
                if (!accounts[k]) accounts[k] = d;
                else if (isPrim) accounts[k].is_primary = true;
            }
        } catch (_) {}
    }
    return accounts;
}

module.exports = {
    findPrimaryTokenFiles,
    loadAllAccounts,
};
