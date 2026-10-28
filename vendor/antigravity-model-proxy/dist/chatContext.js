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
exports.findContextModel = findContextModel;
exports.findConversationIdByTitle = findConversationIdByTitle;
exports.getChatContextUsage = getChatContextUsage;
exports.discoverContextLimit = discoverContextLimit;
exports.getContextInformation = getContextInformation;
/** Read-only context information. Native transcripts omit system prompts and usage metadata. */
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const readline = __importStar(require("node:readline"));
const UUID = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i;
const MAX_TRANSCRIPT_BYTES = 64 * 1024 * 1024;
const transcriptCache = new Map();
const pendingTranscripts = new Map();
const validLimit = (value) => typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
const label = (value) => typeof value === 'string' ? value.trim().replace(/[▾▲▼◂▸◀▶]/g, '').replace(/\s+/g, ' ').trim().toLowerCase() : '';
const modelKey = (value) => label(value).replace(/^models\//, '').replace(/[^a-z0-9]/g, '');
/** Never let an earlier prefix match shadow an exact model or effort variant. */
function findContextModel(name, models) {
    const nameLabel = label(name);
    if (!nameLabel)
        return undefined;
    for (const field of ['displayName', 'name', 'externalModelName']) {
        const matches = models.filter((model) => label(model[field]) === nameLabel);
        if (matches.length === 1)
            return matches[0];
        if (matches.length > 1)
            return undefined;
    }
    const key = modelKey(name);
    const matches = models.filter((model) => [model.displayName, model.name, model.externalModelName].some((value) => value && modelKey(value) === key));
    return matches.length === 1 ? matches[0] : undefined;
}
/** A title is usable only when it identifies one conversation, including archived rows. */
function findConversationIdByTitle(title, dataDirectory) {
    if (typeof title !== 'string' || !title.trim() || title.length > 512)
        return undefined;
    const filename = path.join(dataDirectory, 'conversation_summaries.db');
    if (!fs.existsSync(filename))
        return undefined;
    try {
        // Electron versions without node:sqlite simply leave identity unavailable.
        // eslint-disable-next-line @typescript-eslint/no-require-imports, @typescript-eslint/no-var-requires
        const { DatabaseSync } = require('node:sqlite');
        const db = new DatabaseSync(filename, { readOnly: true });
        try {
            const rows = db.prepare('SELECT conversation_id FROM conversation_summaries WHERE title = ? LIMIT 2')
                .all(title.trim());
            return rows.length === 1 && UUID.test(rows[0].conversation_id) ? rows[0].conversation_id : undefined;
        }
        finally {
            db.close();
        }
    }
    catch {
        return undefined;
    }
}
async function getChatContextUsage(conversationId, dataDirectory) {
    const id = typeof conversationId === 'string' && UUID.test(conversationId) ? conversationId : '';
    const unavailable = { conversationId: id, source: 'unavailable' };
    if (!id)
        return unavailable;
    const filename = path.join(dataDirectory, 'brain', id, '.system_generated', 'logs', 'transcript.jsonl');
    try {
        const stat = await fs.promises.stat(filename);
        // Do not show a truncated tail as the whole context. Large/unsupported files are explicitly unavailable.
        if (!stat.isFile() || stat.size > MAX_TRANSCRIPT_BYTES)
            return unavailable;
        const stamp = `${stat.mtimeMs}:${stat.ctimeMs}:${stat.size}`;
        const cached = transcriptCache.get(filename);
        if (cached?.stamp === stamp)
            return { ...cached.result };
        const pending = pendingTranscripts.get(filename);
        if (pending)
            return { ...await pending };
        const read = async () => {
            let characters = 0;
            let entries = 0;
            let malformed = false;
            const input = fs.createReadStream(filename, { encoding: 'utf8' });
            const lines = readline.createInterface({ input, crlfDelay: Infinity });
            try {
                for await (const line of lines) {
                    if (!line.trim())
                        continue;
                    try {
                        const entry = JSON.parse(line);
                        if (!entry || typeof entry !== 'object' || typeof entry.type !== 'string' ||
                            typeof entry.source !== 'string') {
                            malformed = true;
                            continue;
                        }
                        // The native structured CHECKPOINT starts a new visible context.
                        // Quoted "resuming" text in user messages is never a checkpoint.
                        if (entry.type === 'CHECKPOINT' && entry.source === 'SYSTEM')
                            characters = 0;
                        if (typeof entry.content === 'string')
                            characters += entry.content.length;
                        if (typeof entry.thinking === 'string')
                            characters += entry.thinking.length;
                        if (Array.isArray(entry.tool_calls))
                            characters += JSON.stringify(entry.tool_calls).length;
                        entries++;
                    }
                    catch {
                        malformed = true;
                    }
                }
            }
            finally {
                lines.close();
                input.destroy();
            }
            const after = await fs.promises.stat(filename);
            // A concurrent append or partial JSON line must not cache a falsely small count.
            if (malformed || after.size !== stat.size || after.mtimeMs !== stat.mtimeMs || !entries)
                return unavailable;
            const result = { conversationId: id, source: 'estimated', currentTokens: Math.ceil(characters / 4) };
            if (transcriptCache.size >= 100)
                transcriptCache.delete(transcriptCache.keys().next().value);
            transcriptCache.set(filename, { stamp, result });
            return { ...result };
        };
        const promise = read();
        pendingTranscripts.set(filename, promise);
        try {
            return await promise;
        }
        finally {
            pendingTranscripts.delete(filename);
        }
    }
    catch {
        return unavailable;
    }
}
let catalog;
let catalogExpires = 0;
let catalogPending;
async function publicCatalog() {
    if (Date.now() < catalogExpires)
        return catalog;
    if (catalogPending)
        return catalogPending;
    catalogPending = (async () => {
        catalogExpires = Date.now() + 60000;
        try {
            // A fixed public catalog URL receives no conversation, model name or credentials.
            const response = await fetch('https://models.dev/api.json', { signal: AbortSignal.timeout(5000) });
            if (!response.ok || !response.body)
                return undefined;
            const reader = response.body.getReader();
            const chunks = [];
            let bytes = 0;
            try {
                for (;;) {
                    const chunk = await reader.read();
                    if (chunk.done)
                        break;
                    bytes += chunk.value.byteLength;
                    if (bytes > 32 * 1024 * 1024)
                        return undefined;
                    chunks.push(chunk.value);
                }
            }
            finally {
                await reader.cancel().catch(() => { });
            }
            const parsed = JSON.parse(Buffer.concat(chunks).toString('utf8'));
            if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed))
                return undefined;
            catalog = parsed;
            catalogExpires = Date.now() + 300000;
            return catalog;
        }
        catch {
            return undefined;
        }
    })();
    try {
        return await catalogPending;
    }
    finally {
        catalogPending = undefined;
    }
}
/** Exact catalog identifiers only; conflicting provider limits remain unknown. */
async function discoverContextLimit(modelName, provider) {
    const key = modelKey(modelName);
    if (!key)
        return undefined;
    const data = await publicCatalog();
    if (!data)
        return undefined;
    const preferred = provider && data[provider]?.models ? [[provider, data[provider]]] : Object.entries(data);
    const limits = new Set();
    for (const [, entry] of preferred) {
        if (!entry || typeof entry !== 'object' || !entry.models || typeof entry.models !== 'object')
            continue;
        for (const [id, model] of Object.entries(entry.models)) {
            if (!model || typeof model !== 'object' || !validLimit(model.limit?.context))
                continue;
            if (modelKey(id) === key || modelKey(model.name) === key)
                limits.add(model.limit.context);
        }
    }
    return limits.size === 1 ? [...limits][0] : undefined;
}
async function getContextInformation(payload, dataDirectory, models) {
    const request = payload && typeof payload === 'object' ? payload : {};
    const id = request.conversationId || findConversationIdByTitle(request.title, dataDirectory);
    const result = await getChatContextUsage(id, dataDirectory);
    const name = typeof request.modelName === 'string' && request.modelName.length <= 512 ? request.modelName : '';
    const configured = findContextModel(name, models);
    if (validLimit(configured?.contextWindow)) {
        result.maxTokens = configured.contextWindow;
        result.limitSource = 'configured';
    }
    else if (request.discoverLimit === true && name) {
        const limit = await discoverContextLimit(configured?.externalModelName || name, configured?.provider);
        if (limit) {
            result.maxTokens = limit;
            result.limitSource = 'public-catalog';
        }
    }
    return result;
}
//# sourceMappingURL=chatContext.js.map