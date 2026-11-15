const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

async function runTests() {
    console.log('Running Chat Switch Model Refresh Tests...');
    const uiSrc = fs.readFileSync(path.join(__dirname, '..', 'bin', 'lib', 'patch', 'multi_account_ui.js'), 'utf8');

    let currentCid = 'chat-aaa-1111';
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
                { email: 'aireza2509@gmail.com', is_primary: true },
                { email: 'other@gmail.com', is_primary: false },
            ],
            bindings: {
                'chat-aaa-1111': 'aireza2509@gmail.com',
                'chat-bbb-2222': 'other@gmail.com',
                'chat-ccc-3333': 'other@gmail.com',
            },
            active_default: 'aireza2509@gmail.com',
        },
        __antigravityFindTarget: () => ({ target: targetParent, insertAfter: null, floating: false }),
        __antigravityDetectCascadeId: () => currentCid,
        __antigravitySetHtml: (el, html) => { el.innerHTML = html; },
        innerWidth: 1200,
        innerHeight: 800,
        addEventListener: () => {},
        dispatchEvent: (ev) => { events.push({ type: ev.type, detail: ev.detail }); },
    };

    const sandbox = {
        window: windowObj,
        document: {
            body: { contains: () => true },
            activeElement: null,
            getElementById: (id) => (id === 'antigravity-account-pill' && pillEl.parentElement ? pillEl : null),
            createElement: () => pillEl,
            addEventListener: () => {},
        },
        localStorage: { getItem: () => null },
        CustomEvent: function (type, init) { this.type = type; this.detail = init?.detail; },
        fetch: (url, opts) => {
            fetchCalls.push({ url, opts });
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
    assert.strictEqual(pillEl.dataset.email, 'aireza2509@gmail.com');

    // 2. Switch to chat-bbb-2222 (bound to other@gmail.com)
    currentCid = 'chat-bbb-2222';
    windowObj.__antigravityRenderSelector();
    await new Promise(r => setTimeout(r, 120));
    assert.strictEqual(pillEl.dataset.email, 'other@gmail.com');
    const setActiveCall = fetchCalls.find(c => c.url.endsWith('/api/multi-account/set-active'));
    assert(setActiveCall, 'set-active should be called on chat switch');
    assert.strictEqual(events.length, 0, 'account-switched must wait until set-active resolves');

    resolveSetActive();
    await new Promise(r => setTimeout(r, 10));
    assert.strictEqual(events.length, 1, 'account-switched should fire after set-active resolves');
    assert.strictEqual(events[0].type, 'antigravity:account-switched');
    assert.strictEqual(events[0].detail.email, 'other@gmail.com');
    assert.strictEqual(events[0].detail.cascadeId, 'chat-bbb-2222');

    // 3. Switch to chat-ccc-3333 (same account other@gmail.com) -> should NOT fire account-switched
    currentCid = 'chat-ccc-3333';
    windowObj.__antigravityRenderSelector();
    await new Promise(r => setTimeout(r, 120));
    if (resolveSetActive) resolveSetActive();
    await new Promise(r => setTimeout(r, 10));
    assert.strictEqual(events.length, 1, 'Switching to chat with same account should not re-trigger model refresh');

    console.log('✓ Chat switch model refresh tests passed!');
}

runTests().catch((err) => {
    console.error(err);
    process.exit(1);
});
