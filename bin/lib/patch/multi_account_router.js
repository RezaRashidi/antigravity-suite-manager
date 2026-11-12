// Multi-Account Router: Gateway and Facade Module
const { getBindings, setBinding, setActiveAccount, getActiveAccountEmail } = require('./router/bindings.js');
const { loadAllAccounts, setPrimaryAccount, isAccountHealthy, markAccountUnhealthy, clearAccountUnhealthy, writeJsonAtomic } = require('./router/accounts.js');
const { fetchLanguageServerTelemetry, fetchDirectAccountQuotas, _quotaCache } = require('./router/telemetry.js');
const { startMultiAccountRouter, setLastCascadeId } = require('./router/server.js');

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
                if (prev.is_bypassed !== undefined) acc.is_bypassed = prev.is_bypassed;
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
                    new Promise(r => setTimeout(() => r(null), 8000))
                ]);
                const directFailed = direct && (direct.status === 'verify_required' || direct.status === 'no_license' || direct.status === 'auth_failed' || direct.status === 'forbidden_transient');
                if (direct?.tier_type && !directFailed) {
                    acc.tier_type = direct.tier_type;
                    acc.available_models = direct.available_models || [];
                    acc.model_count = direct.model_count || acc.available_models.length;
                    if (direct.tier_type === 'Paid Pro') {
                        acc.plan = 'Google AI Paid Pro';
                        acc.tier = 'Paid Pro';
                    } else if (direct.tier_type === 'Free Pro') {
                        acc.plan = 'Google AI Free Pro';
                        acc.tier = 'Free Pro';
                    }
                    if (direct.is_bypassed !== undefined) {
                        acc.is_bypassed = direct.is_bypassed;
                    }
                    try {
                        const fp = require('path').join(require('./router/bindings.js').ACCOUNTS_DIR, `${acc.email}.json`);
                        if (require('fs').existsSync(fp)) {
                            const cur = JSON.parse(require('fs').readFileSync(fp, 'utf8'));
                            cur.tier_type = acc.tier_type;
                            cur.tier = acc.tier;
                            cur.plan = acc.plan;
                            cur.available_models = acc.available_models;
                            if (acc.is_bypassed !== undefined) cur.is_bypassed = acc.is_bypassed;
                            writeJsonAtomic(fp, cur);
                        }
                    } catch (_) {}
                }
                if (direct && direct.status === 'ok' && direct.buckets?.length > 0) {
                    acc.quotas = direct.buckets; acc.license_status = 'ok';
                    if (!acc.tier || acc.tier === 'UNKNOWN_TIER') {
                        const isPro = (acc.plan && acc.plan.toLowerCase().includes('pro')) ||
                                      (direct.buckets.length >= 4) ||
                                      direct.buckets.some(b => b.family === 'claude');
                        acc.tier = isPro ? 'PRO' : 'FREE';
                        acc.plan = isPro ? (acc.plan || 'Google AI Pro') : 'Free';
                    }
                    return;
                }
                if (directFailed) {
                    if (direct.tier_type) {
                        acc.tier_type = direct.tier_type;
                        acc.available_models = direct.available_models || [];
                        acc.model_count = direct.model_count || acc.available_models.length;
                    }
                    acc.license_status = direct.status;
                    acc.license_message = direct.message || '';
                    acc.quotas = [];
                    acc.tier = direct.status === 'verify_required' ? 'Verify Required'
                        : (direct.status === 'auth_failed' ? 'Auth Required'
                            : (direct.status === 'no_license' ? 'No License' : (acc.tier_type || 'PRO')));
                    return;
                }
                if (acc.is_primary && lsTelemetry?.buckets?.length > 0) {
                    acc.quotas = lsTelemetry.buckets; acc.license_status = 'ok';
                    const planName = lsTelemetry.plan || 'Google AI Pro';
                    if (!acc.plan) acc.plan = planName;
                    if (!acc.tier) acc.tier = (planName.toLowerCase().includes('pro') || lsTelemetry.tierId === 'g1-pro-tier') ? 'PRO' : 'FREE';
                    return;
                }
                const prev = _quotaCache.accounts?.find(a => a.email?.toLowerCase() === acc.email?.toLowerCase());
                if (prev?.quotas?.length) {
                    acc.quotas = prev.quotas; acc.license_status = prev.license_status; acc.tier = prev.tier;
                    if (prev.is_bypassed !== undefined) acc.is_bypassed = prev.is_bypassed;
                } else {
                    acc.license_status = direct?.status || (direct === null ? 'loading' : 'unknown');
                    acc.license_message = direct?.message || '';
                    acc.quotas = direct?.buckets || [];
                    if (direct?.status === 'exhausted') acc.tier = 'Resource Exhausted';
                    else {
                        const isPro = acc.quotas?.some(b => b.family === 'claude');
                        acc.tier = isPro ? 'PRO' : 'FREE';
                    }
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
            } else {
                const cachedAcc = _quotaCache.accounts.find(a => (a.email || '').toLowerCase() === em);
                if (cachedAcc && acc.is_bypassed !== undefined) {
                    cachedAcc.is_bypassed = acc.is_bypassed;
                }
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
    markAccountBypassed: require('./router/accounts.js').markAccountBypassed,
    isAccountHealthy,
    markAccountUnhealthy,
    clearAccountUnhealthy,
    isEligibilityRpc: require('./router/eligibility_middleware.js').isEligibilityRpc,
    normalizeEligibilityResponse: require('./router/eligibility_middleware.js').normalizeEligibilityResponse,
    getBindings,
    setBinding,
    setActiveAccount,
    setPrimaryAccount,
    setLastCascadeId,
    getActiveAccountEmail: () => getActiveAccountEmail(loadAllAccounts()),
    getAuthenticUserAgent: require('./router/ua.js').getAuthenticUserAgent,
    resetProxyAgent: require('./router/proxy_agent.js').resetProxyAgent,
};
