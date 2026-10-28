"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.describeGoogleAccessError = describeGoogleAccessError;
function describeGoogleAccessError(status, operation = 'generation') {
    const service = operation === 'oauth' ? 'Google OAuth' : 'Google Cloud Code';
    const code = Number.isInteger(status) && status >= 100 && status <= 599 ? status : 502;
    if (code === 401)
        return {
            category: 'authentication',
            message: `${service} rejected authorization (HTTP 401). Reconnect this account using your OAuth client.`,
        };
    if (code === 403)
        return {
            category: 'access-denied',
            message: operation === 'oauth'
                ? 'Google OAuth denied access (HTTP 403). Check your OAuth client, consent/test users and account access settings. This is not a quota limit.'
                : 'Google Cloud Code denied access (HTTP 403). Check account/project permissions and service eligibility. Signing in does not grant access; this status alone does not identify a required subscription.',
        };
    if (code === 429)
        return {
            category: 'rate-limited',
            message: `${service} reported a rate or quota limit (HTTP 429). Respect the provider retry/reset delay; signing in again does not increase quota.`,
        };
    if (code === 408 || code >= 500)
        return {
            category: 'transient',
            message: `${service} is temporarily unavailable (HTTP ${code}). Retry later; switching accounts may not resolve provider-wide demand. This is not an authentication failure.`,
        };
    return {
        category: 'request-failed',
        message: operation === 'oauth'
            ? `Google OAuth request failed (HTTP ${code}). Check your OAuth client configuration.`
            : `Google Cloud Code request failed (HTTP ${code}). Check the endpoint, model and project configuration.`,
    };
}
//# sourceMappingURL=googleAccessErrors.js.map