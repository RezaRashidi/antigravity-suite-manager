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
exports.CloudCodeRouting = exports.fetchCloudCodeTier = void 0;
const node_crypto_1 = require("node:crypto");
const https = __importStar(require("node:https"));
const node_zlib_1 = require("node:zlib");
const PRODUCTION = 'https://cloudcode-pa.googleapis.com';
const DAILY = 'https://daily-cloudcode-pa.googleapis.com';
const MAX_CALLERS = 128;
const TIER_TTL_MS = 60 * 60 * 1000;
const MAX_TIER_BYTES = 512 * 1024;
const LOOKUP_TIMEOUT_MS = 5000;
/** Read account routing with the same identity/project; never replay a generation. */
const fetchCloudCodeTier = (headers, body, signal) => new Promise((resolve, reject) => {
    let project;
    try {
        const envelope = JSON.parse(body.toString('utf8'));
        if (typeof envelope?.project === 'string' && envelope.project.length <= 1024)
            project = envelope.project;
    }
    catch {
        // Generation validation remains the upstream's responsibility.
    }
    const userAgent = headers['user-agent'];
    const version = typeof userAgent === 'string' ? /antigravity\/([\d.]+)/i.exec(userAgent)?.[1] : undefined;
    const payload = Buffer.from(JSON.stringify({
        metadata: { ideName: 'antigravity', ideType: 'ANTIGRAVITY', ...(version ? { ideVersion: version } : {}) },
        ...(project ? { cloudaicompanionProject: project } : {}),
    }));
    const forwarded = {
        'content-type': 'application/json',
        'content-length': String(payload.length),
        'accept-encoding': 'identity',
    };
    for (const name of ['authorization', 'user-agent', 'x-goog-user-project', 'x-goog-api-client']) {
        if (typeof headers[name] === 'string')
            forwarded[name] = headers[name];
    }
    const request = https.request(`${PRODUCTION}/v1internal:loadCodeAssist`, { method: 'POST', headers: forwarded, signal }, (response) => {
        const chunks = [];
        let length = 0;
        response.on('error', reject);
        response.on('aborted', () => reject(new Error('Cloud Code tier lookup was interrupted.')));
        response.on('data', (chunk) => {
            length += chunk.length;
            if (length > MAX_TIER_BYTES)
                request.destroy(new Error('Cloud Code tier response exceeded the size limit.'));
            else
                chunks.push(chunk);
        });
        response.on('end', () => {
            try {
                let bytes = Buffer.concat(chunks);
                const encoding = String(response.headers['content-encoding'] || 'identity').toLowerCase();
                if (encoding === 'gzip')
                    bytes = (0, node_zlib_1.gunzipSync)(bytes, { maxOutputLength: MAX_TIER_BYTES });
                else if (encoding === 'deflate')
                    bytes = (0, node_zlib_1.inflateSync)(bytes, { maxOutputLength: MAX_TIER_BYTES });
                else if (encoding === 'br')
                    bytes = (0, node_zlib_1.brotliDecompressSync)(bytes, { maxOutputLength: MAX_TIER_BYTES });
                else if (encoding !== 'identity')
                    throw new Error('Unsupported tier response encoding.');
                resolve({ status: response.statusCode || 500, body: JSON.parse(bytes.toString('utf8')) });
            }
            catch {
                reject(new Error('Cloud Code tier lookup returned an unreadable response.'));
            }
        });
    });
    // A wall-clock limit also bounds slow trickle responses, not only idle sockets.
    const timeout = setTimeout(() => request.destroy(new Error('Cloud Code tier lookup timed out.')), LOOKUP_TIMEOUT_MS);
    request.once('close', () => clearTimeout(timeout));
    request.once('error', reject);
    request.end(payload);
});
exports.fetchCloudCodeTier = fetchCloudCodeTier;
function callerKey(headers) {
    const authorization = headers.authorization;
    if (typeof authorization !== 'string' || authorization.length > 16384)
        return undefined;
    const bearer = /^Bearer[\t ]+(\S+)[\t ]*$/i.exec(authorization);
    return bearer ? (0, node_crypto_1.createHash)('sha256').update(bearer[1]).digest('hex') : undefined;
}
function object(value) {
    return !!value && typeof value === 'object' && !Array.isArray(value);
}
/**
 * Antigravity IDE 2.5.5 uses production Cloud Code until loadCodeAssist reveals
 * the account tier, then moves non-GCP tiers to daily Cloud Code. A loopback
 * setting masks that native URL switch, so the IDE service preserves it here.
 * Cache entries contain only an irreversible bearer digest and routing state.
 */
class CloudCodeRouting {
    constructor(now = Date.now, lookup = exports.fetchCloudCodeTier) {
        this.now = now;
        this.lookup = lookup;
        this.callers = new Map();
        this.pending = new Map();
    }
    expire() {
        const now = this.now();
        for (const [key, route] of this.callers)
            if (route.expiresAt <= now)
                this.callers.delete(key);
    }
    resolve(headers) {
        this.expire();
        const key = callerKey(headers);
        const route = key ? this.callers.get(key) : undefined;
        if (!key || !route)
            return PRODUCTION;
        // Refresh recency for bounded eviction without extending the tier TTL.
        this.callers.delete(key);
        this.callers.set(key, route);
        return route.origin;
    }
    async resolveForGeneration(headers, body, signal) {
        if (signal.aborted)
            throw new Error('Cloud Code routing request was cancelled.');
        this.expire();
        const key = callerKey(headers);
        if (!key || this.callers.has(key))
            return this.resolve(headers);
        let pending = this.pending.get(key);
        if (!pending) {
            if (this.pending.size >= MAX_CALLERS)
                throw new Error('Too many pending Cloud Code tier lookups.');
            const controller = new AbortController();
            pending = { controller, waiters: 0, promise: Promise.resolve() };
            const current = pending;
            current.promise = this.lookup(headers, body, controller.signal)
                .then((result) => {
                if (controller.signal.aborted)
                    throw new Error('Cloud Code tier lookup was cancelled.');
                this.observe(headers, result.status, result.body);
                if (!this.callers.has(key))
                    throw new Error('Cloud Code tier lookup did not establish account routing.');
            })
                .finally(() => {
                if (this.pending.get(key) === current)
                    this.pending.delete(key);
            });
            this.pending.set(key, current);
        }
        const current = pending;
        current.waiters++;
        try {
            await new Promise((resolve, reject) => {
                const abort = () => reject(new Error('Cloud Code routing request was cancelled.'));
                signal.addEventListener('abort', abort, { once: true });
                current.promise.then(resolve, reject).finally(() => signal.removeEventListener('abort', abort));
                if (signal.aborted)
                    abort();
            });
            return this.resolve(headers);
        }
        finally {
            current.waiters--;
            if (!current.waiters && this.pending.get(key) === current) {
                this.pending.delete(key);
                current.controller.abort();
            }
        }
    }
    observe(headers, status, response) {
        if (!Number.isInteger(status) || status < 200 || status >= 300 || !object(response))
            return;
        const key = callerKey(headers);
        if (!key)
            return;
        const tier = response.paidTier ?? response.paid_tier;
        if (tier !== undefined && tier !== null && !object(tier))
            return;
        const usesGcpTos = object(tier) ? (tier.usesGcpTos ?? tier.uses_gcp_tos) : undefined;
        if (usesGcpTos !== undefined && usesGcpTos !== null && typeof usesGcpTos !== 'boolean')
            return;
        this.expire();
        this.callers.delete(key);
        this.callers.set(key, { origin: usesGcpTos === true ? PRODUCTION : DAILY, expiresAt: this.now() + TIER_TTL_MS });
        while (this.callers.size > MAX_CALLERS)
            this.callers.delete(this.callers.keys().next().value);
    }
    clear() {
        for (const lookup of this.pending.values())
            lookup.controller.abort();
        this.pending.clear();
        this.callers.clear();
    }
}
exports.CloudCodeRouting = CloudCodeRouting;
//# sourceMappingURL=cloudCodeRouting.js.map