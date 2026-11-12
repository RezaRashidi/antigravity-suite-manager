// Multi-Account Router: Account Discovery and Primary Credentials
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');
const { ACCOUNTS_DIR, ensureAccountsDir, logTraffic } = require('./bindings.js');

const UNHEALTHY_STATUSES = new Set(['verify_required', 'no_license', 'auth_failed']);
const DEFAULT_UNHEALTHY_COOLDOWN_MS = 30 * 60 * 1000;
const TRANSIENT_COOLDOWN_MS = 60 * 1000;
const _unhealthyAccounts = new Map();

function writeJsonAtomic(filePath, dataObj) {
    ensureAccountsDir();
    const tmp = `${filePath}.tmp.${process.pid}.${Date.now()}`;
    fs.writeFileSync(tmp, JSON.stringify(dataObj, null, 2), 'utf8');
    fs.renameSync(tmp, filePath);
}

function getRefreshTokenFingerprint(acc) {
    const rt = acc?.token?.refresh_token || acc?.refresh_token || '';
    return rt ? String(rt).slice(-12) : '';
}

function classifyHttpError(statusCode, bodyStr = '') {
    const body = String(bodyStr || '');
    if (/verify your account/i.test(body)) {
        return { reason: 'verify_required', message: 'Verify your account to continue.', persist: true };
    }
    if (/valid license|SUBSCRIPTION_REQUIRED|UNSUPPORTED_CLIENT/i.test(body)) {
        return { reason: 'no_license', message: 'Subscription Required', persist: true };
    }
    if (statusCode === 401 || /UNAUTHENTICATED|invalid_grant/i.test(body)) {
        return { reason: 'auth_failed', message: 'Authentication expired or revoked', persist: true };
    }
    if (statusCode === 403) {
        return { reason: 'forbidden_transient', message: 'Upstream HTTP 403 Forbidden (temporary cooldown)', persist: false };
    }
    return { reason: 'unknown', message: `Upstream HTTP ${statusCode}`, persist: false };
}

function findAccountJsonPath(email) {
    if (!email) return null;
    ensureAccountsDir();
    const direct = path.join(ACCOUNTS_DIR, `${email}.json`);
    if (fs.existsSync(direct)) return direct;
    try {
        const lower = `${email.toLowerCase()}.json`;
        for (const f of fs.readdirSync(ACCOUNTS_DIR)) {
            if (f.toLowerCase() === lower) return path.join(ACCOUNTS_DIR, f);
        }
    } catch (_) {}
    return null;
}

function scrubAccountHealthFields(acc) {
    if (!acc || typeof acc !== 'object') return acc;
    acc.license_status = 'ok';
    delete acc.license_message;
    delete acc.unhealthy_at;
    delete acc.unhealthy_until;
    delete acc.unhealthy_token_fp;
    if (acc.tier === 'Verify Required' || acc.tier === 'No License' || acc.tier === 'Auth Required') {
        acc.tier = acc.tier_type || 'PRO';
    }
    return acc;
}

function markAccountUnhealthy(email, reason = 'verify_required', message = '', cooldownMs = DEFAULT_UNHEALTHY_COOLDOWN_MS, accountObj = null, options = {}) {
    if (!email || email === 'Primary (Native)') return false;
    const key = email.toLowerCase();
    const effectiveCooldownMs = (reason === 'forbidden_transient' && cooldownMs === DEFAULT_UNHEALTHY_COOLDOWN_MS)
        ? TRANSIENT_COOLDOWN_MS
        : (cooldownMs > 0 ? cooldownMs : DEFAULT_UNHEALTHY_COOLDOWN_MS);
    const shouldPersist = options.persist !== undefined ? !!options.persist : UNHEALTHY_STATUSES.has(reason);
    const fp = accountObj ? getRefreshTokenFingerprint(accountObj) : (_unhealthyAccounts.get(key)?.tokenFp || '');
    const now = Date.now();
    _unhealthyAccounts.set(key, {
        reason,
        message: message || reason,
        markedAt: now,
        cooldownMs: effectiveCooldownMs,
        untilMs: now + effectiveCooldownMs,
        tokenFp: fp,
    });
    if (shouldPersist) {
        try {
            const fpJson = findAccountJsonPath(email);
            if (fpJson) {
                const cur = JSON.parse(fs.readFileSync(fpJson, 'utf8'));
                const refreshFp = getRefreshTokenFingerprint(cur);
                if (refreshFp) _unhealthyAccounts.get(key).tokenFp = refreshFp;
                cur.license_status = reason;
                cur.license_message = message || reason;
                cur.unhealthy_at = new Date(now).toISOString();
                cur.unhealthy_until = new Date(now + effectiveCooldownMs).toISOString();
                if (refreshFp) cur.unhealthy_token_fp = refreshFp;
                if (reason === 'verify_required') cur.tier = 'Verify Required';
                else if (reason === 'no_license') cur.tier = 'No License';
                else if (reason === 'auth_failed') cur.tier = 'Auth Required';
                writeJsonAtomic(fpJson, cur);
            }
        } catch (_) {}
    }
    try { logTraffic(`[HEALTH] Marked [${email}] unhealthy (${reason}, persist=${shouldPersist}): ${message || reason}`); } catch (_) {}
    return true;
}

function clearAccountUnhealthy(email) {
    if (!email || email === 'Primary (Native)') return false;
    const key = email.toLowerCase();
    const hadMem = _unhealthyAccounts.delete(key);
    try {
        const fpJson = findAccountJsonPath(email);
        if (fpJson) {
            const cur = JSON.parse(fs.readFileSync(fpJson, 'utf8'));
            if (UNHEALTHY_STATUSES.has(cur.license_status) || cur.license_message || cur.unhealthy_at || cur.unhealthy_until || cur.unhealthy_token_fp) {
                scrubAccountHealthFields(cur);
                writeJsonAtomic(fpJson, cur);
                return true;
            }
        }
    } catch (_) {}
    return hadMem;
}

function isAccountHealthy(accOrEmail, accountsMap = null) {
    if (!accOrEmail) return false;
    let acc = null;
    let email = null;
    if (typeof accOrEmail === 'string') {
        email = accOrEmail;
        if (email === 'Primary (Native)') {
            const prim = accountsMap ? Object.values(accountsMap).find(a => a && a.is_primary) : null;
            return prim ? isAccountHealthy(prim, accountsMap) : true;
        }
        acc = accountsMap ? accountsMap[email.toLowerCase()] : null;
    } else {
        acc = accOrEmail;
        email = acc.email || '';
    }

    const key = (email || '').toLowerCase();
    const curFp = acc ? getRefreshTokenFingerprint(acc) : '';
    if (key) {
        const mem = _unhealthyAccounts.get(key);
        if (mem) {
            if (mem.tokenFp && curFp && mem.tokenFp !== curFp) {
                _unhealthyAccounts.delete(key);
                clearAccountUnhealthy(email);
                scrubAccountHealthFields(acc);
            } else if ((Date.now() - mem.markedAt) < mem.cooldownMs) {
                return false;
            } else {
                _unhealthyAccounts.delete(key);
                clearAccountUnhealthy(email);
                scrubAccountHealthFields(acc);
            }
        }
    }

    if (acc) {
        if (acc.unhealthy_token_fp && curFp && acc.unhealthy_token_fp !== curFp) {
            clearAccountUnhealthy(email || acc.email);
            scrubAccountHealthFields(acc);
        } else if (acc.unhealthy_until) {
            const untilMs = Date.parse(acc.unhealthy_until);
            if (!Number.isNaN(untilMs) && Date.now() >= untilMs) {
                clearAccountUnhealthy(email || acc.email);
                scrubAccountHealthFields(acc);
            }
        }
        if (UNHEALTHY_STATUSES.has(acc.license_status)) return false;
        if (acc.tier === 'Verify Required' || acc.tier === 'No License' || acc.tier === 'Auth Required') return false;
        if (acc.token !== undefined) {
            const hasAccess = typeof acc.token === 'string' ? !!acc.token : !!(acc.token && (acc.token.access_token || acc.token.refresh_token));
            if (!hasAccess && !acc.access_token && !acc.refresh_token) return false;
        }
    }
    return true;
}

function pickHealthyFallbackAccount(accountsMap = {}, excludeEmails = [], preferredEmail = null) {
    const excluded = new Set((excludeEmails || []).filter(Boolean).map(e => String(e).toLowerCase()));
    const entries = Object.values(accountsMap || {}).filter(a => a && a.email && !excluded.has(a.email.toLowerCase()) && isAccountHealthy(a, accountsMap));
    if (!entries.length) return null;

    if (preferredEmail && preferredEmail !== 'Primary (Native)') {
        const pref = entries.find(a => a.email.toLowerCase() === preferredEmail.toLowerCase());
        if (pref) return pref.email;
    }

    entries.sort((a, b) => {
        const aOk = a.license_status === 'ok' ? 1 : 0;
        const bOk = b.license_status === 'ok' ? 1 : 0;
        if (aOk !== bOk) return bOk - aOk;
        const aTier = String(a.tier_type || a.tier || '').toLowerCase().includes('paid') ? 1 : 0;
        const bTier = String(b.tier_type || b.tier || '').toLowerCase().includes('paid') ? 1 : 0;
        if (aTier !== bTier) return bTier - aTier;
        return a.email.localeCompare(b.email);
    });
    return entries[0].email;
}

function findPrimaryTokenFiles() {
    const homes = process.env.ANTIGRAVITY_TEST
        ? [process.env.REAL_HOME || os.homedir()]
        : [os.homedir()];
    if (!process.env.ANTIGRAVITY_TEST && process.env.REAL_HOME && process.env.REAL_HOME !== os.homedir()) homes.push(process.env.REAL_HOME);
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

function isAccountJsonFile(f) {
    return f.endsWith('.json') && f !== 'bindings.json' && f !== 'oauth_credentials.json' && f !== 'subagent_policy.json';
}

function loadAllAccounts() {
    ensureAccountsDir();
    const accounts = {}, primary = path.join(os.homedir(), '.gemini', 'jetski-standalone-oauth-token');
    try {
        for (const f of fs.readdirSync(ACCOUNTS_DIR)) {
            if (isAccountJsonFile(f)) {
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
                        writeJsonAtomic(path.join(ACCOUNTS_DIR, `${em}.json`), accounts[k]);
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
            if (isAccountJsonFile(f)) {
                try {
                    const fp = path.join(ACCOUNTS_DIR, f);
                    const d = JSON.parse(fs.readFileSync(fp, 'utf8'));
                    if (d && d.email) {
                        d.is_primary = (d.email.toLowerCase() === email.toLowerCase());
                        writeJsonAtomic(fp, d);
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
        const fpJson = findAccountJsonPath(email);
        if (fpJson) {
            const cur = JSON.parse(fs.readFileSync(fpJson, 'utf8'));
            cur.is_bypassed = !!isBypassed;
            writeJsonAtomic(fpJson, cur);
            return true;
        }
    } catch (_) {}
    return false;
}

module.exports = {
    writeJsonAtomic,
    findPrimaryTokenFiles,
    loadAllAccounts,
    setPrimaryAccount,
    markAccountBypassed,
    UNHEALTHY_STATUSES,
    classifyHttpError,
    markAccountUnhealthy,
    clearAccountUnhealthy,
    isAccountHealthy,
    pickHealthyFallbackAccount,
    _unhealthyAccounts,
};
