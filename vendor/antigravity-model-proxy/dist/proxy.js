"use strict";
/**
 * Antigravity Local Proxy Server.
 * Routes requests to Google, OpenAI, Anthropic, Ollama, and custom provider endpoints.
 * Intercepts model lists to inject user-defined custom models.
 */
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.startProxy = startProxy;
exports.stopProxy = stopProxy;
exports.getProxyPort = getProxyPort;
const http = __importStar(require("http"));
const https = __importStar(require("https"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const electron_1 = require("electron");
const electron_log_1 = __importDefault(require("electron-log"));
// ─── Imports ──────────────────────────────────────────────────────────────
let server = null;
let proxyPort = 0;
let startingProxy = null;
let stoppingProxy = null;
// Shared cross-turn state
const shared_1 = require("./proxy/shared");
// Model configuration & capability detection
const modelUtils_1 = require("./proxy/modelUtils");
// Custom request transport and model storage
const customRequest_1 = require("./proxy/customRequest");
const modelStore_1 = require("./modelStore");
const listen_1 = require("./proxy/listen");
const proxyAgent_1 = require("./proxy/proxyAgent");
// Dynamic imports (stays require for Electron-specific modules)
// eslint-disable-next-line @typescript-eslint/no-var-requires
const cryptoStore = require('./cryptoStore');
// ─── Model Helpers ────────────────────────────────────────────────────────
function generateModelPlaceholderId(model) {
    const input = (model.displayName || model.name || 'custom-model').toLowerCase();
    let hash = 5381;
    for (let i = 0; i < input.length; i++) {
        hash = (hash << 5) + hash + input.charCodeAt(i);
        hash = hash & hash; // Force 32-bit integer
    }
    const placeholderNum = 400 + (Math.abs(hash) % 200);
    return `MODEL_PLACEHOLDER_M${placeholderNum}`;
}
function getCustomModelsPath() {
    const geminiDir = path.join(electron_1.app.getPath('home'), '.gemini', 'antigravity');
    return path.join(geminiDir, 'custom_models.json');
}
function toSlug(model) {
    return ('custom-' +
        (model.externalModelName || model.name)
            .replace(/^models\//, '')
            .replace(/[^a-zA-Z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '')
            .toLowerCase());
}
// ─── Model Loading ────────────────────────────────────────────────────────
function loadCustomModels() {
    const filePath = getCustomModelsPath();
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { validateCustomModel } = require('./schemaValidator');
    if (!fs.existsSync(filePath)) {
        const defaultModels = {
            models: [
                {
                    name: 'models/gpt-4o',
                    displayName: 'GPT-4o (OpenAI via Proxy)',
                    description: 'OpenAI GPT-4o model redirected through proxy',
                    provider: 'openai',
                    apiKey: process.env.OPENAI_API_KEY || 'YOUR_OPENAI_API_KEY',
                    apiUrl: 'https://api.openai.com/v1/chat/completions',
                    externalModelName: 'gpt-4o',
                },
                {
                    name: 'models/claude-3-5-sonnet',
                    displayName: 'Claude 3.5 Sonnet (Anthropic via Proxy)',
                    description: 'Anthropic Claude 3.5 Sonnet model redirected through proxy',
                    provider: 'anthropic',
                    apiKey: process.env.ANTHROPIC_API_KEY || 'YOUR_ANTHROPIC_API_KEY',
                    apiUrl: 'https://api.anthropic.com/v1/messages',
                    externalModelName: 'claude-3-5-sonnet-latest',
                },
                {
                    name: 'models/llama3',
                    displayName: 'Llama 3 (Local Ollama)',
                    description: 'Local Ollama Llama 3 model run on your machine',
                    provider: 'ollama',
                    apiUrl: 'http://localhost:11434/v1/chat/completions',
                    externalModelName: 'llama3',
                },
            ],
        };
        try {
            fs.mkdirSync(path.dirname(filePath), { recursive: true });
            defaultModels.models.forEach((m) => {
                m.encrypted = false;
            });
            const encrypted = cryptoStore.encryptModels(defaultModels.models);
            fs.writeFileSync(filePath, JSON.stringify({ models: encrypted }, null, 2), 'utf-8');
        }
        catch (e) {
            electron_log_1.default.error('[Proxy] Failed to write default custom_models.json', e);
        }
        return cryptoStore.decryptModels(defaultModels.models);
    }
    try {
        const models = (0, modelStore_1.readModelConfig)(filePath);
        // Auto-migration check
        const unprotected = (value) => typeof value === 'string' && value && value !== 'none' && !/^(enc:|fallback:|local-gcm:)/.test(value);
        const needsMigration = models.some((m) => (!m.encrypted && unprotected(m.apiKey)) ||
            (!m.encryptedHeaders && Object.values(m.customHeaders || {}).some(unprotected)) ||
            (!m.encryptedGoogleAccounts && (m.googleAccounts || []).some((account) => [account.accessToken, account.refreshToken, account.clientSecret].some(unprotected))));
        if (needsMigration) {
            electron_log_1.default.info('[Proxy] Plaintext custom_models.json detected. Migrating to encrypted format...');
            cryptoStore.backupFile(filePath);
            const encryptedModels = cryptoStore.encryptModels(models);
            for (const model of encryptedModels) {
                if (model.customHeaders && !model.encryptedHeaders) {
                    model.customHeaders = Object.fromEntries(Object.entries(model.customHeaders).map(([name, value]) => [name, unprotected(value) ? cryptoStore.encryptString(value) : value]));
                    model.encryptedHeaders = true;
                }
                if (model.googleAccounts && !model.encryptedGoogleAccounts) {
                    model.googleAccounts = model.googleAccounts.map((account) => {
                        const encrypted = { ...account };
                        for (const field of ['accessToken', 'refreshToken', 'clientSecret'])
                            if (unprotected(encrypted[field]))
                                encrypted[field] = cryptoStore.encryptString(encrypted[field]);
                        return encrypted;
                    });
                    model.encryptedGoogleAccounts = true;
                }
            }
            try {
                (0, modelStore_1.writeJsonAtomic)(filePath, { models: encryptedModels });
                electron_log_1.default.info('[Proxy] Successfully migrated custom_models.json to encrypted format.');
                // Continue through validation and enabled filtering below.
            }
            catch (err) {
                electron_log_1.default.error('[Proxy] Failed to write encrypted custom_models.json during migration:', err);
            }
        }
        const decrypted = cryptoStore.decryptModels(models);
        for (const model of decrypted) {
            if (/^(DECRYPTION_FAILED|enc:|fallback:|local-gcm:)/.test(model.apiKey || '')) {
                model.enabled = false;
                electron_log_1.default.warn('[Proxy] Skipping a model whose API key could not be decrypted');
                continue;
            }
            if (model.googleAccounts) {
                model.googleAccounts = model.googleAccounts.flatMap((account) => {
                    const decryptedAccount = { ...account };
                    for (const field of ['accessToken', 'refreshToken', 'clientSecret']) {
                        const value = decryptedAccount[field];
                        if (!value)
                            continue;
                        if (model.encryptedGoogleAccounts)
                            decryptedAccount[field] = cryptoStore.decryptString(value);
                        if (/^(DECRYPTION_FAILED|enc:|fallback:|local-gcm:)/.test(decryptedAccount[field] || '')) {
                            electron_log_1.default.warn('[Proxy] Skipping a Google account whose credentials could not be decrypted');
                            return [];
                        }
                    }
                    return [decryptedAccount];
                });
                model.encryptedGoogleAccounts = false;
            }
            if (model.encryptedHeaders && model.customHeaders) {
                model.customHeaders = Object.fromEntries(Object.entries(model.customHeaders).map(([key, value]) => {
                    const decryptedHeader = cryptoStore.decryptString(value);
                    if (/^(DECRYPTION_FAILED|enc:|fallback:|local-gcm:)/.test(decryptedHeader || '')) {
                        model.enabled = false;
                        electron_log_1.default.warn('[Proxy] Skipping a model whose custom header could not be decrypted');
                    }
                    return [key, decryptedHeader];
                }));
                model.encryptedHeaders = false;
            }
        }
        // Validate all models
        const validModels = [];
        for (let i = 0; i < decrypted.length; i++) {
            const validation = validateCustomModel(decrypted[i]);
            if (validation.valid) {
                if (decrypted[i].enabled !== false)
                    validModels.push(decrypted[i]);
            }
            else {
                electron_log_1.default.warn(`[Proxy] Skipping invalid model at index ${i}: ${validation.error}`);
            }
        }
        if (validModels.length < decrypted.length) {
            electron_log_1.default.info(`[Proxy] Loaded ${validModels.length}/${decrypted.length} valid models (${decrypted.length - validModels.length} skipped)`);
        }
        return validModels;
    }
    catch (e) {
        electron_log_1.default.error('[Proxy] Failed to parse custom_models.json', e);
        return [];
    }
}
// ─── Google Proxy ─────────────────────────────────────────────────────────
function proxyToGoogle(req, res, reqBody) {
    const isCloudCodeUrl = req.url.includes('v1internal') || req.url.includes('daily-cloudcode');
    const targetUrl = isCloudCodeUrl
        ? 'https://daily-cloudcode-pa.googleapis.com'
        : 'https://generativelanguage.googleapis.com';
    const parsedUrl = new URL(req.url, targetUrl);
    const headers = {
        ...req.headers,
    };
    headers['host'] = isCloudCodeUrl ? 'daily-cloudcode-pa.googleapis.com' : 'generativelanguage.googleapis.com';
    delete headers['connection'];
    delete headers['keep-alive'];
    const isGeneration = req.url.includes('generateContent') || req.url.includes('streamGenerateContent');
    const shouldBufferAndModify = isCloudCodeUrl && !isGeneration;
    if (shouldBufferAndModify) {
        delete headers['accept-encoding'];
    }
    const options = {
        method: req.method,
        headers: headers,
        agent: (0, proxyAgent_1.getProxyAgent)(),
    };
    const proxyReq = https.request(parsedUrl, options, (proxyRes) => {
        // P0-5: Timeout for Google proxy requests (60s)
        proxyReq.setTimeout(60000, () => {
            electron_log_1.default.error('[Proxy] Google proxy request timed out after 60s');
            proxyReq.destroy();
            if (!res.headersSent) {
                res.writeHead(504, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: { message: 'Google API request timed out' } }));
            }
        });
        if (shouldBufferAndModify) {
            const responseChunks = [];
            proxyRes.on('data', (chunk) => responseChunks.push(chunk));
            proxyRes.on('end', () => {
                const fullResBody = Buffer.concat(responseChunks);
                let text;
                const encoding = proxyRes.headers['content-encoding'];
                if (encoding === 'gzip') {
                    try {
                        const zlib = require('zlib');
                        text = zlib.gunzipSync(fullResBody).toString('utf-8');
                    }
                    catch (e) {
                        electron_log_1.default.error('[Proxy] gunzipSync failed:', e);
                        text = fullResBody.toString('utf-8');
                    }
                }
                else {
                    text = fullResBody.toString('utf-8');
                }
                electron_log_1.default.info(`[Proxy] Response for ${req.url} (status: ${proxyRes.statusCode}, encoding: ${encoding}, length: ${text.length})`);
                // P0-3: Response body content is NOT logged to disk. Only metadata.
                const proxyHost = req.headers.host || 'localhost';
                text = text.replace(/https:(\/\/)daily-cloudcode-pa\.googleapis\.com/g, `http:$1${proxyHost}`);
                text = text.replace(/https:(\/\/)cloudcode-pa\.googleapis\.com/g, `http:$1${proxyHost}`);
                text = text.replace(/https:(\/\/)generativelanguage\.googleapis\.com/g, `http:$1${proxyHost}`);
                const modifiedHeaders = { ...proxyRes.headers };
                delete modifiedHeaders['content-encoding'];
                const modifiedBuffer = Buffer.from(text, 'utf-8');
                modifiedHeaders['content-length'] = String(modifiedBuffer.length);
                res.writeHead(proxyRes.statusCode || 200, modifiedHeaders);
                res.end(modifiedBuffer);
            });
        }
        else {
            res.writeHead(proxyRes.statusCode || 200, proxyRes.headers);
            proxyRes.pipe(res);
        }
    });
    proxyReq.on('error', (err) => {
        electron_log_1.default.error('[Proxy] Google Forwarding Error:', err);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: { message: 'Proxy forwarding failed: ' + err.message } }));
    });
    if (reqBody) {
        proxyReq.write(reqBody);
    }
    proxyReq.end();
}
// ─── File Data Resolver ────────────────────────────────────────────────────
async function resolveFileData(body, reqHeaders) {
    const contents = body.contents;
    if (!contents)
        return;
    const authHeader = (reqHeaders['authorization'] || reqHeaders['Authorization'] || '');
    for (const item of contents) {
        if (!item.parts)
            continue;
        for (let i = 0; i < item.parts.length; i++) {
            const p = item.parts[i];
            const fd = p.fileData;
            if (!fd?.fileUri)
                continue;
            try {
                const uri = fd.fileUri;
                let fileContent = '';
                if (uri.startsWith('file://')) {
                    const fp = uri.replace('file://', '').replace(/\//g, path.sep);
                    if (fs.existsSync(fp))
                        fileContent = fs.readFileSync(fp, 'utf-8');
                }
                else if (authHeader && uri.startsWith('https://')) {
                    fileContent = await downloadFileContent(uri, authHeader);
                }
                if (fileContent) {
                    item.parts[i] = { text: '[File content]:\n\n' + fileContent };
                }
            }
            catch (e) {
                electron_log_1.default.warn('[Proxy] File resolve failed:', e.message);
            }
        }
    }
}
function downloadFileContent(url, authHeader) {
    return new Promise((resolve, reject) => {
        const u = new URL(url);
        (u.protocol === 'https:' ? https : http).request({
            hostname: u.hostname, path: u.pathname + u.search,
            method: 'GET', headers: { 'Authorization': authHeader }, timeout: 30000,
        }, (res) => {
            if (res.statusCode !== 200) {
                reject(new Error('HTTP ' + res.statusCode));
                return;
            }
            let d = '';
            res.on('data', (c) => d += c.toString());
            res.on('end', () => resolve(d));
        }).on('error', reject).end();
    });
}
// ─── Custom Model Request Handler ─────────────────────────────────────────
function handleCustomModelRequest(res, model, body, isStream, cloudEnvelope = true) {
    void (0, customRequest_1.runCustomModelRequest)(res, model, body, isStream, loadCustomModels(), cloudEnvelope);
}
function readVarint(buf, offset) {
    let result = 0;
    let shift = 0;
    let bytes = 0;
    while (offset + bytes < buf.length) {
        const byte = buf[offset + bytes];
        result |= (byte & 0x7f) << shift;
        bytes++;
        if (!(byte & 0x80))
            break;
        shift += 7;
    }
    return { value: result >>> 0, bytes };
}
function encodeVarint(value) {
    const parts = [];
    let v = value >>> 0;
    do {
        let b = v & 0x7f;
        v >>>= 7;
        if (v !== 0)
            b |= 0x80;
        parts.push(b);
    } while (v !== 0);
    return Buffer.from(parts);
}
function parseProto(buf, offset, end) {
    const fields = [];
    let pos = offset;
    while (pos < end) {
        const start = pos;
        const tagVarint = readVarint(buf, pos);
        const tag = tagVarint.value;
        const wireType = tag & 0x07;
        const fieldNum = tag >>> 3;
        pos += tagVarint.bytes;
        if (wireType === 0) {
            const v = readVarint(buf, pos);
            fields.push({ tag, wireType, fieldNum, value: v.value, start, end: pos + v.bytes });
            pos += v.bytes;
        }
        else if (wireType === 2) {
            const lenVarint = readVarint(buf, pos);
            pos += lenVarint.bytes;
            const len = lenVarint.value;
            const children = parseProto(buf, pos, pos + len);
            const hasChildren = children.length > 0;
            fields.push({ tag, wireType, fieldNum, value: hasChildren ? children : buf.subarray(pos, pos + len), start, end: pos + len });
            pos += len;
        }
        else if (wireType === 1) {
            fields.push({ tag, wireType, fieldNum, value: buf.subarray(pos, pos + 8), start, end: pos + 8 });
            pos += 8;
        }
        else if (wireType === 5) {
            fields.push({ tag, wireType, fieldNum, value: buf.subarray(pos, pos + 4), start, end: pos + 4 });
            pos += 4;
        }
        else {
            break;
        }
    }
    return fields;
}
function encodeProtoBuf(fields) {
    const parts = [];
    for (const field of fields) {
        const tagBuf = encodeVarint(field.tag);
        const data = field.value;
        const lenBuf = encodeVarint(data.length);
        parts.push(tagBuf, lenBuf, data);
    }
    return Buffer.concat(parts);
}
function findModelEntryFieldTag(fields) {
    const tagCounts = new Map();
    for (const f of fields) {
        if (f.wireType === 2) {
            tagCounts.set(f.tag, (tagCounts.get(f.tag) || 0) + 1);
        }
    }
    let bestTag = null;
    let bestCount = 0;
    for (const [tag, count] of tagCounts) {
        if (count > bestCount) {
            bestCount = count;
            bestTag = tag;
        }
    }
    if (bestTag !== null && bestCount >= 2) {
        // Verify it has nested messages
        const sample = fields.find((f) => f.tag === bestTag && Array.isArray(f.value));
        if (sample)
            return bestTag;
    }
    return bestTag;
}
function extractFieldMapping(entry) {
    const mapping = new Map();
    for (const f of entry) {
        if (f.wireType === 2 && Buffer.isBuffer(f.value)) {
            mapping.set(f.fieldNum, 'string');
        }
        else if (f.wireType === 0) {
            mapping.set(f.fieldNum, 'varint');
        }
        else if (f.wireType === 2 && Array.isArray(f.value)) {
            mapping.set(f.fieldNum, 'bytes');
        }
    }
    return mapping;
}
function encodeModelEntryForGetModels(name, displayName, mapping) {
    const fields = [];
    for (const [fieldNum, protoType] of mapping) {
        if (protoType === 'string') {
            const tag = (fieldNum << 3) | 2;
            if (fieldNum === 1) {
                fields.push({ tag, value: Buffer.from(name, 'utf-8') });
            }
            else if (fieldNum === 2) {
                fields.push({ tag, value: Buffer.from(displayName, 'utf-8') });
            }
            else {
                fields.push({ tag, value: Buffer.alloc(0) });
            }
        }
        else if (protoType === 'varint') {
            const tag = (fieldNum << 3) | 0;
            fields.push({ tag, value: encodeVarint(0) });
        }
        else {
            const tag = (fieldNum << 3) | 2;
            fields.push({ tag, value: Buffer.alloc(0) });
        }
    }
    return encodeProtoBuf(fields);
}
// ─── GetAvailableModels Proxy Handler ───────────────────────────────────────
function handleGetAvailableModelsProxy(res, reqBody, lsUrl) {
    let lsParsed;
    try {
        lsParsed = new URL(lsUrl);
        if (!['http:', 'https:'].includes(lsParsed.protocol))
            throw new Error('Invalid protocol');
    }
    catch {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: { message: 'Invalid language server URL' } }));
        return;
    }
    const client = lsParsed.protocol === 'https:' ? https : http;
    const options = {
        method: 'POST',
        hostname: lsParsed.hostname,
        port: lsParsed.port || (lsParsed.protocol === 'https:' ? '443' : '80'),
        path: lsParsed.pathname + lsParsed.search,
        headers: {
            'Content-Type': 'application/grpc-web+proto',
            'Accept': 'application/grpc-web+proto',
            'Content-Length': String(reqBody.length),
        },
        rejectUnauthorized: false,
    };
    const lsReq = client.request(options, (lsRes) => {
        const chunks = [];
        lsRes.on('data', (chunk) => chunks.push(chunk));
        lsRes.on('end', () => {
            const responseBuf = Buffer.concat(chunks);
            const customModels = loadCustomModels();
            let modifiedBuf = responseBuf;
            if (customModels.length > 0 && responseBuf.length > 6) {
                try {
                    const flags = responseBuf[0];
                    const msgLen = responseBuf.readUInt32BE(1);
                    if (5 + msgLen <= responseBuf.length) {
                        const msgBody = responseBuf.subarray(5, 5 + msgLen);
                        const parsed = parseProto(msgBody, 0, msgBody.length);
                        const modelTag = findModelEntryFieldTag(parsed);
                        if (modelTag !== null) {
                            const sampleEntry = parsed.find((f) => f.tag === modelTag && Array.isArray(f.value));
                            if (sampleEntry && Array.isArray(sampleEntry.value)) {
                                const fieldMapping = extractFieldMapping(sampleEntry.value);
                                const newParts = [msgBody];
                                for (const m of customModels) {
                                    const placeholderId = generateModelPlaceholderId(m);
                                    const entry = encodeModelEntryForGetModels('models/' + placeholderId, m.displayName, fieldMapping);
                                    const tagBuf = encodeVarint(modelTag);
                                    const lenBuf = encodeVarint(entry.length);
                                    newParts.push(tagBuf, lenBuf, entry);
                                    electron_log_1.default.info(`[Proxy] Injected into GetAvailableModels: ${m.displayName} => ${placeholderId}`);
                                }
                                const newMsgBody = Buffer.concat(newParts);
                                const newHeader = Buffer.alloc(5);
                                newHeader[0] = flags;
                                newHeader.writeUInt32BE(newMsgBody.length, 1);
                                modifiedBuf = Buffer.concat([newHeader, newMsgBody]);
                            }
                        }
                    }
                }
                catch (err) {
                    electron_log_1.default.error('[Proxy] Failed to inject models into GetAvailableModels:', err);
                }
            }
            res.writeHead(lsRes.statusCode || 200, {
                'Content-Type': 'application/grpc-web+proto',
                'Content-Length': String(modifiedBuf.length),
            });
            res.end(modifiedBuf);
        });
        lsRes.on('error', (err) => {
            electron_log_1.default.error('[Proxy] LS error for GetAvailableModels:', err.message);
            if (!res.headersSent) {
                res.writeHead(502);
                res.end();
            }
        });
    });
    lsReq.setTimeout(30000, () => {
        electron_log_1.default.error('[Proxy] GetAvailableModels forward timed out');
        lsReq.destroy();
        if (!res.headersSent) {
            res.writeHead(504);
            res.end();
        }
    });
    lsReq.on('error', (err) => {
        electron_log_1.default.error('[Proxy] GetAvailableModels forward error:', err.message);
        if (!res.headersSent) {
            res.writeHead(502);
            res.end();
        }
    });
    lsReq.write(reqBody);
    lsReq.end();
}
// ─── Main Request Handler ─────────────────────────────────────────────────
function handleRequest(req, res) {
    let requestUrl;
    try {
        req.url = (req.url || '/').replace(/^.*\/dummy_path_padding/, '');
        // Strip binary patch padding (from LS hostname replacement)
        req.url = req.url.replace(/\/v1internal\/x{7}/, '');
        // This listener routes fixed upstreams; authority-form targets must never replace them.
        if (!req.url.startsWith('/') || /^[\\/]{2}/.test(req.url))
            throw new Error('Invalid target');
        requestUrl = new URL(req.url, 'http://localhost');
    }
    catch {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: { message: 'Invalid request target' } }));
        return;
    }
    // Health check
    if (req.method === 'GET' && (req.url === '/health' || req.url === '/healthz')) {
        const memUsage = process.memoryUsage();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            status: 'ok',
            uptime: process.uptime(),
            port: proxyPort,
            memory: {
                rssMB: Math.round(memUsage.rss / 1024 / 1024),
                heapUsedMB: Math.round(memUsage.heapUsed / 1024 / 1024),
                heapTotalMB: Math.round(memUsage.heapTotal / 1024 / 1024),
            },
            state: {
                activeStreamContexts: shared_1.activeStreamContexts.size,
                modelToolCallIds: shared_1.modelToolCallIds.size,
                translatedToolCalls: shared_1.translatedToolCalls.size,
                modelReasoningContent: shared_1.modelReasoningContent.size,
            },
            timestamp: new Date().toISOString(),
        }));
        return;
    }
    if (req.method === 'GET' && requestUrl.pathname === '/metrics') {
        res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
        res.end(JSON.stringify((0, customRequest_1.getProxyMetrics)()));
        return;
    }
    // P0-4: Enforce maximum request body size to prevent memory exhaustion DoS
    const MAX_BODY_SIZE = 10 * 1024 * 1024; // 10 MB
    let bodyLength = 0;
    let bodyRejected = false;
    const bodyChunks = [];
    req.on('data', (chunk) => {
        bodyLength += chunk.length;
        if (bodyLength > MAX_BODY_SIZE) {
            if (!bodyRejected) {
                bodyRejected = true;
                electron_log_1.default.warn(`[Proxy] Request body exceeds ${MAX_BODY_SIZE / 1024 / 1024}MB limit (${req.method} ${req.url})`);
                req.destroy();
                if (!res.headersSent) {
                    res.writeHead(413, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: { message: `Request body too large. Maximum: ${MAX_BODY_SIZE / 1024 / 1024}MB` } }));
                }
            }
            return;
        }
        bodyChunks.push(chunk);
    });
    req.on('end', () => {
        if (bodyRejected)
            return;
        const fullBody = Buffer.concat(bodyChunks);
        const bodyStr = fullBody.toString('utf-8');
        electron_log_1.default.info(`[Proxy] Request: ${req.method} ${req.url}`);
        // 0. Intercept GetAvailableModels (redirected from Electron webRequest)
        if (req.url.startsWith('/GetAvailableModels')) {
            const gavParsed = new URL(req.url, 'http://127.0.0.1');
            const lsUrl = gavParsed.searchParams.get('ls');
            if (lsUrl) {
                handleGetAvailableModelsProxy(res, fullBody, lsUrl);
                return;
            }
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Missing ls parameter' }));
            return;
        }
        // 1. Intercept /v1internal:fetchAvailableModels
        if (req.url.includes('/v1internal:fetchAvailableModels')) {
            electron_log_1.default.info('[Proxy] Intercepting fetchAvailableModels request');
            const targetUrl = 'https://daily-cloudcode-pa.googleapis.com';
            const parsedUrl = new URL(req.url, targetUrl);
            const fwdHeaders = {
                ...req.headers,
            };
            fwdHeaders['host'] = 'daily-cloudcode-pa.googleapis.com';
            delete fwdHeaders['connection'];
            delete fwdHeaders['keep-alive'];
            delete fwdHeaders['accept-encoding'];
            const fwdOptions = {
                method: req.method,
                headers: fwdHeaders,
            };
            const googleReq = https.request(parsedUrl, fwdOptions, (googleRes) => {
                // P0-5: Timeout for fetchAvailableModels forward request (5s in restricted regions)
                googleReq.setTimeout(5000, () => {
                    electron_log_1.default.error('[Proxy] fetchAvailableModels forward request timed out');
                    googleReq.destroy();
                    if (!res.headersSent) {
                        const customModels = loadCustomModels();
                        const mappedCustom = {};
                        customModels.forEach((m) => {
                            const slug = toSlug(m);
                            mappedCustom[slug] = {
                                displayName: m.displayName,
                                maxTokens: (0, modelUtils_1.detectModelCapabilities)(m).maxTokens,
                                maxOutputTokens: (0, modelUtils_1.detectModelCapabilities)(m).maxOutputTokens,
                                model: generateModelPlaceholderId(m),
                                apiProvider: 'API_PROVIDER_GOOGLE_GEMINI',
                                modelProvider: 'MODEL_PROVIDER_GOOGLE',
                            };
                        });
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ models: mappedCustom }));
                    }
                });
                let googleBody = '';
                googleRes.on('data', (chunk) => (googleBody += chunk));
                googleRes.on('end', () => {
                    try {
                        electron_log_1.default.info(`[Proxy] fetchAvailableModels response status: ${googleRes.statusCode}, body length: ${googleBody.length}`);
                        const googleJson = JSON.parse(googleBody);
                        const customModels = loadCustomModels();
                        electron_log_1.default.info(`[Proxy] Loaded custom models count: ${customModels.length}`);
                        const mergeModels = (target) => {
                            if (Array.isArray(target)) {
                                const mapped = customModels.map((m) => {
                                    const cap = (0, modelUtils_1.detectModelCapabilities)(m, true);
                                    return {
                                        name: 'models/' + generateModelPlaceholderId(m),
                                        version: '1.0',
                                        displayName: m.displayName,
                                        description: m.description,
                                        inputTokenLimit: cap.maxTokens,
                                        outputTokenLimit: cap.maxOutputTokens,
                                        supportedGenerationMethods: ['generateContent', 'countTokens'],
                                        temperature: cap.isThinking ? undefined : 0.7,
                                        topP: cap.isThinking ? undefined : 0.9,
                                        topK: cap.isThinking ? undefined : 40,
                                    };
                                });
                                return [...mapped, ...target];
                            }
                            else if (target && typeof target === 'object') {
                                const result = { ...target };
                                customModels.forEach((m) => {
                                    const slug = toSlug(m);
                                    const cap = (0, modelUtils_1.detectModelCapabilities)(m, true);
                                    const entry = {
                                        displayName: m.displayName,
                                        supportsImages: cap.supportsImages,
                                        supportsThinking: cap.isThinking,
                                        recommended: true,
                                        maxTokens: cap.maxTokens,
                                        maxOutputTokens: cap.maxOutputTokens,
                                        tokenizerType: 'LLAMA_WITH_SPECIAL',
                                        model: generateModelPlaceholderId(m),
                                        apiProvider: 'API_PROVIDER_GOOGLE_GEMINI',
                                        modelProvider: 'MODEL_PROVIDER_GOOGLE',
                                    };
                                    if (cap.supportsImages) {
                                        entry.supportsVideo = false;
                                        entry.supportedMimeTypes = {
                                            'image/png': true,
                                            'image/jpeg': true,
                                            'image/webp': true,
                                            'image/gif': true,
                                            'image/heic': true,
                                            'image/heif': true,
                                            'text/plain': true,
                                            'text/markdown': true,
                                            'text/html': true,
                                            'text/css': true,
                                            'text/xml': true,
                                            'text/csv': true,
                                            'application/json': true,
                                            'application/pdf': true,
                                            'application/x-javascript': true,
                                            'application/x-typescript': true,
                                            'application/x-python-code': true,
                                            'application/x-ipynb+json': true,
                                        };
                                    }
                                    else {
                                        entry.supportsVideo = false;
                                        entry.supportedMimeTypes = {
                                            'text/plain': true,
                                            'text/markdown': true,
                                            'text/html': true,
                                            'text/css': true,
                                            'text/xml': true,
                                            'text/csv': true,
                                            'application/json': true,
                                            'application/pdf': true,
                                            'application/x-javascript': true,
                                            'application/x-typescript': true,
                                            'application/x-python-code': true,
                                            'application/x-ipynb+json': true,
                                        };
                                    }
                                    result[slug] = entry;
                                    m._slug = slug;
                                    electron_log_1.default.info(`[Proxy] Custom model "${m.displayName}" => slug: ${slug} => model: ${generateModelPlaceholderId(m)} => thinking: ${cap.isThinking} => images: ${cap.supportsImages}`);
                                });
                                return result;
                            }
                            return target;
                        };
                        let merged = false;
                        if (googleJson.models) {
                            googleJson.models = mergeModels(googleJson.models);
                            merged = true;
                        }
                        if (googleJson.availableModels) {
                            googleJson.availableModels = mergeModels(googleJson.availableModels);
                            merged = true;
                        }
                        if (googleJson.available_models) {
                            googleJson.available_models = mergeModels(googleJson.available_models);
                            merged = true;
                        }
                        if (!merged) {
                            const modelsMap = {};
                            customModels.forEach((m) => {
                                const slug = toSlug(m);
                                modelsMap[slug] = {
                                    displayName: m.displayName,
                                    recommended: true,
                                    maxTokens: (0, modelUtils_1.detectModelCapabilities)(m).maxTokens,
                                    maxOutputTokens: (0, modelUtils_1.detectModelCapabilities)(m).maxOutputTokens,
                                    tokenizerType: 'LLAMA_WITH_SPECIAL',
                                    model: generateModelPlaceholderId(m),
                                    apiProvider: 'API_PROVIDER_GOOGLE_GEMINI',
                                    modelProvider: 'MODEL_PROVIDER_GOOGLE',
                                };
                                m._slug = slug;
                            });
                            googleJson.models = modelsMap;
                        }
                        // Inject custom model slugs into agentModelSorts
                        const customSlugs = customModels.map((m) => m._slug).filter(Boolean);
                        if (customSlugs.length > 0) {
                            if (googleJson.agentModelSorts && Array.isArray(googleJson.agentModelSorts)) {
                                googleJson.agentModelSorts.forEach((sort) => {
                                    if (sort.groups && Array.isArray(sort.groups)) {
                                        sort.groups.forEach((group) => {
                                            if (group.modelIds && Array.isArray(group.modelIds)) {
                                                customSlugs.forEach((slug) => {
                                                    if (!group.modelIds.includes(slug)) {
                                                        group.modelIds.push(slug);
                                                    }
                                                });
                                            }
                                        });
                                    }
                                });
                            }
                        }
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify(googleJson));
                    }
                    catch (err) {
                        electron_log_1.default.error('[Proxy] Parsing fetchAvailableModels failed, returning custom models:', err);
                        const customModels = loadCustomModels();
                        const mappedCustom = {};
                        customModels.forEach((m) => {
                            const slug = toSlug(m);
                            mappedCustom[slug] = {
                                displayName: m.displayName,
                                maxTokens: (0, modelUtils_1.detectModelCapabilities)(m).maxTokens,
                                maxOutputTokens: (0, modelUtils_1.detectModelCapabilities)(m).maxOutputTokens,
                                model: generateModelPlaceholderId(m),
                                apiProvider: 'API_PROVIDER_GOOGLE_GEMINI',
                                modelProvider: 'MODEL_PROVIDER_GOOGLE',
                            };
                        });
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ models: mappedCustom }));
                    }
                });
            });
            googleReq.on('error', (err) => {
                electron_log_1.default.error('[Proxy] Forwarding fetchAvailableModels failed:', err);
                const customModels = loadCustomModels();
                const mappedCustom = {};
                customModels.forEach((m) => {
                    const slug = toSlug(m);
                    mappedCustom[slug] = {
                        displayName: m.displayName,
                        maxTokens: (0, modelUtils_1.detectModelCapabilities)(m).maxTokens,
                        maxOutputTokens: (0, modelUtils_1.detectModelCapabilities)(m).maxOutputTokens,
                        model: generateModelPlaceholderId(m),
                        apiProvider: 'API_PROVIDER_GOOGLE_GEMINI',
                        modelProvider: 'MODEL_PROVIDER_GOOGLE',
                    };
                });
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ models: mappedCustom }));
            });
            if (fullBody && fullBody.length > 0) {
                googleReq.write(fullBody);
            }
            googleReq.end();
            return;
        }
        // 2. Intercept /v1beta/models or /v1/models list request
        if (req.method === 'GET' && (req.url.endsWith('/models') || req.url.includes('/models?'))) {
            electron_log_1.default.info('[Proxy] Intercepting models list request');
            const targetUrl = 'https://generativelanguage.googleapis.com';
            const parsedUrl = new URL(req.url, targetUrl);
            const mdlHeaders = {
                ...req.headers,
            };
            mdlHeaders['host'] = 'generativelanguage.googleapis.com';
            delete mdlHeaders['connection'];
            delete mdlHeaders['accept-encoding'];
            const mdlOptions = { method: 'GET', headers: mdlHeaders };
            const googleReq = https.request(parsedUrl, mdlOptions, (googleRes) => {
                // P0-5: Timeout for models list forward request (5s)
                googleReq.setTimeout(5000, () => {
                    electron_log_1.default.error('[Proxy] Models list forward request timed out');
                    googleReq.destroy();
                    if (!res.headersSent) {
                        const customModels = loadCustomModels();
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({
                            models: customModels.map((m) => ({
                                name: m.name,
                                displayName: m.displayName,
                                description: m.description,
                                supportedGenerationMethods: ['generateContent'],
                            })),
                        }));
                    }
                });
                let googleBody = '';
                googleRes.on('data', (chunk) => (googleBody += chunk));
                googleRes.on('end', () => {
                    try {
                        const googleJson = JSON.parse(googleBody);
                        const customModels = loadCustomModels();
                        const mappedCustom = customModels.map((m) => ({
                            name: 'models/' + generateModelPlaceholderId(m),
                            version: '1.0',
                            displayName: m.displayName,
                            description: m.description,
                            inputTokenLimit: (0, modelUtils_1.detectModelCapabilities)(m).maxTokens,
                            outputTokenLimit: (0, modelUtils_1.detectModelCapabilities)(m).maxOutputTokens,
                            supportedGenerationMethods: ['generateContent', 'countTokens'],
                            temperature: 0.7,
                            topP: 0.9,
                            topK: 40,
                        }));
                        if (googleJson.models) {
                            googleJson.models = [...mappedCustom, ...googleJson.models];
                        }
                        else {
                            googleJson.models = mappedCustom;
                        }
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify(googleJson));
                    }
                    catch (err) {
                        electron_log_1.default.error('[Proxy] Google list models failed, returning custom models list only:', err);
                        const customModels = loadCustomModels();
                        const mappedCustom = customModels.map((m) => ({
                            name: 'models/' + generateModelPlaceholderId(m),
                            version: '1.0',
                            displayName: m.displayName,
                            description: m.description,
                            inputTokenLimit: (0, modelUtils_1.detectModelCapabilities)(m).maxTokens,
                            outputTokenLimit: (0, modelUtils_1.detectModelCapabilities)(m).maxOutputTokens,
                            supportedGenerationMethods: ['generateContent', 'countTokens'],
                        }));
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ models: mappedCustom }));
                    }
                });
            });
            googleReq.on('error', (err) => {
                electron_log_1.default.error('[Proxy] Google models list request error:', err);
                const customModels = loadCustomModels();
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    models: customModels.map((m) => ({
                        name: m.name,
                        displayName: m.displayName,
                        description: m.description,
                        supportedGenerationMethods: ['generateContent'],
                    })),
                }));
            });
            googleReq.end();
            return;
        }
        // 3. Intercept Cloud Code generation stream or non-stream requests
        const isCloudCodeStream = req.url.includes('/v1internal:streamGenerateContent') || req.url.includes('/v1internal:generateContent');
        if (req.method === 'POST' && isCloudCodeStream) {
            try {
                const reqJson = JSON.parse(bodyStr);
                const modelName = reqJson.model;
                const modelId = (reqJson.modelId || reqJson.model_id);
                electron_log_1.default.info(`[Proxy] Cloud Code generation request model: ${modelName}, modelId: ${modelId}, url: ${req.url}, bodyKeys: ${Object.keys(reqJson).join(',')}`);
                if (modelName) {
                    const customModels = loadCustomModels();
                    const matchedCustomModel = customModels.find((m) => {
                        const enumName = generateModelPlaceholderId(m);
                        return m.name === modelName || toSlug(m) === modelName || enumName === modelName || enumName === modelId;
                    });
                    if (matchedCustomModel) {
                        electron_log_1.default.info(`[Proxy] Intercepting Cloud Code generation for custom model: ${modelName} => ${matchedCustomModel.displayName}`);
                        const isStream = req.url.includes('streamGenerateContent') || req.url.includes('alt=sse');
                        const actualGeminiBody = { ...(reqJson.request || reqJson) };
                        if (typeof reqJson.sessionId === 'string')
                            actualGeminiBody.sessionId = reqJson.sessionId;
                        if (typeof reqJson.conversationId === 'string')
                            actualGeminiBody.conversationId = reqJson.conversationId;
                        // Resolve fileData URIs then route to translator
                        resolveFileData(actualGeminiBody, req.headers).then(() => {
                            handleCustomModelRequest(res, matchedCustomModel, actualGeminiBody, isStream);
                        });
                        return;
                    }
                }
            }
            catch (err) {
                electron_log_1.default.error('[Proxy] Failed to parse Cloud Code stream body:', err);
            }
        }
        // 4. Intercept standard generateContent / streamGenerateContent request
        const generateMatch = req.url.match(/\/(?:v1|v1beta)\/(models\/[^:]+):generateContent/);
        const streamMatch = req.url.match(/\/(?:v1|v1beta)\/(models\/[^:]+):streamGenerateContent/);
        const isGenerate = !!generateMatch;
        const isStandardStream = !!streamMatch;
        if (req.method === 'POST' && (isGenerate || isStandardStream)) {
            let matchedModelName;
            try {
                matchedModelName = decodeURIComponent(isGenerate ? generateMatch[1] : streamMatch[1]);
            }
            catch {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: { message: 'Invalid model URL encoding' } }));
                return;
            }
            const customModels = loadCustomModels();
            const matchedCustomModel = customModels.find((m) => {
                const enumName = generateModelPlaceholderId(m);
                return (m.name === matchedModelName ||
                    m.externalModelName === matchedModelName ||
                    'models/' + m.externalModelName === matchedModelName ||
                    toSlug(m) === matchedModelName ||
                    enumName === matchedModelName ||
                    'models/' + enumName === matchedModelName);
            });
            if (matchedCustomModel) {
                try {
                    const geminiBody = JSON.parse(bodyStr);
                    resolveFileData(geminiBody, req.headers).then(() => {
                        handleCustomModelRequest(res, matchedCustomModel, geminiBody, isStandardStream, false);
                    });
                    return;
                }
                catch (e) {
                    electron_log_1.default.error('[Proxy] JSON parse error in request body:', e);
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: { message: 'Invalid JSON request body' } }));
                    return;
                }
            }
        }
        // 5. Fallback: transparent proxy to Google
        proxyToGoogle(req, res, fullBody);
    });
}
// ─── Server Start/Stop ────────────────────────────────────────────────────
async function startProxy() {
    if (stoppingProxy)
        await stoppingProxy;
    if (server?.listening && proxyPort)
        return proxyPort;
    if (startingProxy)
        return startingProxy;
    const requiredPort = (0, listen_1.getRequiredProxyPort)(electron_1.app.getAppPath());
    const newServer = http.createServer(handleRequest);
    server = newServer;
    (0, shared_1.startCleanupInterval)();
    startingProxy = (0, listen_1.listenProxy)(newServer, requiredPort ?? 50999, requiredPort === undefined)
        .then((port) => {
        proxyPort = port;
        electron_log_1.default.info(`[Proxy] Server listening on http://127.0.0.1:${proxyPort}`);
        return proxyPort;
    })
        .catch((error) => {
        (0, shared_1.stopCleanupInterval)();
        server = null;
        proxyPort = 0;
        electron_log_1.default.error('[Proxy] Startup failed:', error);
        throw error;
    })
        .finally(() => {
        startingProxy = null;
    });
    return startingProxy;
}
function stopProxy() {
    if (stoppingProxy)
        return stoppingProxy;
    stoppingProxy = (async () => {
        // A shutdown requested during startup must also close the listener once ready.
        if (startingProxy) {
            try {
                await startingProxy;
            }
            catch {
                // A failed start already cleared its server and cleanup interval.
            }
        }
        (0, shared_1.stopCleanupInterval)();
        (0, customRequest_1.stopCustomRequests)();
        if (server) {
            const closingServer = server;
            await new Promise((resolve) => closingServer.close(() => resolve()));
            electron_log_1.default.info('[Proxy] Server stopped');
        }
        server = null;
        proxyPort = 0;
    })().finally(() => {
        stoppingProxy = null;
    });
    return stoppingProxy;
}
function getProxyPort() {
    return proxyPort;
}
//# sourceMappingURL=proxy.js.map