// Multi-Account Router: Gateway and Facade Module
const { getBindings, setBinding, setActiveAccount, getActiveAccountEmail } = require('./router/bindings');
const { loadAllAccounts } = require('./router/accounts');
const { fetchLanguageServerTelemetry, fetchDirectAccountQuotas, _quotaCache } = require('./router/telemetry');
const { startMultiAccountRouter } = require('./router/server');

let _refreshing = false;

async function refreshQuotasAsync() {
    if (_refreshing) return;
    _refreshing = true;
    try {
        const accountsMap = loadAllAccounts(), accountsList = Object.values(accountsMap);
        const lsTelemetry = await Promise.race([
            fetchLanguageServerTelemetry(),
            new Promise(r => setTimeout(() => r(null), 1200))
        ]);
        await Promise.all(accountsList.map(async (acc) => {
            try {
                if (acc.is_primary && lsTelemetry?.buckets?.length > 0) {
                    acc.quotas = lsTelemetry.buckets; acc.license_status = 'ok'; acc.tier = acc.tier || 'TEAMS_TIER_PRO';
                    return;
                }
                const direct = await Promise.race([
                    fetchDirectAccountQuotas(acc),
                    new Promise(r => setTimeout(() => r(null), 3500))
                ]);
                if (direct && direct.status === 'ok' && direct.buckets?.length > 0) {
                    acc.quotas = direct.buckets; acc.license_status = 'ok'; acc.tier = acc.tier || 'TEAMS_TIER_PRO';
                } else {
                    const prev = _quotaCache.accounts?.find(a => a.email === acc.email);
                    if (prev?.quotas?.length) {
                        acc.quotas = prev.quotas; acc.license_status = prev.license_status; acc.tier = prev.tier;
                    } else {
                        acc.license_status = direct?.status || 'unknown'; acc.license_message = direct?.message || '';
                        acc.quotas = direct?.buckets || [];
                        if (direct?.status === 'no_license') acc.tier = 'No License';
                        else if (direct?.status === 'exhausted') acc.tier = 'Resource Exhausted';
                    }
                }
            } catch (_) {}
        }));
        _quotaCache.timestamp = Date.now();
        _quotaCache.accounts = accountsList;
    } catch (_) {} finally { _refreshing = false; }
}

function loadAllAccountsWithQuotasSync() {
    const raw = Object.values(loadAllAccounts());
    if (!_quotaCache.accounts || _quotaCache.accounts.length === 0) _quotaCache.accounts = raw;
    if (Date.now() - _quotaCache.timestamp > 45000) refreshQuotasAsync().catch(() => {});
    return _quotaCache.accounts && _quotaCache.accounts.length ? _quotaCache.accounts : raw;
}

async function loadAllAccountsWithQuotas() {
    if (!_quotaCache.accounts || !_quotaCache.accounts.some(a => a.quotas?.length)) {
        await refreshQuotasAsync();
    }
    return loadAllAccountsWithQuotasSync();
}

setTimeout(() => { refreshQuotasAsync().catch(() => {}); }, 100);

module.exports = {
    startMultiAccountRouter,
    loadAllAccounts,
    loadAllAccountsWithQuotas,
    loadAllAccountsWithQuotasSync,
    refreshQuotasAsync,
    getBindings,
    setBinding,
    setActiveAccount,
    getActiveAccountEmail: () => getActiveAccountEmail(loadAllAccounts()),
};
