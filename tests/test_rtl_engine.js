/**
 * Tests for Antigravity Suite Internal RTL Engine, Styles, Migration, and Multi-Account Coexistence.
 */
'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const engine = require('../bin/lib/patch/rtl/rtl_engine.js');
const styles = require('../bin/lib/patch/rtl/rtl_styles.js');
const patcher = require('../bin/lib/patch/rtl/patch_rtl.js');

// Lightweight DOM stub sufficient to exercise querySelectorAll, closest, tree walking, and attributes
function makeEl(tag, opts) {
    const o = opts || {};
    const attrs = new Map(Object.entries(o.attrs || {}));
    const el = {
        nodeType: 1,
        tagName: tag.toUpperCase(),
        id: o.id || '',
        className: o.className || '',
        value: o.value !== undefined ? o.value : '',
        parentElement: null,
        children: [],
        childNodes: [],
        isConnected: true,
        style: {},
        classList: {
            contains: (cls) => (` ${el.className} `).includes(` ${cls} `)
        },
        getAttribute: (k) => (attrs.has(k) ? attrs.get(k) : null),
        setAttribute: (k, v) => attrs.set(k, String(v)),
        removeAttribute: (k) => attrs.delete(k),
        hasAttribute: (k) => attrs.has(k),
        append: (...nodes) => {
            for (const n of nodes) {
                if (typeof n === 'string') {
                    el.childNodes.push({ nodeType: 3, nodeValue: n, parentElement: el });
                } else {
                    n.parentElement = el;
                    el.childNodes.push(n);
                    if (n.nodeType === 1) el.children.push(n);
                }
            }
            return el;
        },
        get textContent() {
            return el.childNodes.map((c) => (c.nodeType === 3 ? c.nodeValue : c.textContent)).join('');
        },
        set textContent(v) {
            el.children = [];
            el.childNodes = v ? [{ nodeType: 3, nodeValue: String(v), parentElement: el }] : [];
        },
        matches: (sel) => {
            const parts = sel.split(',').map((s) => s.trim()).filter(Boolean);
            for (const s of parts) {
                if (matchesSingle(el, s)) return true;
            }
            return false;
        },
        closest: (sel) => {
            let cur = el;
            while (cur) {
                if (cur.matches(sel)) return cur;
                cur = cur.parentElement;
            }
            return null;
        },
        querySelectorAll: (sel) => {
            const res = [];
            const visit = (node) => {
                for (const c of node.children) {
                    if (c.matches(sel)) res.push(c);
                    visit(c);
                }
            };
            visit(el);
            return res;
        },
        querySelector: (sel) => el.querySelectorAll(sel)[0] || null
    };
    if (o.id) attrs.set('id', o.id);
    if (o.children) el.append(...o.children);
    return el;
}

function matchesSingle(el, sel) {
    // Support descendant selectors like '[data-testid="user-input-step"] .whitespace-pre-wrap' or 'a > b'
    if (sel.includes(' > ')) {
        const idx = sel.lastIndexOf(' > ');
        const parentSel = sel.slice(0, idx).trim();
        const childSel = sel.slice(idx + 3).trim();
        return Boolean(el.parentElement && matchesSimple(el, childSel) && matchesSingle(el.parentElement, parentSel));
    }
    if (sel.includes(' ')) {
        const idx = sel.lastIndexOf(' ');
        const ancSel = sel.slice(0, idx).trim();
        const tailSel = sel.slice(idx + 1).trim();
        if (!matchesSimple(el, tailSel)) return false;
        let cur = el.parentElement;
        while (cur) {
            if (matchesSingle(cur, ancSel)) return true;
            cur = cur.parentElement;
        }
        return false;
    }
    return matchesSimple(el, sel);
}

function matchesSimple(el, sel) {
    if (!el || el.nodeType !== 1) return false;
    const tagMatch = sel.match(/^[a-zA-Z0-9]+/);
    if (tagMatch && el.tagName !== tagMatch[0].toUpperCase()) return false;
    const idMatch = sel.match(/#([a-zA-Z0-9_-]+)/);
    if (idMatch && el.id !== idMatch[1]) return false;
    for (const cm of sel.matchAll(/\.([a-zA-Z0-9_-]+)/g)) {
        if (!el.classList.contains(cm[1])) return false;
    }
    for (const am of sel.matchAll(/\[([^\]=^]+)(?:(\^?=)"([^"]*)")?\]/g)) {
        const val = el.getAttribute(am[1]);
        if (val === null) return false;
        if (am[2] === '=' && val !== am[3]) return false;
        if (am[2] === '^=' && !val.startsWith(am[3])) return false;
    }
    return true;
}

function runTests() {
    console.log('Running Antigravity Internal RTL Tests...');

    // 1. Code-stripped weighted text direction detection
    assert.strictEqual(engine.classifyText('سلام دنیا'), 'rtl');
    assert.strictEqual(engine.classifyText('Hello world'), 'ltr');
    assert.strictEqual(engine.classifyText('**Bug 1:** مشکل اینجاست که جدول می‌شکنه'), 'rtl', 'Should detect RTL despite English prefix');
    assert.strictEqual(engine.classifyText('GitHub API خطا داد و توکن برنگشت'), 'rtl', 'Should detect RTL despite leading acronym');
    assert.strictEqual(engine.classifyText('Fix bug in parser when streaming tokens'), 'ltr');
    assert.strictEqual(engine.classifyText('Check the word سلام in documentation only'), 'ltr', 'Single incidental Persian word in English sentence stays LTR');
    assert.strictEqual(engine.classifyText('فایل https://example.com/some/very/long/english/path/here باز شد'), 'rtl', 'URLs stripped before ratio');
    assert.strictEqual(engine.classifyText('مسیر /home/reza/.antigravity-suite-manager/bin/lib/sh/patch_rtl.sh بررسی شد'), 'rtl', 'Paths stripped before ratio');

    const mixedPara = makeEl('p', {
        children: [
            makeEl('code', { children: ['patch_rtl_v234_shim.js'] }),
            ' بررسی شد و مشکل حل گردید'
        ]
    });
    assert.strictEqual(engine.detectDirection(mixedPara), 'rtl', 'Inline <code> at start of Persian paragraph must be ignored');

    const pureCodePara = makeEl('p', {
        children: [makeEl('code', { children: ['npm run build'] })]
    });
    assert.strictEqual(engine.detectDirection(pureCodePara), 'ltr', 'Pure code paragraph stays LTR');

    // 2. Table RTL: reverses column direction on <table> while keeping .md-table-host & .md-table-scroll LTR!
    const doc = makeEl('body');
    doc.body = doc;
    doc.defaultView = null;
    doc.activeElement = null;

    const mdContainer = makeEl('div', { className: 'leading-relaxed md-divider-spacing' });
    const persianP = makeEl('p', { children: [makeEl('code', { children: ['app.asar'] }), ' با موفقیت پچ شد'] });
    const tableHost = makeEl('div', { className: 'group/md-table relative my-4 md-table-host', attrs: { 'data-width-mode': 'column' } });
    const tableScroll = makeEl('div', { className: 'w-full overflow-x-auto md-table-scroll' });
    const tableInner = makeEl('div', { attrs: { 'data-md-table': 't1' } });
    const faTable = makeEl('table', {
        children: [
            makeEl('thead', {
                children: [
                    makeEl('tr', {
                        children: [
                            makeEl('th', { children: ['نام فایل'] }),
                            makeEl('th', { children: ['وضعیت'] }),
                            makeEl('th', { children: ['تعداد'] })
                        ]
                    })
                ]
            }),
            makeEl('tbody', {
                children: [
                    makeEl('tr', {
                        children: [
                            makeEl('td', { children: [makeEl('code', { children: ['rtl_engine.js'] })] }),
                            makeEl('td', { children: ['سالم و فعال'] }),
                            makeEl('td', { children: ['12'] })
                        ]
                    })
                ]
            })
        ]
    });
    tableInner.append(faTable);
    tableScroll.append(tableInner);
    tableHost.append(tableScroll);

    const enTableHost = makeEl('div', { className: 'md-table-host' });
    const enTableScroll = makeEl('div', { className: 'md-table-scroll' });
    const enTable = makeEl('table', {
        children: [
            makeEl('thead', { children: [makeEl('tr', { children: [makeEl('th', { children: ['File'] }), makeEl('th', { children: ['Status'] })] })] }),
            makeEl('tbody', { children: [makeEl('tr', { children: [makeEl('td', { children: ['main.js'] }), makeEl('td', { children: ['OK'] })] })] })
        ]
    });
    enTableScroll.append(enTable);
    enTableHost.append(enTableScroll);

    const preBlock = makeEl('pre', { children: [makeEl('code', { children: ['// فارسی comment\nconst x = 1;'] })] });
    const listEl = makeEl('ul', {
        children: [
            makeEl('li', { children: ['مورد اول'] }),
            makeEl('li', { children: ['مورد دوم'] })
        ]
    });

    // User prompt bubble with @mention + hover action buttons (historical bubble)
    const userStep = makeEl('div', { attrs: { 'data-testid': 'user-input-step' } });
    const userBubbleCard = makeEl('div', { className: 'relative p-px rounded-xl bg-card-border' });
    const userBubble = makeEl('div', { attrs: { 'data-testid': 'user-message-bubble' }, className: 'relative flex flex-row items-center gap-2 p-1.5 bg-card' });
    const userScroll = makeEl('div', { className: 'flex-1 p-0.5' });
    const userPromptText = makeEl('div', {
        attrs: { 'data-quotable': 'true' },
        className: 'whitespace-pre-wrap text-sm',
        children: [
            makeEl('span', { className: 'context-scope-mention', children: ['very_long_english_filename_here.ts'] }),
            ' این فایل رو بررسی کن'
        ]
    });
    const userHoverBtns = makeEl('div', { className: 'user-input-buttons-container', children: [makeEl('button', { children: ['Copy'] })] });
    userScroll.append(userPromptText);
    userBubble.append(userScroll, userHoverBtns);
    userBubbleCard.append(userBubble);
    userStep.append(userBubbleCard);

    mdContainer.append(persianP, tableHost, enTableHost, preBlock, listEl);
    doc.append(userStep, mdContainer);

    engine.updateScope(doc, doc.body, { isRTL: true, forceRTL: false });

    assert.strictEqual(userStep.getAttribute('dir'), 'rtl', 'Historical Persian user-input-step must get dir="rtl"');
    assert.strictEqual(userBubble.getAttribute('dir'), 'rtl', 'User message bubble must get dir="rtl"');
    assert.strictEqual(userBubble.getAttribute('data-ag-rtl-bubble'), '1', 'Persian bubble must be tagged for physical right alignment');
    assert.strictEqual(userBubbleCard.getAttribute('data-ag-rtl-bubble'), '1', 'Bubble card wrapper must be tagged for physical right alignment');
    assert.strictEqual(userPromptText.getAttribute('dir'), 'rtl', 'Prompt text with @mention must ignore mention & get dir="rtl"');

    // English prompt bubble must stay LTR and NOT get RTL bubble tag
    const enStep = makeEl('div', { attrs: { 'data-testid': 'user-input-step' } });
    const enBubble = makeEl('div', { attrs: { 'data-testid': 'user-message-bubble' }, children: [makeEl('div', { className: 'whitespace-pre-wrap', children: ['Please check this build error'] })] });
    enStep.append(enBubble);
    engine.updateUserInputStep(enStep, false, true);
    assert.strictEqual(enStep.getAttribute('dir'), 'ltr');
    assert.strictEqual(enBubble.getAttribute('data-ag-rtl-bubble'), null, 'English prompt bubble stays on left');

    // Font autocomplete & OS font weight selector checks
    const osCatalog = {
        all: ['Arial', 'Dana', 'DanaNoEn', 'JetBrains Mono', 'Sahel', 'Vazirmatn', 'Verdana', 'Fira Code'],
        fa: ['Dana', 'DanaNoEn', 'Sahel', 'Vazirmatn'],
        en: ['Arial', 'Verdana'],
        code: ['Fira Code', 'JetBrains Mono'],
        weights: {
            dana: [400, 700],
            dananoen: [400, 700],
            sahel: [300, 400, 600, 700, 900]
        }
    };
    const faFiltered = styles.filterFonts(osCatalog, 'da', 'fa');
    assert.strictEqual(faFiltered[0], 'Dana', 'OS lang=fa prefix match must rank first for FA input');
    const codeFiltered = styles.filterFonts(osCatalog, '', 'code');
    assert.deepStrictEqual(codeFiltered, ['Fira Code', 'JetBrains Mono'], 'Empty Code input must list OS monospace fonts');
    const danaWeights = styles.getAvailableWeights(osCatalog, 'DanaNoEn');
    assert.deepStrictEqual(danaWeights.map((w) => w.value), ['', '400', '700'], 'Weight selector must show OS weights for selected font');
    const sahelWeights = styles.getAvailableWeights(osCatalog, 'Sahel');
    assert.deepStrictEqual(sahelWeights.map((w) => w.value), ['', '300', '400', '600', '700', '900']);
    const weightedCss = styles.buildDynamicCSS({ faFont: 'Sahel', fw: '500', lh: '2.1', fs: '20' }, '');
    assert.ok(weightedCss.includes('font-weight: 500 !important'), 'Custom fw must apply body font-weight override');
    assert.ok(weightedCss.includes('font-weight: 700 !important'), 'Custom fw must preserve stronger bold headings/strong');
    assert.ok(weightedCss.includes('[data-testid="user-input-step"] .whitespace-pre-wrap') && weightedCss.includes('font-size: 20px !important'), 'Font size must override Tailwind .text-sm on prompt bubbles & chat blocks');
    assert.ok(weightedCss.includes('line-height: 2.1 !important'), 'Line height must apply cleanly to chat blocks and spans');
    const stylesSrc = fs.readFileSync(path.join(__dirname, '../bin/lib/patch/rtl/rtl_styles.js'), 'utf8');
    assert.ok(!stylesSrc.includes('FA_FONT_BOOST_RE') && !stylesSrc.includes('CODE_FONT_BOOST_RE'), 'Must not hardcode font name regexes');

    // Best-practice check on UI app: panelSeen hides dot, no forced resize event
    const appUiSrc = fs.readFileSync(path.join(__dirname, '../bin/lib/patch/rtl/rtl_ui_app.js'), 'utf8');
    assert.ok(appUiSrc.includes('panelSeen'), 'App UI must persist panelSeen to dismiss topbar dot after first open');
    assert.ok(!appUiSrc.includes("new Event('resize')"), 'App UI must not trigger forced synchronous resize events');

    assert.strictEqual(persianP.getAttribute('dir'), 'rtl');
    assert.strictEqual(tableHost.getAttribute('dir'), null, '.md-table-host must NOT have dir');
    assert.strictEqual(tableScroll.getAttribute('dir'), null, '.md-table-scroll must NOT have dir');
    assert.strictEqual(faTable.getAttribute('dir'), 'rtl', 'Persian table gets dir="rtl" to reverse columns RTL');
    assert.strictEqual(enTable.getAttribute('dir'), 'ltr', 'English table keeps dir="ltr"');
    assert.strictEqual(preBlock.getAttribute('dir'), null, '<pre> must never get dir attribute');
    assert.strictEqual(listEl.getAttribute('dir'), 'rtl', 'Persian list gets dir="rtl"');

    // Force RTL keeps table wrappers clean and sets table & non-code cells RTL
    engine.updateScope(doc, doc.body, { isRTL: true, forceRTL: true });
    assert.strictEqual(tableHost.getAttribute('dir'), null);
    assert.strictEqual(tableScroll.getAttribute('dir'), null);
    assert.strictEqual(enTable.getAttribute('dir'), 'rtl', 'Force RTL reverses tables too');
    const enCells = enTable.querySelectorAll('th, td');
    assert.ok(enCells.every((c) => c.getAttribute('dir') === 'rtl'));

    // 3. CSS hygiene: zero :has(), zero global Tailwind overrides, Dana Regular + Bold @font-face matching
    const baseFontCss = styles.buildBaseFontCSS('AAA=');
    assert.ok(baseFontCss.includes('data:font/woff2;base64,AAA='), 'Base font-face builds separately once');
    const css = styles.buildDynamicCSS({ faFont: 'dana', lh: '1.6', fs: '16', forceRTL: true }, '');
    assert.ok(!css.includes('data:font/woff2'), 'Dynamic CSS omits static base64 font payload');
    const cssNoComments = css.replace(/\/\*[\s\S]*?\*\//g, '');
    assert.ok(!/:has\(/i.test(cssNoComments), 'RTL CSS must NOT use :has() selectors');
    assert.ok(!/\.w-11\b|\.h-6\b|\.h-7\b|\.bg-accent\b/.test(cssNoComments), 'RTL CSS must NOT override Tailwind utilities');
    assert.ok(css.includes('.md-table-host') && css.includes('table[dir="rtl"]'), 'RTL CSS must preserve .md-table-host LTR and fix table[dir="rtl"] borders');
    assert.ok(css.includes("local('Dana Regular')") && css.includes("local('Dana-Regular')"), 'User faFont must emit Regular FullName/PostScriptName for non-bold text');
    assert.ok(css.includes("local('Dana Bold')") && css.includes("local('Dana-Bold')"), 'User faFont must emit Bold FullName/PostScriptName');
    const danaNoEnCss = styles.buildDynamicCSS({ faFont: 'DanaNoEn Bold', lh: '1.6', fs: '16', forceRTL: false }, '');
    assert.ok(danaNoEnCss.includes("local('DanaNoEn Regular')") && danaNoEnCss.includes("local('DanaNoEn Bold')"), 'Must resolve both Regular & Bold for DanaNoEn');
    assert.ok(/font-weight:\s*600 699/.test(danaNoEnCss) && /font-weight:\s*700 799/.test(danaNoEnCss), 'Bold/SemiBold @font-face must cover font-weight 600-799');

    // 4. Migration & Multi-Account UI coexistence in dist/utils.js
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ag_rtl_test_'));
    try {
        const distDir = path.join(tmpDir, 'dist');
        fs.mkdirSync(distDir, { recursive: true });
        const utilsPath = path.join(distDir, 'utils.js');

        // Simulate legacy antigravity-rtl with nested MULTI_ACCOUNT_UI block
        const legacyUtils = `
async function invokeWindowLoadUrl(win, url) {
    try {
        /* ANTIGRAVITY RTL PATCH */
        win.webContents.on('console-message', () => {});
        /* MULTI_ACCOUNT_UI_START */
        const maMarker = 'KEEP_ME_ALIVE';
        /* MULTI_ACCOUNT_UI_END */
        win.webContents.on('dom-ready', () => {});
        await win.loadURL(url);
/* END ANTIGRAVITY RTL PATCH */
    } catch (e) {}
}
`;
        fs.writeFileSync(utilsPath, legacyUtils, 'utf8');

        patcher.patchApp(tmpDir);
        const patchedUtils = fs.readFileSync(utilsPath, 'utf8');
        assert.ok(patchedUtils.includes('/* MULTI_ACCOUNT_UI_START */') && patchedUtils.includes('KEEP_ME_ALIVE'), 'Migration must preserve nested MULTI_ACCOUNT_UI block');
        assert.ok(!patchedUtils.includes('/* ANTIGRAVITY RTL PATCH */'), 'Legacy RTL markers must be removed');
        assert.ok(patchedUtils.includes('/* ANTIGRAVITY_SUITE_RTL_START */'), 'Internal RTL hook must be installed');
        assert.ok(fs.existsSync(path.join(distDir, 'rtl', 'rtl_engine.js')), 'Internal RTL runtime assets must be copied');

        // Verify unpatch removes RTL completely while leaving MULTI_ACCOUNT_UI untouched
        patcher.unpatchApp(tmpDir);
        const unpatchedUtils = fs.readFileSync(utilsPath, 'utf8');
        assert.ok(!unpatchedUtils.includes('ANTIGRAVITY_SUITE_RTL'), 'Unpatch must strip internal RTL hook');
        assert.ok(unpatchedUtils.includes('KEEP_ME_ALIVE'), 'Unpatch must preserve Multi-Account UI hook');
        assert.ok(!fs.existsSync(path.join(distDir, 'rtl')), 'Unpatch must remove dist/rtl directory');
        assert.ok(unpatchedUtils.includes('await win.loadURL(url);'), 'Unpatch must preserve await win.loadURL(url)');
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }

    // 4b. Streaming chat update still runs while input has focus
    const streamDoc = makeEl('body');
    streamDoc.body = streamDoc;
    const listeners = {};
    streamDoc.addEventListener = (ev, cb) => { listeners[ev] = cb; };
    const chatBox = makeEl('div', { className: 'leading-relaxed', attrs: { 'data-testid': 'conversation-view' } });
    const streamP = makeEl('p', { children: ['API error... '] });
    chatBox.append(streamP);
    const inputBox = makeEl('div', { attrs: { contenteditable: 'true' }, children: [makeEl('p', { children: ['hello'] })] });
    streamDoc.append(chatBox, inputBox);
    streamDoc.activeElement = inputBox;

    let observedCb = null;
    class MockObserver {
        constructor(cb) { observedCb = cb; }
        observe() {}
        disconnect() {}
    }
    streamDoc.defaultView = { MutationObserver: MockObserver };

    const watcher = engine.createWatcher(streamDoc, () => ({ isRTL: true, forceRTL: false }));
    watcher.flushAll();
    assert.strictEqual(streamP.getAttribute('dir'), 'ltr');

    // Simulate streaming Persian chunk appended to streamP while inputBox stays focused
    streamP.append('مشکل برطرف شد و سیستم درست کار می‌کند');
    observedCb([{ type: 'characterData', target: streamP.childNodes[1], addedNodes: [] }]);

    setTimeout(() => {
        try {
            assert.strictEqual(streamP.getAttribute('dir'), 'rtl', 'Streaming chunk must flip block to RTL even while chat input is focused');
            watcher.disconnect();

            console.log('✓ Weighted code-stripped direction detection verified');
            console.log('✓ Streaming chat update while input focused verified');
            console.log('✓ Persian/LTR table column reversal & .md-table-host protection verified');
            console.log('✓ CSS zero-:has() & Tailwind safety verified');
            console.log('✓ Legacy migration + Multi-Account UI preservation verified');
            console.log('All Antigravity Internal RTL tests passed successfully!');
        } catch (err) {
            console.error(err);
            process.exit(1);
        }
    }, 220);
}

runTests();
