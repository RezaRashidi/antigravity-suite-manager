"use strict";
/**
 * Shared state module for proxy orchestration.
 * Extracted from proxy.js to decouple translators from main orchestration.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.stateTimestamps = exports.translatedToolCalls = exports.activeStreamContexts = exports.modelReasoningContent = exports.modelToolCallIds = void 0;
exports.touchStateTimestamp = touchStateTimestamp;
exports.startCleanupInterval = startCleanupInterval;
exports.stopCleanupInterval = stopCleanupInterval;
exports.officialQuotaScopeKey = officialQuotaScopeKey;
exports.recordOfficialQuota = recordOfficialQuota;
exports.getOfficialQuota = getOfficialQuota;
exports.clearOfficialQuota = clearOfficialQuota;
// ─── State ────────────────────────────────────────────────────────────────
/** modelName → { "functionName": "original_tool_call_id" } */
exports.modelToolCallIds = new Map();
/** modelName → preserved reasoning_content from previous turn */
exports.modelReasoningContent = new Map();
/** streamId → { accumulatedText, accumulatedReasoning, toolCalls } */
exports.activeStreamContexts = new Map();
/** toolCallId → { originalName, translatedName, cmd, cwd } */
exports.translatedToolCalls = new Map();
/** State entry timestamps for periodic cleanup */
exports.stateTimestamps = {
    streamCtx: new Map(),
    toolCallIds: new Map(),
    translatedCalls: new Map(),
    reasoning: new Map(),
};
// ─── Helpers ──────────────────────────────────────────────────────────────
function touchStateTimestamp(map, key) {
    map.set(key, Date.now());
}
// ─── Periodic Cleanup (managed lifecycle) ─────────────────────────────────
let cleanupInterval = null;
function startCleanupInterval() {
    if (cleanupInterval)
        return; // already running
    cleanupInterval = setInterval(() => {
        const now = Date.now();
        const STREAM_TTL = 600000; // 10 minutes for active stream contexts
        const TOOL_TTL = 1800000; // 30 minutes for tool call IDs & reasoning
        for (const [key, ts] of exports.stateTimestamps.streamCtx) {
            if (now - ts > STREAM_TTL) {
                exports.activeStreamContexts.delete(key);
                exports.stateTimestamps.streamCtx.delete(key);
            }
        }
        for (const [key, ts] of exports.stateTimestamps.toolCallIds) {
            if (now - ts > TOOL_TTL) {
                exports.modelToolCallIds.delete(key);
                exports.stateTimestamps.toolCallIds.delete(key);
            }
        }
        for (const [key, ts] of exports.stateTimestamps.translatedCalls) {
            if (now - ts > TOOL_TTL) {
                exports.translatedToolCalls.delete(key);
                exports.stateTimestamps.translatedCalls.delete(key);
            }
        }
        for (const [key, ts] of exports.stateTimestamps.reasoning) {
            if (now - ts > TOOL_TTL) {
                exports.modelReasoningContent.delete(key);
                exports.stateTimestamps.reasoning.delete(key);
            }
        }
    }, 300000);
    // Importing translator/model-management helpers must not keep a CLI process alive.
    cleanupInterval.unref?.();
}
function stopCleanupInterval() {
    if (cleanupInterval) {
        clearInterval(cleanupInterval);
        cleanupInterval = null;
    }
}
// Auto-start for backward compatibility (will be replaced by proxy.ts lifecycle)
startCleanupInterval();
const officialQuotas = new Map();
const OFFICIAL_QUOTA_TTL = 10 * 60000;
const OFFICIAL_QUOTA_CAPACITY = 128;
function officialQuotaScopeKey(scope) {
    const endpoint = new URL(scope.endpoint);
    const local = ['localhost', '127.0.0.1', '[::1]'].includes(endpoint.hostname);
    if (!scope.accountId ||
        [scope.accountId, scope.clientId, scope.project].some((value) => value !== undefined && (typeof value !== 'string' || value.length > 4096)) ||
        endpoint.username ||
        endpoint.password ||
        (!local &&
            (endpoint.protocol !== 'https:' ||
                !['cloudcode-pa.googleapis.com', 'daily-cloudcode-pa.googleapis.com'].includes(endpoint.hostname))) ||
        !['http:', 'https:'].includes(endpoint.protocol))
        throw new Error('Invalid quota scope');
    return JSON.stringify([scope.accountId, scope.clientId || '', scope.project || '', endpoint.origin]);
}
function recordOfficialQuota(data, scope, checkedAt = Date.now()) {
    const now = Date.now();
    if (!data ||
        typeof data !== 'object' ||
        Array.isArray(data) ||
        !Number.isFinite(checkedAt) ||
        checkedAt > now ||
        now - checkedAt >= OFFICIAL_QUOTA_TTL)
        return;
    const key = officialQuotaScopeKey(scope);
    // Keep only fields consumed by the quota parser; never retain an echoed request or credentials.
    const clean = {};
    let remainingBuckets = 256;
    const bucket = (value) => {
        if (!value || typeof value !== 'object' || remainingBuckets-- <= 0)
            return undefined;
        const source = value;
        const result = {};
        for (const field of ['bucketId', 'id', 'modelId', 'displayName', 'title', 'label', 'resetTime']) {
            if (typeof source[field] === 'string')
                result[field] = source[field].slice(0, 512);
        }
        if (typeof source.remainingFraction === 'number' && Number.isFinite(source.remainingFraction))
            result.remainingFraction = Math.max(0, Math.min(1, source.remainingFraction));
        return result;
    };
    if (Array.isArray(data.buckets))
        clean.buckets = data.buckets.slice(0, 256).map(bucket).filter(Boolean);
    if (Array.isArray(data.groups))
        clean.groups = data.groups.slice(0, 64).flatMap((value) => {
            if (!value || typeof value !== 'object')
                return [];
            const source = value;
            const group = {};
            for (const field of ['name', 'displayName', 'title', 'label', 'id'])
                if (typeof source[field] === 'string')
                    group[field] = source[field].slice(0, 512);
            group.buckets = Array.isArray(source.buckets) ? source.buckets.slice(0, 256).map(bucket).filter(Boolean) : [];
            return [group];
        });
    for (const field of ['subscriptionTier', 'userTier', 'planTier'])
        if (typeof data[field] === 'string')
            clean[field] = data[field].slice(0, 128);
    if (data.paidTier &&
        typeof data.paidTier === 'object' &&
        typeof data.paidTier.tier === 'string')
        clean.paidTier = { tier: data.paidTier.tier.slice(0, 128) };
    if (Buffer.byteLength(JSON.stringify(clean), 'utf8') > 128 * 1024)
        return;
    for (const [storedKey, entry] of officialQuotas)
        if (now < entry.checkedAt || now - entry.checkedAt >= OFFICIAL_QUOTA_TTL)
            officialQuotas.delete(storedKey);
    if ((officialQuotas.get(key)?.checkedAt ?? -1) > checkedAt)
        return;
    officialQuotas.delete(key);
    officialQuotas.set(key, { scope: { ...scope }, checkedAt, data: clean });
    while (officialQuotas.size > OFFICIAL_QUOTA_CAPACITY)
        officialQuotas.delete(officialQuotas.keys().next().value);
}
function getOfficialQuota(scope) {
    const key = officialQuotaScopeKey(scope);
    const entry = officialQuotas.get(key);
    if (!entry)
        return undefined;
    if (Date.now() < entry.checkedAt || Date.now() - entry.checkedAt >= OFFICIAL_QUOTA_TTL) {
        officialQuotas.delete(key);
        return undefined;
    }
    return JSON.parse(JSON.stringify(entry));
}
function clearOfficialQuota(accountId) {
    for (const [key, entry] of officialQuotas)
        if (!accountId || entry.scope.accountId === accountId)
            officialQuotas.delete(key);
}
//# sourceMappingURL=shared.js.map