// Multi-Account Router: Gateway and Facade Module
const { getBindings, setBinding, setActiveAccount, getActiveAccountEmail } = require('./router/bindings');
const { loadAllAccounts } = require('./router/accounts');
const { fetchLanguageServerTelemetry, fetchDirectAccountQuotas, _quotaCache } = require('./router/telemetry');
const { startMultiAccountRouter } = require('./router/server');

async function loadAllAccountsWithQuotas() {
    const now = Date.now();
    if (_quotaCache.accounts.length > 0 && (now - _quotaCache.timestamp < 30000)) {
        return _quotaCache.accounts;
    }
    const accountsMap = loadAllAccounts();
    const accountsList = Object.values(accountsMap);
    const lsTelemetry = await fetchLanguageServerTelemetry();

    for (const acc of accountsList) {
        if (acc.is_primary && lsTelemetry?.buckets?.length > 0) {
            acc.quotas = lsTelemetry.buckets;
            acc.license_status = 'ok';
            acc.tier = acc.tier || 'TEAMS_TIER_PRO';
        } else {
            const direct = await fetchDirectAccountQuotas(acc);
            acc.license_status = direct.status;
            acc.license_message = direct.message || '';
            acc.quotas = direct.buckets || [];
            if (direct.status === 'no_license') acc.tier = 'No License (Subscription Required)';
            else if (direct.status === 'exhausted') acc.tier = 'Resource Exhausted';
        }
    }
    _quotaCache.timestamp = now;
    _quotaCache.accounts = accountsList;
    return accountsList;
}

module.exports = {
    startMultiAccountRouter,
    loadAllAccounts,
    loadAllAccountsWithQuotas,
    getBindings,
    setBinding,
    setActiveAccount,
    getActiveAccountEmail: () => getActiveAccountEmail(loadAllAccounts()),
};
