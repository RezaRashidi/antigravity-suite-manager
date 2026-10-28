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
exports.cloudflareRequest = exports.WorkersAiSetupError = void 0;
exports.checkedAccount = checkedAccount;
exports.checkedToken = checkedToken;
exports.expiresOn = expiresOn;
exports.isAccountWorkersModel = isAccountWorkersModel;
exports.setupWorkersAi = setupWorkersAi;
/** Optional Workers AI onboarding. Never runs inference or creates token managers. */
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const node_crypto_1 = require("node:crypto");
const modelManagement_1 = require("./modelManagement");
const modelStore_1 = require("./modelStore");
const cryptoStore = __importStar(require("./cryptoStore"));
const API = 'https://api.cloudflare.com/client/v4';
const ACCOUNT_SCOPE = 'com.cloudflare.api.account';
const ID = /^[a-f0-9]{32}$/i;
class WorkersAiSetupError extends Error {
}
exports.WorkersAiSetupError = WorkersAiSetupError;
const fail = (message) => new WorkersAiSetupError(message);
function checkedAccount(value) {
    if (typeof value !== 'string' || !ID.test(value))
        throw fail('Account ID must contain exactly 32 hexadecimal characters.');
    return value.toLowerCase();
}
function checkedToken(value) {
    if (typeof value !== 'string' || !/^[\x21-\x7e]{20,4096}$/.test(value) || value === '********')
        throw fail('Provide one valid token using the masked prompt, environment or token file.');
    return value;
}
function expiresOn(value, days = 90, now = Date.now()) {
    if (!Number.isInteger(days) || days < 1 || days > 365)
        throw fail('Expiry must be between 1 and 365 days.');
    const date = value === undefined ? new Date(now + days * 86400000) : new Date(value);
    if (value !== undefined &&
        (!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?Z$/.test(value) ||
            !Number.isFinite(date.getTime()) ||
            date.toISOString().replace('.000Z', 'Z') !== value.replace('.000Z', 'Z')))
        throw fail('Use a valid UTC ISO expiry, for example 2027-01-01T00:00:00Z.');
    if (date.getTime() <= now || date.getTime() > now + 365 * 86400000)
        throw fail('Expiry must be in the future and no more than 365 days away.');
    return date.toISOString();
}
/** Fixed origin, bounded response and deadline, no redirects or retries. */
const cloudflareRequest = async (route, token, method = 'GET', body) => {
    checkedToken(token);
    if (!/^\/(?:accounts(?:\/|\?)|user\/tokens\/verify$)/.test(route) || route.includes('#'))
        throw fail('Invalid Cloudflare API route.');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    try {
        const response = await fetch(API + route, {
            method,
            redirect: 'error',
            signal: controller.signal,
            headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
            ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        });
        if (!response.ok) {
            await response.body?.cancel();
            throw fail(`Cloudflare request failed (HTTP ${response.status}). Check token permissions and the selected account.`);
        }
        const reader = response.body?.getReader();
        if (!reader)
            throw fail('Cloudflare returned no response.');
        const chunks = [];
        let size = 0;
        while (true) {
            const next = await reader.read();
            if (next.done)
                break;
            size += next.value.length;
            if (size > 2 * 1024 * 1024) {
                await reader.cancel();
                throw fail('Cloudflare response exceeds 2 MiB.');
            }
            chunks.push(next.value);
        }
        const result = JSON.parse(Buffer.concat(chunks).toString('utf8'));
        if (!result || result.success !== true)
            throw fail('Cloudflare rejected the request. Check token permissions and the selected account.');
        return result;
    }
    catch (error) {
        if (error instanceof WorkersAiSetupError)
            throw error;
        throw fail('Cloudflare request failed or timed out. No request was retried.');
    }
    finally {
        clearTimeout(timer);
    }
};
exports.cloudflareRequest = cloudflareRequest;
async function paginated(route, token, request) {
    const items = [];
    const seen = new Set();
    const deadline = Date.now() + 30000;
    for (let page = 1; page <= 50; page++) {
        if (Date.now() >= deadline)
            throw fail('Cloudflare listing exceeded its time limit.');
        const response = await request(`${route}${route.includes('?') ? '&' : '?'}page=${page}&per_page=100`, token);
        if (!Array.isArray(response.result) ||
            response.result.some((item) => !item || typeof item !== 'object' || Array.isArray(item)))
            throw fail('Cloudflare returned an invalid list.');
        const info = response.result_info;
        if (info &&
            (typeof info !== 'object' || Object.values(info).some((n) => !Number.isSafeInteger(n) || Number(n) < 0)))
            throw fail('Cloudflare returned invalid pagination.');
        if (info?.page !== undefined && info.page !== page)
            throw fail('Cloudflare returned an unexpected page.');
        const signature = JSON.stringify(response.result);
        if (response.result.length && seen.has(signature))
            throw fail('Cloudflare repeated a page.');
        seen.add(signature);
        items.push(...response.result);
        if (items.length > 5000)
            throw fail('Cloudflare listing exceeds 5000 entries.');
        const more = info?.total_count !== undefined
            ? items.length < info.total_count
            : info?.total_pages !== undefined
                ? page < info.total_pages
                : response.result.length >= (info?.per_page || 100);
        if (!more)
            return items;
        if (!response.result.length)
            throw fail('Cloudflare returned an incomplete list.');
    }
    throw fail('Cloudflare listing exceeded 50 pages.');
}
function isAccountWorkersModel(model, account) {
    try {
        const url = new URL(model.apiUrl);
        const match = /^\/client\/v4\/accounts\/([a-fA-F0-9]{32})\/ai\/v1(?:\/chat\/completions)?\/?$/.exec(url.pathname);
        return (url.origin === 'https://api.cloudflare.com' &&
            !url.username &&
            !url.password &&
            !url.search &&
            !url.hash &&
            !!match &&
            match[1].toLowerCase() === checkedAccount(account));
    }
    catch {
        return false;
    }
}
function planModels(store, account, token, catalog, selected, rotate) {
    if (selected.length > 5000 ||
        selected.some((id) => typeof id !== 'string') ||
        new Set(selected).size !== selected.length)
        throw fail('Select distinct model IDs from the discovered catalog.');
    const existing = store.read();
    if (new Set(existing.map((entry) => entry.name)).size !== existing.length)
        throw fail('Resolve duplicate saved model names before onboarding.');
    const updates = new Map();
    const withToken = (model) => {
        const prepared = { ...(0, modelStore_1.redactModel)(model), apiKey: token };
        if (prepared.customHeaders && typeof prepared.customHeaders === 'object') {
            // A saved Authorization header overrides apiKey in the provider adapter.
            // Remove all old authentication aliases so the fresh apiKey is authoritative.
            prepared.customHeaders = Object.fromEntries(Object.entries(prepared.customHeaders).filter(([name]) => !/^(authorization|x-auth-key|x-auth-email)$/i.test(name)));
        }
        return prepared;
    };
    if (rotate)
        for (const model of existing)
            if (isAccountWorkersModel(model, account))
                updates.set(model.name, withToken(model));
    for (const id of selected) {
        const found = catalog.find((model) => model.id === id);
        if (!found)
            throw fail('A selected model is not in the current Workers AI catalog.');
        const matches = existing.filter((entry) => isAccountWorkersModel(entry, account) && entry.externalModelName === id);
        if (matches.length) {
            for (const model of matches)
                updates.set(model.name, withToken(model));
            continue;
        }
        const suffix = (0, node_crypto_1.createHash)('sha256').update(id).digest('hex').slice(0, 16);
        const name = `models/workers-ai-${account}-${suffix}`;
        if (existing.some((entry) => entry.name === name))
            throw fail('A generated model name conflicts with an existing entry; rename that entry first.');
        const metadata = {};
        for (const field of ['contextWindow', 'maxOutputTokens', 'supportsVision', 'supportsThinking'])
            if (found[field] !== undefined)
                metadata[field] = found[field];
        updates.set(name, {
            name,
            displayName: `${found.displayName} (Workers AI)`,
            description: `${id} via Cloudflare Workers AI`,
            provider: 'workers-ai',
            apiFormat: 'openai',
            apiUrl: `${API}/accounts/${account}/ai/v1/chat/completions`,
            externalModelName: id,
            enabled: true,
            apiKey: token,
            ...metadata,
        });
    }
    return [...updates.values()];
}
async function setupWorkersAi(options, dependencies = {}) {
    const request = dependencies.request || exports.cloudflareRequest;
    const now = dependencies.now || Date.now;
    const inputToken = checkedToken(options.token);
    if (!['existing', 'create', 'verify-only'].includes(options.mode))
        throw fail('Choose existing, create or verify-only.');
    if (options.selected !== undefined &&
        (!Array.isArray(options.selected) ||
            options.selected.length > 5000 ||
            options.selected.some((id) => typeof id !== 'string' || !id.trim()) ||
            new Set(options.selected).size !== options.selected.length))
        throw fail('Select distinct non-empty model IDs from the discovered catalog.');
    if (options.mode === 'verify-only' && (options.rotate || options.selected?.length || options.chooseModels))
        throw fail('verify-only cannot select, rotate or create models or tokens.');
    if (options.mode !== 'create' && (options.expires !== undefined || options.expiresInDays !== undefined))
        throw fail('Expiry options apply only to create mode.');
    const expiry = options.mode === 'create' ? expiresOn(options.expires, options.expiresInDays, now()) : undefined;
    if (options.mode === 'create' && !options.rotate && !options.selected?.length && !options.chooseModels)
        throw fail('Select models or rotation before creating a token.');
    // Refuse linked destinations before any token can be minted or encrypted.
    for (const filename of [
        options.dataDirectory,
        path.join(options.dataDirectory, 'custom_models.json'),
        path.join(options.dataDirectory, '.model-credentials-key'),
    ]) {
        if (fs.existsSync(filename) && fs.lstatSync(filename).isSymbolicLink())
            throw fail('Linked model or credential paths are not supported.');
    }
    let account = options.accountId ? checkedAccount(options.accountId) : undefined;
    if (!account) {
        if (options.mode !== 'create')
            throw fail('An Account ID is required when using an existing token.');
        const accounts = (await paginated('/accounts', inputToken, request)).map((item) => ({
            id: checkedAccount(item.id),
            name: typeof item.name === 'string'
                ? item.name
                    .split(inputToken)
                    .join('[redacted]')
                    .replace(/[\x00-\x1f\x7f]/g, '')
                    .slice(0, 120)
                : 'Cloudflare account',
        }));
        if (accounts.length === 1)
            account = accounts[0].id;
        else if (accounts.length && options.chooseAccount)
            account = checkedAccount(await options.chooseAccount(accounts));
        else
            throw fail('Specify --account-id when multiple or no accounts are listed. Account listing may require Account Settings Read.');
        if (!accounts.some((item) => item.id === account))
            throw fail('Choose an account from the returned account list.');
    }
    cryptoStore.configureCredentialDirectory(options.dataDirectory);
    const manager = dependencies.manager || (0, modelManagement_1.createModelManager)(options.dataDirectory, cryptoStore, async () => { });
    // Validate local configuration before token creation; never overwrite corrupt files.
    let existing;
    try {
        existing = manager.store.read();
    }
    catch {
        throw fail('The existing model configuration could not be read. Repair it before onboarding.');
    }
    if (new Set(existing.map((entry) => entry.name)).size !== existing.length)
        throw fail('Resolve duplicate saved model names before onboarding.');
    if (options.rotate &&
        !options.selected?.length &&
        !options.chooseModels &&
        !existing.some((entry) => isAccountWorkersModel(entry, account)))
        throw fail('No matching account entries to rotate; nothing was saved or created.');
    for (const id of options.selected || []) {
        const name = `models/workers-ai-${account}-${(0, node_crypto_1.createHash)('sha256').update(id).digest('hex').slice(0, 16)}`;
        if (!existing.some((entry) => isAccountWorkersModel(entry, account) && entry.externalModelName === id) &&
            existing.some((entry) => entry.name === name))
            throw fail('A generated model name conflicts with an existing entry; rename that entry first.');
    }
    let token = inputToken;
    let createdId;
    let creationAttempted = false;
    try {
        if (options.mode === 'create') {
            const groups = await paginated(`/accounts/${account}/tokens/permission_groups?name=Workers%20AI%20Write&scope=${ACCOUNT_SCOPE}`, inputToken, request);
            const eligible = groups.filter((group) => group?.name === 'Workers AI Write' &&
                typeof group.id === 'string' &&
                ID.test(group.id) &&
                group.is_selectable !== false &&
                Array.isArray(group.scopes) &&
                group.scopes.length === 1 &&
                group.scopes[0] === ACCOUNT_SCOPE);
            if (eligible.length !== 1)
                throw fail('Exactly one account-scoped Workers AI Write permission is required; no substitute permission was selected.');
            if (options.confirmCreate && !(await options.confirmCreate(account, expiry)))
                throw fail('Token creation cancelled; nothing was created.');
            const name = `antigravity-workers-ai-${new Date(now()).toISOString().replace(/[:.]/g, '-')}`;
            creationAttempted = true;
            const created = await request(`/accounts/${account}/tokens`, inputToken, 'POST', {
                name,
                expires_on: expiry,
                policies: [
                    {
                        effect: 'allow',
                        resources: { [`${ACCOUNT_SCOPE}.${account}`]: '*' },
                        permission_groups: [{ id: eligible[0].id }],
                    },
                ],
            });
            const result = created.result && typeof created.result === 'object' ? created.result : {};
            if (typeof result.id === 'string' && ID.test(result.id))
                createdId = result.id;
            if (!createdId || result.status !== 'active')
                throw fail('Cloudflare did not return a usable active token.');
            token = checkedToken(result.value);
            if (typeof result.expires_on !== 'string' || Date.parse(result.expires_on) !== Date.parse(expiry))
                throw fail('Cloudflare did not confirm the requested token expiry.');
        }
        // Catalog access verifies this token against the selected account without
        // generation, token-management rights or guessing account/user token types.
        let catalog;
        try {
            const discovered = await manager.discoverModels({
                provider: 'workers-ai',
                apiFormat: 'openai',
                apiUrl: `${API}/accounts/${account}/ai/v1/chat/completions`,
                apiKey: token,
            });
            if (!discovered.success || !Array.isArray(discovered.models))
                throw new Error();
            catalog = discovered.models;
            if (JSON.stringify(catalog).includes(token) || JSON.stringify(catalog).includes(inputToken))
                throw new Error();
        }
        catch {
            throw fail('Workers AI catalog access failed. Check the selected account and Workers AI token permissions; generation was not tested.');
        }
        if (options.mode === 'verify-only')
            return { accountId: account, catalog, saved: 0, verification: 'catalog-access-only', tokenCreated: false };
        const selected = options.chooseModels ? await options.chooseModels(catalog) : options.selected || [];
        const planned = planModels(manager.store, account, token, catalog, selected, options.rotate === true);
        if (!planned.length)
            throw fail('No models selected or matching account entries to rotate; nothing was saved.');
        try {
            manager.store.import(planned);
        }
        catch {
            throw fail('Model validation or encrypted atomic save failed; the model configuration was not partially updated.');
        }
        return {
            accountId: account,
            saved: planned.length,
            verification: 'catalog-access-only',
            tokenCreated: !!createdId,
            ...(createdId ? { tokenId: createdId, expiresOn: expiry } : {}),
        };
    }
    catch (error) {
        const safe = error instanceof WorkersAiSetupError ? error.message : 'Workers AI setup failed; no secret was printed.';
        if (createdId)
            throw fail(`${safe} Token ${createdId} was created but was not saved. Revoke that token in the Cloudflare account dashboard before retrying. Existing tokens were not revoked.`);
        if (creationAttempted)
            throw fail(`${safe} Token creation may have succeeded remotely; no automatic retry was made. Inspect account tokens in Cloudflare before retrying.`);
        throw fail(safe);
    }
}
//# sourceMappingURL=workersAiSetup.js.map