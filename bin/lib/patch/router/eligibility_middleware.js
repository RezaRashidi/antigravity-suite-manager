// Multi-Account Router: Local Network Eligibility & Location Normalization Middleware
// Intercepts authentication and license handshake endpoints to enforce valid client entitlement
// without requiring binary patching of the language_server executable.

function isEligibilityRpc(url) {
    if (!url || typeof url !== 'string') return false;
    return url.includes('loadCodeAssist') ||
           url.includes('fetchUserInfo') ||
           url.includes('retrieveUserQuotaSummary');
}

function normalizeEligibilityResponse(url, statusCode, bodyStr) {
    if (!bodyStr || typeof bodyStr !== 'string') return { statusCode, bodyStr, modified: false };

    try {
        let json = JSON.parse(bodyStr);
        let modified = false;

        // 1. /v1internal:loadCodeAssist
        if (url.includes('loadCodeAssist')) {
            if (statusCode === 403 || json.ineligible || json.error?.code === 403 || json.ineligibilityReason) {
                statusCode = 200;
                delete json.ineligible;
                delete json.ineligibilityReason;
                delete json.error;
                json.hasValidAuth = true;
                json.has_valid_auth = true;
                json.isGcpTos = true;
                if (!json.currentTier) json.currentTier = 'TEAMS_TIER_PRO';
                modified = true;
            } else if (json && typeof json === 'object') {
                if (json.hasValidAuth === false || json.has_valid_auth === false) {
                    json.hasValidAuth = true;
                    json.has_valid_auth = true;
                    modified = true;
                }
            }
        }

        // 2. /v1internal:fetchUserInfo
        if (url.includes('fetchUserInfo')) {
            if (json && typeof json === 'object') {
                if (json.isEligible === false) {
                    json.isEligible = true;
                    modified = true;
                }
            }
        }

        // 3. /v1internal:retrieveUserQuotaSummary
        if (url.includes('retrieveUserQuotaSummary')) {
            if (statusCode === 403 && json.error?.code === 403) {
                statusCode = 200;
                json = {
                    userStatus: {
                        isEligible: true,
                        tier: 'TEAMS_TIER_PRO'
                    },
                    buckets: []
                };
                modified = true;
            }
        }

        if (modified) {
            return {
                statusCode,
                bodyStr: JSON.stringify(json),
                modified: true
            };
        }
    } catch (_) {}

    return { statusCode, bodyStr, modified: false };
}

module.exports = {
    isEligibilityRpc,
    normalizeEligibilityResponse
};
