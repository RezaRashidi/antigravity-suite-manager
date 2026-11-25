// Test: Prompt Input Typing Performance & MutationObserver Isolation
const assert = require('assert');
const fs = require('fs');
const path = require('path');

function runTests() {
    console.log('Running Prompt Input Typing Performance & Isolation Tests...');

    // 1. Verify multi_account_ui.js ignores typing / contenteditable mutations
    const uiCode = fs.readFileSync(path.join(__dirname, '../bin/lib/patch/multi_account_ui.js'), 'utf8');
    assert.ok(uiCode.includes('contenteditable'), 'multi_account_ui.js should check for contenteditable');
    assert.ok(uiCode.includes('data-lexical-editor'), 'multi_account_ui.js should check for data-lexical-editor');
    assert.ok(uiCode.includes('monaco-editor'), 'multi_account_ui.js should check for monaco-editor');
    assert.ok(uiCode.includes('isRelevant'), 'multi_account_ui.js should filter mutations with isRelevant');
    assert.ok(uiCode.includes('document.activeElement'), 'multi_account_ui.js should guard interval with activeElement');
    assert.ok(uiCode.includes('renderSig'), 'multi_account_ui.js should skip redundant innerHTML rebuilds via renderSig');
    assert.ok(uiCode.includes('lastTypingTs'), 'multi_account_ui.js should fast-path exit during active typing');
    assert.ok(!uiCode.includes('30000'), 'multi_account_ui.js must NOT poll fetchState in background when dropdown is closed');
    console.log('✓ multi_account_ui.js typing mutation filter, renderSig & modal-only refresh verified');

    // 1c. Verify verify_url extraction, Free Pro vs Paid Pro tier classification, & error/logged-out/refresh-failed flyout states
    const { classifyHttpError } = require('../bin/lib/patch/router/accounts.js');
    const { classifyAccountTier } = require('../bin/lib/patch/router/telemetry.js');
    const paidTier = classifyAccountTier({
        'gemini-4-hydrogen-high': { displayName: 'Gemini 4 Hydrogen High', tagTitle: 'New' },
        'gemini-4-neon-high': { displayName: 'Gemini 4 Neon High', tagTitle: 'New' },
        'claude-opus-5-5-high': { displayName: 'Claude Opus 5.5 High', tagTitle: 'New' },
    });
    assert.strictEqual(paidTier.tierType, 'Paid Pro', 'Account with enabled 5-5/neon & no disabled notice must be Paid Pro');
    const freeProModels = {
        'gemini-4-hydrogen-high': { displayName: 'Gemini 4 Hydrogen High', tagTitle: 'New' },
        'gemini-4-neon-disabled': { displayName: 'Gemini 4 Neon', tagTitle: 'Paid Pro', tagDescription: 'Available on paid Google AI Pro and Ultra plans. Not included with your current plan.' },
    };
    for (let i = 0; i < 16; i++) freeProModels[`gemini-3-${i}`] = { displayName: `Model ${i}` };
    const freeProTier = classifyAccountTier(freeProModels);
    assert.strictEqual(freeProTier.tierType, 'Free Pro', 'Account with hydrogen New + -disabled Paid Pro notice must be Free Pro, NOT Paid Pro');
    const vRes = classifyHttpError(403, JSON.stringify({ error: { message: 'Please verify your account', details: [{ metadata: { validation_url: 'https://accounts.google.com/signin/continue?sarp=1' } }] } }));
    assert.strictEqual(vRes.reason, 'verify_required');
    assert.strictEqual(vRes.verifyUrl, 'https://accounts.google.com/signin/continue?sarp=1');
    const flyCode = fs.readFileSync(path.join(__dirname, '../bin/lib/patch/ui/flyout.js'), 'utf8');
    assert.ok(flyCode.includes('agy-flyout-verify-link'), 'flyout.js should render clickable verification link');
    assert.ok(flyCode.includes('Logged Out / Session Expired'), 'flyout.js should show logged-out state');
    assert.ok(flyCode.includes('Refresh Failed') && flyCode.includes('Not Refreshed (Cached)'), 'flyout.js should show refresh failure states');
    assert.ok(!uiCode.includes('showFly = async'), 'hovering an account item must not block UI with async handler');
    assert.ok(uiCode.includes('targetEmail') && uiCode.includes('inFlightByEmail'), 'refresh must trigger per-account only when hovering an account');
    console.log('✓ Paid/Free tier classification, verify_url extraction, per-account hover refresh & flyout states verified');

    // 1b. Verify styles.css has NO global :has() selectors (major Blink keystroke stall)
    const cssCode = fs.readFileSync(path.join(__dirname, '../bin/lib/patch/ui/styles.css'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
    assert.ok(!/:has\(/i.test(cssCode), 'styles.css must NOT contain :has() selectors (causes Blink style invalidation on every keystroke)');
    console.log('✓ styles.css zero :has() selector check verified');

    // 2. Verify mount.js eliminated forced synchronous reflows & duplicate observers
    const mountCode = fs.readFileSync(path.join(__dirname, '../bin/lib/patch/ui/mount.js'), 'utf8');
    assert.ok(!mountCode.includes('el.getBoundingClientRect().height > 0'), 'mount.js should NOT force reflow via getBoundingClientRect().height');
    assert.ok(!mountCode.includes('el.getBoundingClientRect().width > 0'), 'mount.js should NOT force reflow via getBoundingClientRect().width');
    assert.ok(mountCode.includes('__antigravityMountInit'), 'mount.js should guard against duplicate injection');
    assert.ok(mountCode.includes('footerHidden'), 'mount.js should track footerHidden state');
    assert.ok(mountCode.includes('footerMo.disconnect()'), 'mount.js should disconnect footerMo once hidden');
    assert.ok(mountCode.includes('disconnectFooterMo'), 'mount.js should auto-disconnect footerMo on bounded timeout');
    assert.ok(mountCode.includes('optimizeRtl'), 'mount.js should include RTL typing bypass');
    console.log('✓ mount.js reflow elimination & bounded footerMo disconnect verified');

    // 3. Verify antigravity-multi-account-ide.js target injection caching
    const ideCode = fs.readFileSync(path.join(__dirname, '../bin/lib/patch/antigravity-multi-account-ide.js'), 'utf8');
    assert.ok(ideCode.includes('target._agyInjected'), 'IDE patch should cache injected target to prevent IPC execution loop');
    assert.ok(ideCode.includes('4000') || ideCode.includes('5000'), 'IDE patch should relax scan interval to >= 4000ms');
    console.log('✓ antigravity-multi-account-ide.js IPC scan caching verified');

    // 4. Functional simulation of mount.js DOM queries
    const mockWindow = {
        addEventListener: () => {},
        removeEventListener: () => {}
    };
    const mockDocument = {
        querySelectorAll: (sel) => {
            if (sel === '[data-testid="model-selector-trigger"]') {
                return [{
                    closest: () => ({ parentElement: null }),
                    parentElement: { closest: () => ({ firstElementChild: {} }) }
                }];
            }
            if (sel === 'button[title="Reset State"], button[title*="Reset"]') {
                return [{
                    closest: () => ({ style: { setProperty: () => {} } }),
                    parentElement: null
                }];
            }
            return [];
        },
        querySelector: (sel) => {
            if (sel === '[data-testid="conversation-view"]') return { getAttribute: () => 'cascade-test-123' };
            return null;
        },
        getElementById: () => null,
        addEventListener: () => {}
    };

    global.window = mockWindow;
    global.document = mockDocument;

    // Load mount.js code in mock environment
    eval(mountCode);

    assert.strictEqual(typeof mockWindow.__antigravityDetectCascadeId, 'function');
    assert.strictEqual(mockWindow.__antigravityDetectCascadeId(), 'cascade-test-123');

    assert.strictEqual(typeof mockWindow.__antigravityFindTarget, 'function');
    const target = mockWindow.__antigravityFindTarget();
    assert.ok(target, 'Should find target without throwing or calling layout metrics');

    console.log('✓ Functional mount module simulation passed');
    console.log('All Prompt Input Typing Performance & Isolation tests passed successfully!');
    process.exit(0);
}

runTests();
