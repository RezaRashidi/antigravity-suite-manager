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
    console.log('✓ multi_account_ui.js typing mutation filter verified');

    // 2. Verify mount.js eliminated forced synchronous reflows
    const mountCode = fs.readFileSync(path.join(__dirname, '../bin/lib/patch/ui/mount.js'), 'utf8');
    assert.ok(!mountCode.includes('el.getBoundingClientRect().height > 0'), 'mount.js should NOT force reflow via getBoundingClientRect().height');
    assert.ok(!mountCode.includes('el.getBoundingClientRect().width > 0'), 'mount.js should NOT force reflow via getBoundingClientRect().width');
    assert.ok(mountCode.includes('footerHidden'), 'mount.js should track footerHidden state');
    assert.ok(mountCode.includes('footerMo.disconnect()'), 'mount.js should disconnect footerMo once hidden');
    assert.ok(mountCode.includes('optimizeRtl'), 'mount.js should include RTL typing bypass');
    console.log('✓ mount.js reflow elimination & footerMo disconnect verified');

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
