"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveGoogleFailoverPool = resolveGoogleFailoverPool;
exports.isGoogleQuotaFailure = isGoogleQuotaFailure;
exports.attemptGooglePoolFailover = attemptGooglePoolFailover;
const http = __importStar(require("node:http"));
const https = __importStar(require("node:https"));
const googleAccounts_1 = require("../googleAccounts");
const googlePoolPolicy_1 = require("../googlePoolPolicy");
const nativeSubagentResponse_1 = require("./nativeSubagentResponse");
const ERROR_LIMIT = 64 * 1024;
function parsedRequest(body) {
    try {
        const value = JSON.parse(body.toString('utf8'));
        return value && typeof value === 'object' && !Array.isArray(value) ? value : undefined;
    }
    catch {
        return undefined;
    }
}
/** No global credential aggregation: only one explicitly opted-in matching model is eligible. */
function resolveGoogleFailoverPool(models, body) {
    const parsed = parsedRequest(body);
    if (typeof parsed?.model !== 'string')
        return undefined;
    const upstream = parsed.model.replace(/^models\//, '');
    const matches = models.filter((model) => model.enabled !== false &&
        model.provider === 'google-cloudcode' &&
        model.googlePool?.nativeFailoverEnabled === true &&
        (model.externalModelName || model.name).replace(/^models\//, '') === upstream &&
        model.googleAccounts?.some((account) => account.enabled !== false));
    // Even similar pools may have different projects or policies. Let the user choose one explicitly.
    return matches.length === 1 ? matches[0] : undefined;
}
/** HTTP 400/403 require a structured, explicit Google rate-limit diagnosis. */
function isGoogleQuotaFailure(status, body) {
    if (status === 429)
        return true;
    if (status !== 400 && status !== 403)
        return false;
    try {
        const value = JSON.parse(body);
        const error = value?.error || value;
        if (error?.status === 'RESOURCE_EXHAUSTED')
            return true;
        return (Array.isArray(error?.details) &&
            error.details.some((detail) => detail?.['@type'] === 'type.googleapis.com/google.rpc.ErrorInfo' &&
                typeof detail.reason === 'string' &&
                /^(?:RATE_LIMIT_EXCEEDED|QUOTA_EXCEEDED|QUOTA_EXHAUSTED|DAILY_LIMIT_EXCEEDED|WEEKLY_LIMIT_EXCEEDED)$/.test(detail.reason)));
    }
    catch {
        return false;
    }
}
/** Retry matching native Google requests only before downstream response headers are sent. */
async function attemptGooglePoolFailover(req, res, reqBody, errorRes, errorBody, options, nativeSubagent, cloudCodeOrigin = 'https://daily-cloudcode-pa.googleapis.com') {
    const unavailable = () => res.destroyed || res.writableEnded || options.isStopping?.();
    if (unavailable())
        return true;
    // Public Gemini and Cloud Code use different request/response envelopes. Only native
    // Cloud Code requests can be replayed without a complete protocol adapter.
    if (!/^\/v1internal:(?:streamGenerateContent|generateContent)(?:\?|$)/.test(req.url || ''))
        return false;
    if (!isGoogleQuotaFailure(errorRes.statusCode || 500, errorBody))
        return false;
    const pool = resolveGoogleFailoverPool(options.loadCustomModels(), reqBody);
    const body = parsedRequest(reqBody);
    if (!pool || !body || typeof body.model !== 'string')
        return false;
    const upstreamModel = body.model.replace(/^models\//, '');
    const originalToken = String(req.headers.authorization || '')
        .replace(/^Bearer\s+/i, '')
        .trim();
    const failingAccount = pool.googleAccounts.find((account) => account.accessToken === originalToken);
    const decision = (0, googlePoolPolicy_1.classifyGoogleRateLimit)(errorBody, errorRes.headers['retry-after']);
    if (failingAccount)
        (0, googleAccounts_1.recordGoogleAccountFailure)({
            ...failingAccount,
            project: typeof body.project === 'string' ? body.project : undefined,
            cloudCodeEndpoint: undefined,
        }, errorRes.statusCode, decision.retryAfterMs ?? pool.googlePool?.cooldownMs, upstreamModel, decision.reason, cloudCodeOrigin);
    let candidates = pool.googleAccounts.filter((account) => account.enabled !== false && account.id !== failingAccount?.id);
    if (!candidates.length)
        return false;
    const identity = typeof body.sessionId === 'string'
        ? body.sessionId
        : typeof body.conversationId === 'string'
            ? body.conversationId
            : undefined;
    const controller = new AbortController();
    const cancel = () => {
        if (!res.writableFinished)
            controller.abort();
    };
    res.once('close', cancel);
    const timeout = setTimeout(() => controller.abort(), options.timeoutMs ?? pool.retryBudgetMs ?? pool.timeout ?? 60000);
    let abandonAcquire;
    try {
        const maximum = Math.min(3, candidates.length);
        for (let attempt = 0; attempt < maximum && candidates.length; attempt++) {
            if (unavailable() || controller.signal.aborted)
                return !!unavailable();
            let lease;
            // Refresh can be shared by other requests. Cancel our waiter without cancelling their refresh.
            try {
                lease = await new Promise((resolve, reject) => {
                    let abandoned = false;
                    const cancelAcquire = () => {
                        abandoned = true;
                        resolve(undefined);
                    };
                    abandonAcquire = cancelAcquire;
                    controller.signal.addEventListener('abort', cancelAcquire, { once: true });
                    void (0, googleAccounts_1.acquireGoogleAccount)(pool.name, candidates, pool.googlePool, identity, upstreamModel, pool.apiUrl || cloudCodeOrigin).then((value) => {
                        controller.signal.removeEventListener('abort', cancelAcquire);
                        if (abandoned || unavailable() || controller.signal.aborted) {
                            value.release({ cancelled: true });
                            resolve(undefined);
                        }
                        else
                            resolve(value);
                    }, (error) => {
                        controller.signal.removeEventListener('abort', cancelAcquire);
                        reject(error);
                    });
                });
            }
            catch {
                return false;
            }
            finally {
                abandonAcquire = undefined;
            }
            if (!lease)
                return !!unavailable();
            if (unavailable() || controller.signal.aborted) {
                lease.release({ cancelled: true });
                return !!unavailable();
            }
            let target;
            let retryBody;
            let headers;
            try {
                const origin = (0, googleAccounts_1.googleAccountEndpoint)(lease.account, pool.apiUrl || cloudCodeOrigin);
                target = new URL(req.url || '', origin);
                if (target.origin !== new URL(origin).origin ||
                    !/^\/v1internal:(?:streamGenerateContent|generateContent)$/.test(target.pathname))
                    throw new Error('Unsupported native generation path');
                headers = options.forwardingHeaders(req.headers);
                headers.host = target.host;
                headers.authorization = `Bearer ${lease.account.accessToken}`;
                // Never carry the original account's billing project into another account.
                delete headers['x-goog-user-project'];
                const cloned = { ...body };
                delete cloned.project;
                if (lease.account.project) {
                    cloned.project = lease.account.project;
                    headers['x-goog-user-project'] = lease.account.project;
                }
                retryBody = Buffer.from(JSON.stringify(cloned));
                headers['content-length'] = String(retryBody.length);
                headers['accept-encoding'] = 'identity';
            }
            catch {
                lease.release({ cancelled: true });
                return false;
            }
            const selectedLease = lease;
            const started = Date.now();
            const handled = await new Promise((resolve) => {
                let settled = false;
                let request;
                let response;
                const finish = (handled, result) => {
                    if (settled)
                        return;
                    settled = true;
                    controller.signal.removeEventListener('abort', abort);
                    selectedLease.release(result);
                    resolve(handled);
                };
                const fail = () => {
                    if (settled)
                        return;
                    const sent = res.headersSent;
                    finish(sent || !!unavailable(), { status: 502, cancelled: !!unavailable() });
                    if (sent && !res.destroyed && !res.writableEnded)
                        res.destroy();
                    response?.destroy();
                    request?.destroy();
                };
                const abort = () => {
                    if (settled)
                        return;
                    const sent = res.headersSent;
                    finish(sent || !!unavailable(), { cancelled: true });
                    if (sent && !res.destroyed && !res.writableEnded)
                        res.destroy();
                    response?.destroy();
                    request?.destroy();
                };
                controller.signal.addEventListener('abort', abort, { once: true });
                try {
                    request = (options.requestFn || (target.protocol === 'http:' ? http.request : https.request))(target, { method: req.method, headers }, (upstream) => {
                        response = upstream;
                        if (settled || unavailable() || controller.signal.aborted) {
                            abort();
                            upstream.destroy();
                            return;
                        }
                        upstream.once('error', fail);
                        upstream.once('aborted', fail);
                        upstream.once('close', () => {
                            if (!upstream.complete)
                                fail();
                        });
                        const status = upstream.statusCode || 502;
                        if ([400, 401, 403, 408, 429].includes(status) || status >= 500) {
                            const chunks = [];
                            let size = 0;
                            upstream.on('data', (chunk) => {
                                size += chunk.length;
                                if (size > ERROR_LIMIT)
                                    fail();
                                else
                                    chunks.push(chunk);
                            });
                            upstream.once('end', () => {
                                const text = Buffer.concat(chunks).toString('utf8');
                                const limited = isGoogleQuotaFailure(status, text);
                                const limit = limited ? (0, googlePoolPolicy_1.classifyGoogleRateLimit)(text, upstream.headers['retry-after']) : undefined;
                                if (status === 400 && !limited) {
                                    res.writeHead(status, options.forwardingHeaders(upstream.headers));
                                    res.end(Buffer.concat(chunks));
                                    finish(true, { status });
                                    return;
                                }
                                finish(false, { status, retryAfterMs: limit?.retryAfterMs, cooldownReason: limit?.reason });
                            });
                            return;
                        }
                        const success = () => finish(true, { status, latencyMs: Date.now() - started });
                        if (nativeSubagent) {
                            void (0, nativeSubagentResponse_1.forwardNativeGeneration)(upstream, res, nativeSubagent, target.pathname.includes('streamGenerateContent') || target.searchParams.get('alt') === 'sse').then(success, fail);
                        }
                        else {
                            upstream.once('end', success);
                            res.writeHead(status, options.forwardingHeaders(upstream.headers));
                            upstream.pipe(res);
                        }
                    });
                    request.once('error', fail);
                    request.once('close', () => {
                        if (!response || !response.complete)
                            fail();
                    });
                    options.trackUpstream?.(request);
                    if (controller.signal.aborted || unavailable())
                        abort();
                    if (!settled)
                        request.end(retryBody);
                }
                catch {
                    fail();
                }
            });
            if (handled)
                return true;
            candidates = candidates.filter((account) => account.id !== selectedLease.account.id);
        }
        return false;
    }
    finally {
        clearTimeout(timeout);
        res.off('close', cancel);
        abandonAcquire?.();
    }
}
//# sourceMappingURL=googlePoolFailover.js.map