// Multi-Account Router: Gateway and Facade Module
const { getBindings, setBinding, setActiveAccount, getActiveAccountEmail } = require('./router/bindings.js');
const { loadAllAccounts } = require('./router/accounts.js');
const { fetchLanguageServerTelemetry, fetchDirectAccountQuotas, _quotaCache } = require('./router/telemetry.js');
const { startMultiAccountRouter } = require('./router/server.js');

let _refreshing = false;

async function refreshQuotasAsync() {
    if (_refreshing) return;
    _refreshing = true;
    try {
        const accountsMap = loadAllAccounts(), accountsList = Object.values(accountsMap);
        if (!_quotaCache.accounts) _quotaCache.accounts = [];
        const cachedByEmail = new Map(_quotaCache.accounts.map(a => [(a.email || '').toLowerCase(), a]));
        for (const acc of accountsList) {
            const em = (acc.email || '').toLowerCase();
            const prev = cachedByEmail.get(em);
            if (prev) {
                acc.quotas = prev.quotas || [];
                acc.license_status = prev.license_status;
                acc.tier = prev.tier;
            }
        }
        _quotaCache.accounts = accountsList;

        const lsTelemetry = await Promise.race([
            fetchLanguageServerTelemetry(),
            new Promise(r => setTimeout(() => r(null), 1200))
        ]);
        await Promise.all(accountsList.map(async (acc) => {
            try {
                const direct = await Promise.race([
                    fetchDirectAccountQuotas(acc),
                    new Promise(r => setTimeout(() => r(null), 3000))
                ]);
                if (direct && direct.status === 'ok' && direct.buckets?.length > 0) {
                    acc.quotas = direct.buckets; acc.license_status = 'ok'; acc.tier = acc.tier || 'TEAMS_TIER_PRO';
                    return;
                }
                if (acc.is_primary && lsTelemetry?.buckets?.length > 0) {
                    acc.quotas = lsTelemetry.buckets; acc.license_status = 'ok'; acc.tier = acc.tier || 'TEAMS_TIER_PRO';
                    return;
                }
                const prev = _quotaCache.accounts?.find(a => a.email?.toLowerCase() === acc.email?.toLowerCase());
                if (prev?.quotas?.length) {
                    acc.quotas = prev.quotas; acc.license_status = prev.license_status; acc.tier = prev.tier;
                } else {
                    acc.license_status = direct?.status || 'unknown'; acc.license_message = direct?.message || '';
                    acc.quotas = direct?.buckets || [];
                    if (direct?.status === 'no_license') acc.tier = 'No License';
                    else if (direct?.status === 'exhausted') acc.tier = 'Resource Exhausted';
                }
            } catch (_) {}
        }));
        _quotaCache.timestamp = Date.now();
        _quotaCache.accounts = accountsList;
    } catch (_) {} finally { _refreshing = false; }
}

function loadAllAccountsWithQuotasSync() {
    const rawMap = loadAllAccounts();
    const rawList = Object.values(rawMap);
    if (!_quotaCache.accounts || _quotaCache.accounts.length === 0) {
        _quotaCache.accounts = rawList;
    } else {
        const cachedEmails = new Set(_quotaCache.accounts.map(a => (a.email || '').toLowerCase()));
        for (const acc of rawList) {
            const em = (acc.email || '').toLowerCase();
            if (em && !cachedEmails.has(em)) {
                _quotaCache.accounts.push(acc);
                cachedEmails.add(em);
            }
        }
        const rawEmails = new Set(rawList.map(a => (a.email || '').toLowerCase()));
        _quotaCache.accounts = _quotaCache.accounts.filter(a => rawEmails.has((a.email || '').toLowerCase()));
    }
    if (Date.now() - _quotaCache.timestamp > 20000) refreshQuotasAsync().catch(() => {});
    return _quotaCache.accounts && _quotaCache.accounts.length ? _quotaCache.accounts : rawList;
}

async function loadAllAccountsWithQuotas() {
    if (!_quotaCache.accounts || !_quotaCache.accounts.some(a => a.quotas?.length)) {
        await refreshQuotasAsync();
    }
    return loadAllAccountsWithQuotasSync();
}

function removeAccount(email) {
    if (!email) return;
    try {
        const fs = require('fs'), path = require('path');
        const { ACCOUNTS_DIR } = require('./router/bindings.js');
        const { findPrimaryTokenFiles } = require('./router/accounts.js');
        const target = path.join(ACCOUNTS_DIR, `${email}.json`);
        if (fs.existsSync(target)) fs.unlinkSync(target);

        try {
            for (const f of fs.readdirSync(ACCOUNTS_DIR)) {
                if (f.toLowerCase() === `${email.toLowerCase()}.json`) {
                    const p = path.join(ACCOUNTS_DIR, f);
                    if (fs.existsSync(p)) fs.unlinkSync(p);
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
                if (em && em.toLowerCase() === email.toLowerCase()) {
                    fs.unlinkSync(f);
                }
            } catch (_) {}
        }

        if (_quotaCache?.accounts) {
            _quotaCache.accounts = _quotaCache.accounts.filter(a => (a.email || '').toLowerCase() !== email.toLowerCase());
        }
    } catch (_) {}
}

module.exports = {
    startMultiAccountRouter,
    loadAllAccounts,
    loadAllAccountsWithQuotas,
    loadAllAccountsWithQuotasSync,
    refreshQuotasAsync,
    removeAccount,
    getBindings,
    setBinding,
    setActiveAccount,
    getActiveAccountEmail: () => getActiveAccountEmail(loadAllAccounts()),
};
