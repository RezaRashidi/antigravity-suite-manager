// Multi-Account Router: Account Discovery and Primary Credentials
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');
const { ACCOUNTS_DIR, ensureAccountsDir } = require('./bindings.js');

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

function readTokenFromKeyring() {
    try {
        const rh = process.env.REAL_HOME || os.homedir();
        if (fs.existsSync(path.join(rh, '.gemini', 'cache', 'antigravity-keyring-unavailable'))) return null;
        const py = process.platform === 'win32' ? 'python' : (process.env.PYTHON || 'python3');
        const sDirs = [
            process.env.ANTIGRAVITY_SUITE_DIR,
            path.join(rh, 'PhpstormProjects', 'antigravity-suite-manager'),
            path.join(rh, '.antigravity-suite-manager'),
            path.join(rh, 'antigravity-suite-manager'),
        ].filter(Boolean);
        const pypath = sDirs.map(d => path.join(d, 'src')).join(':') + (process.env.PYTHONPATH ? ':' + process.env.PYTHONPATH : '');
        const script = 'import sys; from antigravity_suite.auth.keyring_dbus import get_token_from_keyring; t = get_token_from_keyring(); sys.stdout.write(t if t else "")';
        const env = { ...process.env, REAL_HOME: rh, PYTHONPATH: pypath };
        const res = spawnSync(py, ['-c', script], { env, timeout: 2000, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
        const raw = res?.stdout ? res.stdout.trim() : '';
        if (raw && raw.startsWith('{')) {
            try {
                const targetPath = path.join(rh, '.gemini', 'jetski-standalone-oauth-token');
                fs.mkdirSync(path.dirname(targetPath), { recursive: true });
                if (!fs.existsSync(targetPath)) {
                    fs.writeFileSync(targetPath, raw, { encoding: 'utf8', mode: 0o600 });
                }
                const cacheDir = path.join(rh, '.gemini', 'cache');
                fs.mkdirSync(cacheDir, { recursive: true });
                const marker = path.join(cacheDir, 'antigravity-keyring-unavailable');
                if (!fs.existsSync(marker)) fs.writeFileSync(marker, '', 'utf8');
            } catch (_) {}
            return raw;
        }
    } catch (_) {}
    return null;
}

function loadAllAccounts() {
    ensureAccountsDir();
    const accounts = {}, primary = path.join(os.homedir(), '.gemini', 'jetski-standalone-oauth-token');
    try {
        for (const f of fs.readdirSync(ACCOUNTS_DIR)) {
            if (f.endsWith('.json') && f !== 'bindings.json' && f !== 'oauth_credentials.json') {
                try {
                    const d = JSON.parse(fs.readFileSync(path.join(ACCOUNTS_DIR, f), 'utf8'));
                    if (d && d.email) {
                        d.is_primary = false;
                        d.is_bypassed = !!d.is_bypassed;
                        accounts[d.email.toLowerCase()] = d;
                    }
                } catch (_) {}
            }
        }
    } catch (_) {}
    for (const f of findPrimaryTokenFiles()) {
        try {
            const d = JSON.parse(fs.readFileSync(f, 'utf8'));
            let em = d.email || d.id_token_email;
            if (!em && d.id_token) {
                const parts = d.id_token.split('.');
                if (parts[1]) em = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf8')).email;
            }
            if (em) {
                const k = em.toLowerCase(), isPrim = (f === primary);
                d.email = em; d.is_primary = isPrim;
                if (!accounts[k]) {
                    accounts[k] = d;
                } else if (isPrim) {
                    accounts[k].is_primary = true;
                    if (d.token) accounts[k].token = d.token;
                    if (d.auth_method) accounts[k].auth_method = d.auth_method;
                    try {
                        fs.writeFileSync(path.join(ACCOUNTS_DIR, `${em}.json`), JSON.stringify(accounts[k], null, 2), 'utf8');
                    } catch (_) {}
                }
            }
        } catch (_) {}
    }
    const hasPrimary = Object.values(accounts).some(a => a.is_primary);
    if (!hasPrimary) {
        const kToken = readTokenFromKeyring();
        if (kToken) {
            try {
                const d = JSON.parse(kToken);
                let em = d.email || d.id_token_email;
                if (!em && d.id_token) {
                    const parts = d.id_token.split('.');
                    if (parts[1]) em = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf8')).email;
                }
                if (em) {
                    d.email = em;
                    d.is_primary = true;
                    accounts[em.toLowerCase()] = d;
                }
            } catch (_) {}
        }
    }
    return accounts;
}

function setPrimaryAccount(email) {
    if (!email) return false;
    const accounts = loadAllAccounts();
    const target = accounts[email.toLowerCase()];
    if (!target) return false;

    try {
        for (const f of fs.readdirSync(ACCOUNTS_DIR)) {
            if (f.endsWith('.json') && f !== 'bindings.json' && f !== 'oauth_credentials.json') {
                try {
                    const fp = path.join(ACCOUNTS_DIR, f);
                    const d = JSON.parse(fs.readFileSync(fp, 'utf8'));
                    if (d && d.email) {
                        d.is_primary = (d.email.toLowerCase() === email.toLowerCase());
                        fs.writeFileSync(fp, JSON.stringify(d, null, 2), 'utf8');
                    }
                } catch (_) {}
            }
        }
    } catch (_) {}

    const tokenData = {
        token: target.token || {},
        id_token: target.id_token || '',
        email: target.email,
        name: target.name || target.email.split('@')[0],
        auth_method: target.auth_method || 'consumer'
    };
    if (process.env.ANTIGRAVITY_TEST) {
        const testHome = process.env.REAL_HOME || os.homedir();
        for (const dName of ['.gemini', '.gemide']) {
            const pDir = path.join(testHome, dName);
            try {
                fs.mkdirSync(pDir, { recursive: true });
                fs.writeFileSync(path.join(pDir, 'jetski-standalone-oauth-token'), JSON.stringify(tokenData, null, 2), 'utf8');
            } catch (_) {}
        }
    } else {
        const rh = process.env.REAL_HOME || os.homedir();
        const pDirs = [
            path.join(rh, '.gemini'),
            path.join(rh, '.gemide'),
            path.join(rh, '.gemini', 'antigravity-ide'),
            path.join(rh, '.config', 'antigravity'),
            path.join(rh, '.config', 'Antigravity')
        ];
        if (process.env.REAL_HOME && process.env.REAL_HOME !== os.homedir()) {
            pDirs.push(path.join(os.homedir(), '.gemini'));
            pDirs.push(path.join(os.homedir(), '.gemide'));
        }
        for (const pDir of pDirs) {
            if (fs.existsSync(pDir)) {
                try {
                    fs.writeFileSync(path.join(pDir, 'jetski-standalone-oauth-token'), JSON.stringify(tokenData, null, 2), 'utf8');
                } catch (_) {}
            }
        }
    }

    try {
        const { setActiveAccount, setBinding } = require('./bindings.js');
        setActiveAccount(target.email);
        setBinding('__default__', target.email);
    } catch (_) {}

    try {
        require('./telemetry.js').forceRefreshLanguageServerQuota();
    } catch (_) {}

    return true;
}

function markAccountBypassed(email, isBypassed = true) {
    if (!email) return false;
    ensureAccountsDir();
    try {
        const fp = path.join(ACCOUNTS_DIR, `${email}.json`);
        if (fs.existsSync(fp)) {
            const cur = JSON.parse(fs.readFileSync(fp, 'utf8'));
            cur.is_bypassed = !!isBypassed;
            fs.writeFileSync(fp, JSON.stringify(cur, null, 2), 'utf8');
            return true;
        }
        for (const f of fs.readdirSync(ACCOUNTS_DIR)) {
            if (f.toLowerCase() === `${email.toLowerCase()}.json`) {
                const p = path.join(ACCOUNTS_DIR, f);
                const cur = JSON.parse(fs.readFileSync(p, 'utf8'));
                cur.is_bypassed = !!isBypassed;
                fs.writeFileSync(p, JSON.stringify(cur, null, 2), 'utf8');
                return true;
            }
        }
    } catch (_) {}
    return false;
}

module.exports = {
    findPrimaryTokenFiles,
    loadAllAccounts,
    setPrimaryAccount,
    markAccountBypassed,
};
