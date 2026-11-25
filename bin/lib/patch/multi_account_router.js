// Multi-Account Router: Gateway and Facade Module
const { getBindings, setBinding, setActiveAccount, getActiveAccountEmail } = require('./router/bindings.js');
const { loadAllAccounts, setPrimaryAccount, isAccountHealthy, markAccountUnhealthy, clearAccountUnhealthy, writeJsonAtomic } = require('./router/accounts.js');
const { fetchLanguageServerTelemetry, fetchDirectAccountQuotas, _quotaCache } = require('./router/telemetry.js');
const { startMultiAccountRouter, setLastCascadeId } = require('./router/server.js');

const _refreshPromises = new Map();

async function refreshQuotasAsync(force = false, targetEmail = null) {
    const scopeKey = targetEmail ? String(targetEmail).toLowerCase() : '__all__';
    const existing = _refreshPromises.get(scopeKey);
    if (existing) {
        if (!force || (Date.now() - existing.ts < 3000)) {
            return existing.promise;
        }
        await existing.promise;
    }
    const run = (async () => {
        try {
            const accountsMap = loadAllAccounts(), accountsList = Object.values(accountsMap);
            if (!_quotaCache.accounts) _quotaCache.accounts = [];
            const cachedByEmail = new Map(_quotaCache.accounts.map(a => [(a.email || '').toLowerCase(), a]));
            for (const acc of accountsList) {
                const em = (acc.email || '').toLowerCase();
                const prev = cachedByEmail.get(em);
                if (prev) {
                    if (!acc.quotas?.length && prev.quotas?.length) acc.quotas = prev.quotas;
                    if (!acc.license_status && prev.license_status) acc.license_status = prev.license_status;
                    if (!acc.tier_type && prev.tier_type) acc.tier_type = prev.tier_type;
                    if ((!acc.tier || acc.tier === 'PRO') && prev.tier) acc.tier = prev.tier;
                    if (!acc.plan && prev.plan) acc.plan = prev.plan;
                    if (!acc.available_models?.length && prev.available_models?.length) acc.available_models = prev.available_models;
                    if (!acc.available_model_ids?.length && prev.available_model_ids?.length) acc.available_model_ids = prev.available_model_ids;
                    if (!acc.model_count && prev.model_count) acc.model_count = prev.model_count;
                    if (prev.verify_url && !acc.verify_url) acc.verify_url = prev.verify_url;
                    if (prev.license_message && !acc.license_message) acc.license_message = prev.license_message;
                    if (prev.refresh_error && !acc.refresh_error) acc.refresh_error = prev.refresh_error;
                    if (prev.is_bypassed !== undefined) acc.is_bypassed = prev.is_bypassed;
                }
            }
            _quotaCache.accounts = accountsList;

            const targets = targetEmail
                ? accountsList.filter(a => a.email && a.email.toLowerCase() === scopeKey)
                : accountsList;
            if (!targets.length) return;

            const shouldFetchLs = !targetEmail || targets.some(a => a.is_primary);
            const lsPromise = shouldFetchLs
                ? Promise.race([fetchLanguageServerTelemetry(), new Promise(r => setTimeout(() => r(null), 1200))])
                : Promise.resolve(null);
            const [lsTelemetry] = await Promise.all([
                lsPromise,
                Promise.all(targets.map(async (acc) => {
                try {
                    const direct = await Promise.race([
                        fetchDirectAccountQuotas(acc, force),
                        new Promise(r => setTimeout(() => r(null), 8000))
                    ]);
                    const directFailed = direct && (direct.status === 'verify_required' || direct.status === 'no_license' || direct.status === 'auth_failed' || direct.status === 'forbidden_transient');
                    const hasFreshModels = Boolean(direct && ((direct.available_models && direct.available_models.length > 0) || direct.model_count > 0));
                    if (direct?.tier_type && !directFailed && hasFreshModels) {
                        acc.tier_type = direct.tier_type;
                        acc.available_models = direct.available_models || [];
                        acc.available_model_ids = direct.available_model_ids || [];
                        acc.model_count = direct.model_count || acc.available_models.length;
                        if (direct.tier_type === 'Paid Pro') {
                            acc.plan = 'Google AI Paid Pro';
                            acc.tier = 'Paid Pro';
                        } else if (direct.tier_type === 'Free Pro') {
                            acc.plan = 'Google AI Free Pro';
                            acc.tier = 'Free Pro';
                        } else {
                            acc.plan = 'Free';
                            acc.tier = 'FREE';
                        }
                        if (direct.is_bypassed !== undefined) {
                            acc.is_bypassed = direct.is_bypassed;
                        }
                    }
                if (direct && direct.status === 'ok' && direct.buckets?.length > 0) {
                    acc.quotas = direct.buckets; acc.license_status = 'ok';
                    delete acc.refresh_error; delete acc.verify_url; delete acc.license_message;
                    if (!acc.tier || acc.tier === 'UNKNOWN_TIER') {
                        const isPro = (acc.plan && acc.plan.toLowerCase().includes('pro')) ||
                                      (direct.buckets.length >= 4) ||
                                      direct.buckets.some(b => b.family === 'claude');
                        acc.tier = isPro ? 'PRO' : 'FREE';
                        acc.plan = isPro ? (acc.plan || 'Google AI Pro') : 'Free';
                    }
                }
                if (direct && !directFailed && (direct.tier_type || (direct.status === 'ok' && direct.buckets?.length > 0))) {
                    try {
                        const fp = require('path').join(require('./router/bindings.js').ACCOUNTS_DIR, `${acc.email}.json`);
                        if (require('fs').existsSync(fp)) {
                            const cur = JSON.parse(require('fs').readFileSync(fp, 'utf8'));
                            if (direct.tier_type) {
                                cur.tier_type = acc.tier_type;
                                cur.tier = acc.tier;
                                cur.plan = acc.plan;
                                cur.available_models = acc.available_models;
                                cur.available_model_ids = acc.available_model_ids;
                            }
                            if (acc.quotas?.length) cur.quotas = acc.quotas;
                            if (acc.is_bypassed !== undefined) cur.is_bypassed = acc.is_bypassed;
                            writeJsonAtomic(fp, cur);
                        }
                    } catch (_) {}
                    if (direct.status === 'ok' && direct.buckets?.length > 0) return;
                }
                if (directFailed) {
                    if (direct.tier_type) {
                        acc.tier_type = direct.tier_type;
                        acc.available_models = direct.available_models || [];
                        acc.available_model_ids = direct.available_model_ids || [];
                        acc.model_count = direct.model_count || acc.available_models.length;
                    }
                    acc.license_status = direct.status;
                    acc.license_message = direct.message || '';
                    if (direct.verify_url) acc.verify_url = direct.verify_url;
                    acc.refresh_error = direct.message || direct.status;
                    acc.quotas = [];
                    acc.tier = direct.status === 'verify_required' ? 'Verify Required'
                        : (direct.status === 'auth_failed' ? 'Auth Required'
                            : (direct.status === 'no_license' ? 'No License' : (acc.tier_type || 'PRO')));
                    return;
                }
                const errMsg = direct === null
                    ? 'Refresh timed out (8s)'
                    : (direct?.message || (direct?.status && direct.status !== 'ok' ? `Refresh failed (${direct.status})` : 'Refresh failed'));
                const prev = _quotaCache.accounts?.find(a => a.email?.toLowerCase() === acc.email?.toLowerCase());
                if (prev?.quotas?.length) {
                    acc.quotas = prev.quotas; acc.license_status = prev.license_status; acc.tier = prev.tier;
                    acc.refresh_error = errMsg;
                    if (prev.is_bypassed !== undefined) acc.is_bypassed = prev.is_bypassed;
                } else {
                    acc.license_status = direct?.status || 'refresh_failed';
                    acc.license_message = errMsg;
                    acc.refresh_error = errMsg;
                    acc.quotas = direct?.buckets || [];
                    if (direct?.status === 'exhausted') acc.tier = 'Resource Exhausted';
                    else if (!acc.tier) {
                        const isPro = acc.quotas?.some(b => b.family === 'claude');
                        acc.tier = isPro ? 'PRO' : 'FREE';
                    }
                }
            } catch (_) {}
        }))]);
        const lsRes = lsTelemetry;
        if (lsRes?.buckets?.length > 0) {
            const prim = targets.find(a => a.is_primary && (!a.quotas || !a.quotas.length) && !['verify_required', 'no_license', 'auth_failed'].includes(a.license_status));
            if (prim) {
                prim.quotas = lsRes.buckets; prim.license_status = 'ok';
                delete prim.refresh_error;
                const planName = lsRes.plan || 'Google AI Pro';
                if (!prim.plan) prim.plan = planName;
                if (!prim.tier) prim.tier = (planName.toLowerCase().includes('pro') || lsRes.tierId === 'g1-pro-tier') ? 'PRO' : 'FREE';
            }
        }
        _quotaCache.timestamp = Date.now();
        _quotaCache.accounts = accountsList;
        } catch (_) {}
    })();
    _refreshPromises.set(scopeKey, { ts: Date.now(), promise: run });
    try { await run; } finally {
        if (_refreshPromises.get(scopeKey)?.promise === run) _refreshPromises.delete(scopeKey);
    }
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
