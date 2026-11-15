const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

async function runTests() {
    console.log('Running Chat Switch Model Refresh Tests...');
    const uiSrc = fs.readFileSync(path.join(__dirname, '..', 'bin', 'lib', 'patch', 'multi_account_ui.js'), 'utf8');

    let currentCid = 'chat-aaa-1111';
    let currentSelectedModel = 'Gemini 4 Hydrogen';
    const events = [];
    const fetchCalls = [];
    let resolveSetActive = null;

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
            accounts: [
                { email: 'user1@example.com', is_primary: true },
                { email: 'user2@example.com', is_primary: false },
            ],
            bindings: {
                'chat-aaa-1111': { email: 'user1@example.com', model: 'Gemini 4 Hydrogen' },
                'chat-bbb-2222': { email: 'user2@example.com', model: 'Gemini 3.8 Flash' },
                'chat-ccc-3333': { email: 'user2@example.com', model: '' },
            },
            active_default: 'user1@example.com',
        },
        __antigravityAvailableConfigs: [
            { label: 'Gemini 4 Hydrogen', modelOrAlias: { model: 'models/gemini-4-hydrogen' } },
            { label: 'Gemini 3.8 Flash', modelOrAlias: { model: 'models/gemini-3.8-flash' } },
        ],
        __antigravityGetSelectedModel: () => currentSelectedModel,
        __antigravitySelectModel: async (target, configs) => {
            const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
            const targetNorm = norm(target);
            const exists = configs.some(c => norm(c.label).includes(targetNorm) || targetNorm.includes(norm(c.label)));
            if (exists) {
                currentSelectedModel = target;
                return target;
            }
            // fallback to first config (e.g. Flash)
            const fallback = configs.find(c => /flash/i.test(c.label))?.label || configs[0]?.label || 'Gemini 3.8 Flash';
            currentSelectedModel = fallback;
            return fallback;
        },
        __antigravityFindTarget: () => ({ target: targetParent, insertAfter: null, floating: false }),
        __antigravityDetectCascadeId: () => currentCid,
        __antigravitySetHtml: (el, html) => { el.innerHTML = html; },
        innerWidth: 1200,
        innerHeight: 800,
        addEventListener: () => {},
        dispatchEvent: (ev) => { events.push({ type: ev.type, detail: ev.detail }); },
    };

    let clickListener = null;
    const sandbox = {
        window: windowObj,
        document: {
            body: { contains: () => true },
            activeElement: null,
            getElementById: (id) => (id === 'antigravity-account-pill' && pillEl.parentElement ? pillEl : null),
            createElement: () => pillEl,
            addEventListener: (type, fn) => {
                if (type === 'click') clickListener = fn;
            },
        },
        localStorage: { getItem: () => null },
        CustomEvent: function (type, init) { this.type = type; this.detail = init?.detail; },
        fetch: (url, opts) => {
            fetchCalls.push({ url, opts, body: opts?.body ? JSON.parse(opts.body) : null });
            if (url.endsWith('/api/multi-account/set-active')) {
                return new Promise((resolve) => {
                    resolveSetActive = () => resolve({ ok: true, json: async () => ({ ok: true }) });
                });
            }
            return Promise.resolve({
                ok: true,
                json: async () => windowObj.__AGY_INITIAL_STATE__,
            });
        },
        setTimeout,
        clearTimeout,
        setInterval: () => 0,
        MutationObserver: function () { this.observe = () => {}; },
        history: {},
        Promise,
        Set,
        Date,
        JSON,
    };

    vm.runInNewContext(uiSrc, sandbox);
    await new Promise(r => setTimeout(r, 10));

    // 1. Initial mount: should NOT emit antigravity:account-switched
    assert.strictEqual(events.length, 0, 'Initial mount should not dispatch account-switched');
    assert.strictEqual(pillEl.dataset.email, 'user1@example.com');

    // 2. Switch to chat-bbb-2222 (bound to user2@example.com, model Gemini 3.8 Flash)
    currentCid = 'chat-bbb-2222';
    windowObj.__antigravityRenderSelector();
    await new Promise(r => setTimeout(r, 120));
    assert.strictEqual(pillEl.dataset.email, 'user2@example.com');
    const setActiveCall = fetchCalls.find(c => c.url.endsWith('/api/multi-account/set-active'));
    assert(setActiveCall, 'set-active should be called on chat switch');
    assert.strictEqual(events.length, 0, 'account-switched must wait until set-active resolves');

    resolveSetActive();
    await new Promise(r => setTimeout(r, 200));
    assert.strictEqual(events.length, 1, 'account-switched should fire after set-active resolves');
    assert.strictEqual(events[0].type, 'antigravity:account-switched');
    assert.strictEqual(events[0].detail.email, 'user2@example.com');
    assert.strictEqual(events[0].detail.cascadeId, 'chat-bbb-2222');
    assert.strictEqual(currentSelectedModel, 'Gemini 3.8 Flash', 'Model must restore to Gemini 3.8 Flash');

    // 3. Switch back to chat-aaa-1111 (user1@example.com, model Gemini 4 Hydrogen)
    currentCid = 'chat-aaa-1111';
    windowObj.__antigravityRenderSelector();
    await new Promise(r => setTimeout(r, 120));
    if (resolveSetActive) resolveSetActive();
    await new Promise(r => setTimeout(r, 200));
    assert.strictEqual(events.length, 2, 'account-switched should fire on switch back to chat-aaa');
    assert.strictEqual(events[1].detail.email, 'user1@example.com');
    assert.strictEqual(currentSelectedModel, 'Gemini 4 Hydrogen', 'Model must restore to Gemini 4 Hydrogen');

    // 4. Test missing model fallback on account without Hydrogen
    // Change available configs to only include Gemini 3.8 Flash (e.g. Free account)
    windowObj.__antigravityAvailableConfigs = [
        { label: 'Gemini 3.8 Flash', modelOrAlias: { model: 'models/gemini-3.8-flash' } }
    ];
    // Create new chat-ddd-4444 bound to an account with Hydrogen saved, but available configs only has Flash
    sandbox.window.__AGY_INITIAL_STATE__.bindings['chat-ddd-4444'] = {
        email: 'user2@example.com',
        model: 'Gemini 4 Hydrogen'
    };
    currentCid = 'chat-ddd-4444';
    windowObj.__antigravityRenderSelector();
    await new Promise(r => setTimeout(r, 120));
    if (resolveSetActive) resolveSetActive();
    await new Promise(r => setTimeout(r, 200));
    assert.strictEqual(currentSelectedModel, 'Gemini 3.8 Flash', 'Model must fallback to available Flash when Hydrogen is missing');

    // 5. In-chat model change detection & persistence
    currentSelectedModel = 'Gemini 3.8 Flash (High)';
    if (clickListener) {
        clickListener({ target: { closest: () => null } });
    }
    await new Promise(r => setTimeout(r, 400));
    const bindCalls = fetchCalls.filter(c => c.url.endsWith('/api/multi-account/bind'));
    const lastBind = bindCalls[bindCalls.length - 1];
    assert(lastBind, 'Binding call must be recorded when model changes');
    assert.strictEqual(lastBind.body.model, 'Gemini 3.8 Flash (High)', 'Model update must be sent to router bind API');

    console.log('✓ Chat switch model refresh tests passed!');
}

runTests().catch((err) => {
    console.error(err);
    process.exit(1);
});
