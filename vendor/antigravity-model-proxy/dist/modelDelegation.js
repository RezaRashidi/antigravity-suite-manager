"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createModelDelegation = createModelDelegation;
const node_crypto_1 = require("node:crypto");
const customRequest_1 = require("./proxy/customRequest");
const providers_1 = require("./providers");
const INPUT_LIMIT = 64 * 1024;
const BODY_LIMIT = 256 * 1024;
const CONCURRENT_LIMIT = 4;
const PAGE_SIZE = 100;
function boundedWorkerModel(selected) {
    const defaultOutput = selected.contextWindow
        ? Math.min(4096, Math.max(1, Math.floor(selected.contextWindow / 4)))
        : 4096;
    const maxOutputTokens = Math.min(selected.maxOutputTokens ?? defaultOutput, 8192);
    const format = (0, providers_1.resolveApiFormat)(selected.provider, selected.apiFormat);
    const budget = (value) => format === 'anthropic'
        ? maxOutputTokens <= 1024
            ? 0
            : Math.min(value, maxOutputTokens - 1)
        : Math.min(value, maxOutputTokens);
    const model = {
        ...selected,
        fallbackModels: [],
        maxRetries: 0,
        timeout: Math.min(selected.timeout ?? 120000, 120000),
        retryBudgetMs: Math.min(selected.retryBudgetMs ?? 120000, 120000),
        maxOutputTokens,
        ...(selected.thinkingBudget === undefined ? {} : { thinkingBudget: budget(selected.thinkingBudget) }),
    };
    const thinking = selected.extraBody?.thinking;
    if (format === 'anthropic' && thinking && typeof thinking === 'object' && !Array.isArray(thinking)) {
        const options = thinking;
        if (options.type === 'enabled' && typeof options.budget_tokens === 'number') {
            const capped = budget(options.budget_tokens);
            model.extraBody = {
                ...selected.extraBody,
                thinking: capped === 0 ? { type: 'disabled' } : { ...options, budget_tokens: capped },
            };
        }
    }
    return model;
}
function respond(res, status, message) {
    if (res.destroyed || res.writableEnded)
        return;
    res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
    res.end(JSON.stringify({ error: { message } }));
}
/** Call only after the owned service's origin and bearer checks have passed. */
function createModelDelegation(loadModels) {
    let active = 0;
    return (req, res) => {
        if (!req.url?.startsWith('/_addon/delegation/'))
            return false;
        const url = new URL(req.url, 'http://127.0.0.1');
        if (req.method === 'GET' && url.pathname === '/_addon/delegation/models') {
            const cursors = url.searchParams.getAll('cursor');
            const cursor = cursors[0] ?? '0';
            if ([...url.searchParams.keys()].some((key) => key !== 'cursor') ||
                cursors.length > 1 ||
                !/^(0|[1-9]\d*)$/.test(cursor) ||
                !Number.isSafeInteger(Number(cursor))) {
                respond(res, 400, 'Use one non-negative integer cursor');
                return true;
            }
            const offset = Number(cursor);
            const enabled = loadModels().filter((model) => model.enabled !== false);
            const models = enabled.slice(offset, offset + PAGE_SIZE).map((model) => ({
                name: model.name,
                displayName: (model.displayName || model.name).slice(0, 256),
                description: typeof model.description === 'string' ? model.description.slice(0, 256) : '',
            }));
            res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
            res.end(JSON.stringify({
                models,
                mode: 'text-only',
                ...(offset + PAGE_SIZE < enabled.length ? { nextCursor: offset + PAGE_SIZE } : {}),
            }));
            return true;
        }
        if (req.method !== 'POST' || req.url !== '/_addon/delegation/run') {
            respond(res, 404, 'Unknown model delegation route');
            return true;
        }
        if (req.headers['content-type']?.split(';')[0] !== 'application/json') {
            respond(res, 415, 'Expected application/json');
            return true;
        }
        if (active >= CONCURRENT_LIMIT) {
            respond(res, 429, 'Four model delegations are already running. Wait for one to finish.');
            return true;
        }
        active++;
        void (async () => {
            let size = 0;
            const chunks = [];
            for await (const chunk of req) {
                size += chunk.length;
                if (size > BODY_LIMIT) {
                    respond(res, 413, 'Model delegation request exceeds 256 KiB');
                    return;
                }
                chunks.push(Buffer.from(chunk));
            }
            let input;
            try {
                input = JSON.parse(Buffer.concat(chunks).toString('utf8'));
            }
            catch {
                respond(res, 400, 'Invalid JSON');
                return;
            }
            if (!input ||
                typeof input !== 'object' ||
                Array.isArray(input) ||
                Object.keys(input).some((key) => !['model', 'prompt', 'context'].includes(key)) ||
                typeof input.model !== 'string' ||
                !input.model.trim() ||
                typeof input.prompt !== 'string' ||
                !input.prompt.trim() ||
                (input.context !== undefined && typeof input.context !== 'string')) {
                respond(res, 400, 'Use an exact saved model name, a non-empty prompt, and optional text context');
                return;
            }
            const context = (input.context || '');
            if (Buffer.byteLength(input.prompt, 'utf8') + Buffer.byteLength(context, 'utf8') > INPUT_LIMIT) {
                respond(res, 413, 'Prompt and context together must not exceed 64 KiB');
                return;
            }
            // Never interpret a copied native-child routing marker as this worker's model selection.
            if ((input.prompt + context).includes('[antigravity-subagent-route:')) {
                respond(res, 400, 'Native subagent routing markers cannot be used in MCP delegation');
                return;
            }
            const matches = loadModels().filter((model) => model.name === input.model && model.enabled !== false);
            if (matches.length !== 1) {
                respond(res, 400, 'Select one enabled configured model by its exact saved name using list_custom_models');
                return;
            }
            if (res.destroyed || res.writableEnded)
                return;
            const model = boundedWorkerModel(matches[0]);
            const id = `mcp-delegation-${(0, node_crypto_1.randomUUID)()}`;
            res.setHeader('X-Antigravity-Delegation-Id', id);
            // A new request contains only explicitly supplied context; it inherits no IDE history or tools.
            await (0, customRequest_1.runCustomModelRequest)(res, model, {
                conversationId: id,
                sessionId: id,
                systemInstruction: {
                    parts: [
                        {
                            text: 'You are an independent text-only worker. Complete the supplied task using only its supplied context. You have no tools, filesystem access, or parent conversation history. Return the result to the parent; do not claim to have run commands, edited files, or called tools.',
                        },
                    ],
                },
                contents: [
                    {
                        role: 'user',
                        parts: [
                            ...(context ? [{ text: `Context supplied by the parent:\n${context}` }] : []),
                            { text: `Task:\n${input.prompt}` },
                        ],
                    },
                ],
                generationConfig: { maxOutputTokens: model.maxOutputTokens },
            }, false, [model], false);
        })()
            .catch(() => {
            respond(res, 500, 'Model delegation could not be completed. Check the local proxy diagnostics.');
        })
            .finally(() => {
            active--;
        });
        return true;
    };
}
//# sourceMappingURL=modelDelegation.js.map