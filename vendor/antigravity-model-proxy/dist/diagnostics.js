"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.beginDiagnosticRequest = beginDiagnosticRequest;
exports.getDiagnostics = getDiagnostics;
exports.getRecentModelNames = getRecentModelNames;
exports.clearDiagnostics = clearDiagnostics;
/** Process-local, bounded diagnostics. No prompts, response text, URLs or credentials are retained. */
const node_crypto_1 = require("node:crypto");
const MAX_REQUESTS = 200;
const requests = [];
let epoch = 0;
let active = 0;
let startedAt = Date.now();
const label = (value) => String(value)
    .replace(/[\x00-\x1f\x7f]/g, '')
    .slice(0, 160);
const count = (value) => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : undefined;
const object = (value) => value && typeof value === 'object' && !Array.isArray(value) ? value : {};
function beginDiagnosticRequest(input) {
    const timestamp = Date.now();
    const requestEpoch = epoch;
    const usage = {};
    let finished = false;
    active += 1;
    const update = (key, value) => {
        const measured = count(value);
        if (measured !== undefined)
            usage[key] = Math.max(usage[key] ?? 0, measured);
    };
    return {
        /** Usage belongs to the final attempted provider/model, not a sum of retry billing. */
        resetUsage() {
            if (finished)
                return;
            delete usage.inputTokens;
            delete usage.outputTokens;
            delete usage.cachedTokens;
        },
        observe(value, format) {
            if (finished || !value || typeof value !== 'object')
                return;
            const raw = object(value);
            const data = raw.response && typeof raw.response === 'object' ? object(raw.response) : raw;
            if (format === 'openai') {
                const u = object(data.usage);
                update('inputTokens', u.prompt_tokens);
                update('outputTokens', u.completion_tokens);
                update('cachedTokens', object(u.prompt_tokens_details).cached_tokens);
            }
            else if (format === 'anthropic') {
                const u = object(data.usage || object(data.message).usage);
                const uncached = count(u.input_tokens);
                if (uncached !== undefined)
                    update('inputTokens', uncached + (count(u.cache_read_input_tokens) ?? 0) + (count(u.cache_creation_input_tokens) ?? 0));
                update('outputTokens', u.output_tokens);
                update('cachedTokens', u.cache_read_input_tokens);
            }
            else {
                const u = object(data.usageMetadata);
                update('inputTokens', u.promptTokenCount);
                update('outputTokens', u.candidatesTokenCount);
                update('cachedTokens', u.cachedContentTokenCount);
            }
        },
        finish(result) {
            if (finished)
                return;
            finished = true;
            active = Math.max(0, active - 1);
            if (requestEpoch !== epoch)
                return;
            const status = count(result.status);
            requests.unshift({
                id: (0, node_crypto_1.randomUUID)(),
                timestamp,
                model: label(result.model ?? input.model),
                provider: label(result.provider ?? input.provider),
                stream: input.stream,
                kind: input.kind || 'request',
                outcome: result.outcome,
                ...(status !== undefined && status >= 100 && status <= 599 ? { status } : {}),
                latencyMs: Math.max(0, Date.now() - timestamp),
                ...usage,
            });
            requests.length = Math.min(requests.length, MAX_REQUESTS);
        },
    };
}
function getDiagnostics() {
    const recentModels = getRecentModelNames();
    const total = (key) => requests.reduce((sum, r) => sum + (r[key] ?? 0), 0);
    return {
        success: true,
        startedAt,
        active,
        capacity: MAX_REQUESTS,
        summary: {
            requests: requests.length,
            succeeded: requests.filter((r) => r.outcome === 'succeeded').length,
            failed: requests.filter((r) => r.outcome === 'failed').length,
            cancelled: requests.filter((r) => r.outcome === 'cancelled').length,
            measuredRequests: requests.filter((r) => r.inputTokens !== undefined || r.outputTokens !== undefined).length,
            measuredInputRequests: requests.filter((r) => r.inputTokens !== undefined).length,
            measuredOutputRequests: requests.filter((r) => r.outputTokens !== undefined).length,
            measuredCachedRequests: requests.filter((r) => r.cachedTokens !== undefined).length,
            inputTokens: total('inputTokens'),
            outputTokens: total('outputTokens'),
            cachedTokens: total('cachedTokens'),
        },
        recentModels,
        requests: requests.map((r) => ({ ...r })),
    };
}
function getRecentModelNames() {
    return [
        ...new Set(requests.filter((r) => r.outcome === 'succeeded' && r.kind === 'request').map((r) => r.model)),
    ].slice(0, 5);
}
function clearDiagnostics() {
    epoch += 1;
    requests.length = 0;
    startedAt = Date.now();
    return { success: true };
}
//# sourceMappingURL=diagnostics.js.map