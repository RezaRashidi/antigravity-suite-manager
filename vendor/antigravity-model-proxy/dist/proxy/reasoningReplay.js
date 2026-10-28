"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.reasoningReplayCache = exports.ReasoningReplayCache = void 0;
const node_crypto_1 = require("node:crypto");
const TTL = 30 * 60000;
const MAX_ENTRIES = 256;
const MAX_ENTRY_CHARACTERS = 256 * 1024;
const MAX_TOTAL_CHARACTERS = 4 * 1024 * 1024;
const object = (value) => value && typeof value === 'object' && !Array.isArray(value) ? value : undefined;
const identifier = (value) => typeof value === 'string' && value.length > 0 && value.length <= 256 && value.trim() === value ? value : undefined;
/** Canonical JSON fingerprints do not depend on object-property insertion order. */
function canonical(value) {
    let characters = 0;
    let nodes = 0;
    const add = (text) => {
        characters += text.length;
        if (characters > MAX_ENTRY_CHARACTERS)
            throw new Error('Fingerprint exceeds bound');
        return text;
    };
    const visit = (item, depth) => {
        if (++nodes > 10000 || depth > 64)
            throw new Error('Fingerprint exceeds bound');
        if (item === null || typeof item === 'boolean' || typeof item === 'number')
            return add(JSON.stringify(item));
        if (typeof item === 'string')
            return add(JSON.stringify(item));
        if (Array.isArray(item))
            return add('[') + item.map((entry) => visit(entry ?? null, depth + 1)).join(add(',')) + add(']');
        const record = object(item);
        if (!record)
            throw new Error('Unsupported fingerprint value');
        const fields = Object.keys(record)
            .filter((key) => record[key] !== undefined)
            .sort();
        return (add('{') +
            fields.map((key) => add(JSON.stringify(key)) + add(':') + visit(record[key], depth + 1)).join(add(',')) +
            add('}'));
    };
    return visit(value, 0);
}
function scope(body, model) {
    const conversation = [
        ['cascade_id', identifier(object(body.labels)?.cascade_id)],
        ['conversationId', identifier(body.conversationId)],
        ['sessionId', identifier(body.sessionId)],
    ].find((entry) => entry[1] !== undefined);
    if (!conversation || !model.name || !model.provider || !model.apiUrl)
        return undefined;
    try {
        // Credentials influence isolation, but neither their values nor the scope tuple are retained.
        return (0, node_crypto_1.createHash)('sha256')
            .update(canonical([
            conversation,
            model.name,
            model.provider,
            model.apiUrl,
            model.externalModelName || '',
            model.apiFormat || '',
            model.apiKey || '',
            model.customHeaders || {},
            model.rawUrl === true,
        ]))
            .digest('hex');
    }
    catch {
        return undefined;
    }
}
function callGroup(parts) {
    const calls = [];
    const ids = new Set();
    for (const value of parts) {
        const part = object(value);
        if (!part || part.functionCall === undefined)
            continue;
        const call = object(part.functionCall);
        const id = identifier(call?.id), name = identifier(call?.name);
        if (!id || !name || ids.has(id) || calls.length >= 256)
            return undefined;
        ids.add(id);
        calls.push({ id, name, args: call?.args ?? {} });
    }
    if (!calls.length)
        return undefined;
    try {
        calls.sort((left, right) => (left.id < right.id ? -1 : left.id > right.id ? 1 : 0));
        return (0, node_crypto_1.createHash)('sha256').update(canonical(calls)).digest('hex');
    }
    catch {
        return undefined;
    }
}
/** Volatile, bounded recovery for clients that omit thought parts from tool history. */
class ReasoningReplayCache {
    constructor(now = Date.now) {
        this.now = now;
        this.entries = new Map();
        this.characters = 0;
    }
    remove(key) {
        this.characters -= this.entries.get(key)?.reasoning?.length || 0;
        this.entries.delete(key);
    }
    prune() {
        const now = this.now();
        for (const [key, entry] of this.entries) {
            if (now < entry.recordedAt || now - entry.recordedAt >= TTL)
                this.remove(key);
        }
    }
    clear() {
        this.entries.clear();
        this.characters = 0;
    }
    /** Call only after successful completion, with all mapped thought/tool-call parts. */
    record(body, model, parts) {
        this.prune();
        const modelScope = scope(body, model);
        if (!modelScope)
            return;
        const group = callGroup(parts);
        if (!group)
            return;
        const reusedHistoryGroup = body.contents?.some((content) => content.role === 'model' && Array.isArray(content.parts) && callGroup(content.parts) === group);
        let reasoning = '';
        for (const value of reusedHistoryGroup ? [] : parts) {
            const part = object(value);
            if (!part?.thought || typeof part.text !== 'string')
                continue;
            if (reasoning.length + part.text.length > MAX_ENTRY_CHARACTERS)
                return;
            reasoning += part.text;
        }
        const key = `${modelScope}:${group}`;
        const existing = this.entries.get(key);
        if (existing) {
            if (existing.reasoning !== reasoning && existing.reasoning !== null) {
                // Reused IDs with different reasoning are ambiguous until expiration; never guess.
                this.characters -= existing.reasoning.length;
                existing.reasoning = null;
            }
            return;
        }
        // Empty turns and groups already present in history block later reuse, even
        // when the earlier observation has expired or was evicted from this cache.
        this.entries.set(key, { reasoning: reasoning || null, recordedAt: this.now() });
        this.characters += reasoning.length;
        while (this.entries.size > MAX_ENTRIES || this.characters > MAX_TOTAL_CHARACTERS) {
            this.remove(this.entries.keys().next().value);
        }
    }
    /** Recover before context budgeting; return a copy only when a history item changes. */
    restore(body, model) {
        this.prune();
        const modelScope = scope(body, model);
        if (!modelScope || !Array.isArray(body.contents))
            return body;
        let changed = false;
        const contents = body.contents.map((content) => {
            if (content.role !== 'model' || !Array.isArray(content.parts) || content.parts.some((part) => part.thought))
                return content;
            const group = callGroup(content.parts);
            if (!group)
                return content;
            const reasoning = this.entries.get(`${modelScope}:${group}`)?.reasoning;
            if (!reasoning)
                return content;
            changed = true;
            return { ...content, parts: [{ text: reasoning, thought: true }, ...content.parts] };
        });
        return changed ? { ...body, contents } : body;
    }
}
exports.ReasoningReplayCache = ReasoningReplayCache;
exports.reasoningReplayCache = new ReasoningReplayCache();
//# sourceMappingURL=reasoningReplay.js.map