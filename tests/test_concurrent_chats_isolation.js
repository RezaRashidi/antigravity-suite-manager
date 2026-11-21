const assert = require('assert');
const fs = require('fs');
const http = require('http');
const os = require('os');
const path = require('path');
const vm = require('vm');

async function runTests() {
    console.log('Running Concurrent Chats Isolation & Model Catalog Regression Tests...');

    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'agy_concurrent_iso_'));
    const origAccountsDir = process.env.ANTIGRAVITY_ACCOUNTS_DIR;
    const origHome = process.env.REAL_HOME;
    const origTest = process.env.ANTIGRAVITY_TEST;

    process.env.ANTIGRAVITY_ACCOUNTS_DIR = tmpDir;
    process.env.REAL_HOME = tmpDir;
    process.env.ANTIGRAVITY_TEST = '1';

    const futureIso = new Date(Date.now() + 3600 * 1000).toISOString();
    fs.writeFileSync(path.join(tmpDir, 'paid@gmail.com.json'), JSON.stringify({
        email: 'paid@gmail.com',
        is_primary: false,
        license_status: 'ok',
        tier_type: 'Paid Pro',
        token: { access_token: 'tok-paid', refresh_token: 'rt-paid', expiry: futureIso },
    }, null, 2));
    fs.writeFileSync(path.join(tmpDir, 'free@gmail.com.json'), JSON.stringify({
        email: 'free@gmail.com',
        is_primary: false,
        license_status: 'ok',
        tier_type: 'Free',
        token: { access_token: 'tok-free', refresh_token: 'rt-free', expiry: futureIso },
    }, null, 2));

    const { startMultiAccountRouter } = require('../bin/lib/patch/router/server.js');
    const { setActiveAccount, setBinding, getBindings } = require('../bin/lib/patch/router/bindings.js');
    const { parseGroupsToBuckets } = require('../bin/lib/patch/router/telemetry.js');

    // 1. Telemetry: Argon group must stay separate from Gemini weekly bucket
    const buckets = parseGroupsToBuckets([
        {
            displayName: 'Gemini Models',
            buckets: [
                { bucketId: 'gemini-weekly', window: 'weekly', remainingFraction: 0.02, resetTime: '2026-11-26T12:00:00Z' },
                { bucketId: 'gemini-5h', window: '5h', remainingFraction: 1, resetTime: '2026-11-21T22:00:00Z' },
            ],
        },
        {
            displayName: 'Claude and GPT models',
            buckets: [
                { bucketId: '3p-weekly', window: 'weekly', remainingFraction: 1 },
            ],
        },
        {
            displayName: 'Gemini 4 Argon',
            buckets: [
                { bucketId: 'gemini-argon-wtu-weekly', displayName: 'Gemini 4 Argon Weekly Limit', window: 'weekly', remainingFraction: 0.75 },
            ],
        },
    ]);
    const gemW = buckets.find(b => b.family === 'gemini' && b.window === 'weekly');
    const argW = buckets.find(b => b.family === 'argon' && b.window === 'weekly');
    assert.strictEqual(gemW?.percent, 2, 'Gemini weekly quota must preserve 2%');
    assert.strictEqual(argW?.percent, 75, 'Argon weekly quota must be tracked separately without collision');
    console.log('✓ Argon quota separation verified');

    // 2. Router: fetchAvailableModels without cascadeId must stay on activeDefault and preserve Paid Pro model catalog
    const seenModelListAuth = [];
    const mockUpstream = http.createServer((req, res) => {
        if (req.url.includes('fetchAvailableModels')) {
            const auth = req.headers.authorization || '';
            seenModelListAuth.push(auth);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            if (auth === 'Bearer tok-paid') {
                return res.end(JSON.stringify({
                    models: {
                        'gemini-4-hydrogen-high': { displayName: 'Gemini 4 Hydrogen (High)', model: 'MODEL_PLACEHOLDER_M525' },
                        'gemini-3.8-flash-high': { displayName: 'Gemini 3.8 Flash (High)', model: 'MODEL_PLACEHOLDER_M318' },
                    },
                    agentModelSorts: [{ displayName: 'Recommended', groups: [{ modelIds: ['gemini-4-hydrogen-high', 'gemini-3.8-flash-high'] }] }],
                }));
            }
            return res.end(JSON.stringify({
                models: {
                    'gemini-3.8-flash-high': { displayName: 'Gemini 3.8 Flash (High)', model: 'MODEL_PLACEHOLDER_M318' },
                },
                agentModelSorts: [{ displayName: 'Recommended', groups: [{ modelIds: ['gemini-3.8-flash-high'] }] }],
            }));
        }
        res.writeHead(200, { 'Content-Type': 'text/event-stream' });
        res.end('data: {"candidates":[]}\n\n');
    });

    const postJson = (port, urlPath, body) => new Promise((resolve, reject) => {
        const s = JSON.stringify(body);
        const r = http.request({ hostname: '127.0.0.1', port, path: urlPath, method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(s) } }, (resp) => {
            let d = ''; resp.on('data', c => d += c);
            resp.on('end', () => resolve({ status: resp.statusCode, body: d }));
        });
        r.on('error', reject);
        r.write(s); r.end();
    });

    await new Promise(r => mockUpstream.listen(0, '127.0.0.1', r));
    const router = startMultiAccountRouter(0, {
        allowNewInstance: true,
        host: '127.0.0.1',
        upstreamProtocol: 'http:',
        upstreamHost: '127.0.0.1',
        upstreamPort: mockUpstream.address().port,
    });
    await new Promise(r => router.once('listening', r));

    try {
        const port = router.address().port;
        setBinding('chat-paid-1111', 'paid@gmail.com', 'gemini-4-hydrogen-high');
        setBinding('chat-free-2222', 'free@gmail.com', 'gemini-3.8-flash-high');
        setActiveAccount('paid@gmail.com');

        // Seed Paid Pro catalog first
        await postJson(port, '/v1internal:fetchAvailableModels', {});
        assert.strictEqual(seenModelListAuth[seenModelListAuth.length - 1], 'Bearer tok-paid');

        // Background Free chat runs generation (sets _lastCascadeId = chat-free-2222)
        await postJson(port, '/v1internal:streamGenerateContent?alt=sse', { cascadeId: 'chat-free-2222', request: { model: 'gemini-3.8-flash-high' } });

        // Subsequent global fetchAvailableModels ({} without cascadeId) must STILL stay on activeDefault (paid@gmail.com)
        await postJson(port, '/v1internal:fetchAvailableModels', {});
        assert.strictEqual(seenModelListAuth[seenModelListAuth.length - 1], 'Bearer tok-paid', 'Global fetchAvailableModels must not be hijacked by background chat');

        // Paid Pro chat receives background Sonar monitor call -> must NOT clobber gemini-4-hydrogen-high
        await postJson(port, '/v1internal:streamGenerateContent?alt=sse', { cascadeId: 'chat-paid-1111', request: { model: 'gemini-4-hydrogen-sonar' } });
        assert.strictEqual(getBindings()['chat-paid-1111'].model, 'gemini-4-hydrogen-high', 'Sonar model must not overwrite chat model');

        // When user actually views Free chat (activeDefault = free@gmail.com), fetchAvailableModels preserves M525 in models map for concurrent Paid Pro chats
        setActiveAccount('free@gmail.com');
        const freeModelsRes = await postJson(port, '/v1internal:fetchAvailableModels', {});
        const parsedFree = JSON.parse(freeModelsRes.body);
        assert.ok(parsedFree.models['gemini-4-hydrogen-high'], 'Merged catalog must retain MODEL_PLACEHOLDER_M525 for concurrent Paid Pro chats');
        assert.deepStrictEqual(parsedFree.agentModelSorts[0].groups[0].modelIds, ['gemini-3.8-flash-high'], 'UI dropdown list must stay scoped to Free account');
        console.log('✓ Router fetchAvailableModels isolation and catalog preservation verified');
    } finally {
        router.close();
        mockUpstream.close();
        try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
        if (origAccountsDir === undefined) delete process.env.ANTIGRAVITY_ACCOUNTS_DIR;
        else process.env.ANTIGRAVITY_ACCOUNTS_DIR = origAccountsDir;
        if (origHome === undefined) delete process.env.REAL_HOME;
        else process.env.REAL_HOME = origHome;
        if (origTest === undefined) delete process.env.ANTIGRAVITY_TEST;
        else process.env.ANTIGRAVITY_TEST = origTest;
    }

    // 3. UI: handleChatModelRestoration awaits active refresh, and passive MutationObserver/interval does not clobber saved model
    const uiSrc = fs.readFileSync(path.join(__dirname, '..', 'bin', 'lib', 'patch', 'multi_account_ui.js'), 'utf8');
    let currentCid = 'chat-paid-1111';
    let currentSelectedModel = 'Gemini 4 Hydrogen (High)';
    const bindCalls = [];
    let intervalFn = null;
    const pillEl = {
        id: 'antigravity-account-pill',
        dataset: {},
        className: '',
        innerHTML: '',
        parentElement: null,
        querySelector: () => null,
        querySelectorAll: () => [],
    };
    const targetParent = {
        appendChild: (el) => { el.parentElement = targetParent; },
        insertBefore: (el) => { el.parentElement = targetParent; },
    };
    const windowObj = {
        __AGY_ROUTER_HOST__: 'http://127.0.0.1:41999',
        __AGY_INITIAL_STATE__: {
            accounts: [{ email: 'paid@gmail.com' }, { email: 'free@gmail.com' }],
            bindings: {
                'chat-paid-1111': { email: 'paid@gmail.com', model: 'Gemini 4 Hydrogen (High)' },
                'chat-free-2222': { email: 'free@gmail.com', model: 'Gemini 3.8 Flash (High)' },
            },
            active_default: 'paid@gmail.com',
        },
        __antigravityAvailableConfigs: [{ label: 'Gemini 3.8 Flash (High)' }],
        __antigravityActiveRefreshPromise: null,
        __antigravityGetSelectedModel: () => currentSelectedModel,
        __antigravitySelectModel: async (target, configs) => {
            const exists = configs.some(c => c.label === target);
            currentSelectedModel = exists ? target : (configs[0]?.label || currentSelectedModel);
            return currentSelectedModel;
        },
        __antigravityFindTarget: () => ({ target: targetParent, insertAfter: null, floating: false }),
        __antigravityDetectCascadeId: () => currentCid,
        __antigravitySetHtml: (el, html) => { el.innerHTML = html; },
        addEventListener: () => {},
        dispatchEvent: (ev) => {
            if (ev.type === 'antigravity:account-switched') {
                windowObj.__antigravityActiveRefreshPromise = new Promise(resolve => {
                    setTimeout(() => {
                        windowObj.__antigravityAvailableConfigs = [{ label: 'Gemini 4 Hydrogen (High)' }, { label: 'Gemini 3.8 Flash (High)' }];
                        windowObj.__antigravityActiveRefreshPromise = null;
                        resolve();
                    }, 180);
                });
            }
        },
    };
    const sandbox = {
        window: windowObj,
        document: {
            hasFocus: () => true,
            body: { contains: () => true },
            activeElement: null,
            getElementById: (id) => (id === 'antigravity-account-pill' && pillEl.parentElement ? pillEl : null),
            createElement: () => pillEl,
            addEventListener: () => {},
        },
        localStorage: { getItem: () => null },
        CustomEvent: function (type, init) { this.type = type; this.detail = init?.detail; },
        fetch: (url, opts) => {
            if (url.endsWith('/api/multi-account/bind') && opts?.body) bindCalls.push(JSON.parse(opts.body));
            if (url.endsWith('/api/multi-account/set-active')) return Promise.resolve({ ok: true, json: async () => ({ ok: true }) });
            return Promise.resolve({ ok: true, json: async () => windowObj.__AGY_INITIAL_STATE__ });
        },
        setTimeout,
        clearTimeout,
        setInterval: (fn) => { intervalFn = fn; return 1; },
        MutationObserver: function () { this.observe = () => {}; },
        history: {},
        Promise,
        Set,
        Date,
        JSON,
    };

    vm.runInNewContext(uiSrc, sandbox);
    await new Promise(r => setTimeout(r, 20));

    // Switch to Free chat, then back to Paid chat while configs initially only had Free models
    currentCid = 'chat-free-2222';
    windowObj.__antigravityRenderSelector();
    await new Promise(r => setTimeout(r, 150));

    windowObj.__antigravityAvailableConfigs = [{ label: 'Gemini 3.8 Flash (High)' }];
    currentCid = 'chat-paid-1111';
    windowObj.__antigravityRenderSelector();
    await new Promise(r => setTimeout(r, 400));
    assert.strictEqual(currentSelectedModel, 'Gemini 4 Hydrogen (High)', 'Restoration must wait for refreshed configs and restore Hydrogen High');

    // Simulate background React glitch changing visible dropdown text without user click
    const bindsBeforeGlitch = bindCalls.length;
    currentSelectedModel = 'Gemini 3.8 Flash (High)';
    if (intervalFn) intervalFn();
    await new Promise(r => setTimeout(r, 50));
    assert.strictEqual(bindCalls.length, bindsBeforeGlitch, 'Passive interval/MutationObserver must NEVER overwrite saved model without user interaction');
    console.log('✓ UI restoration wait and passive clobber guard verified');

    console.log('✓ All concurrent chats isolation regression tests passed!');
}

runTests().catch((err) => {
    console.error(err);
    process.exit(1);
});
