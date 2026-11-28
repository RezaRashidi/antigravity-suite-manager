/**
 * Antigravity Suite Internal RTL Direction Engine
 * Shared by Antigravity App, Antigravity IDE, and unit tests.
 */
(function (root) {
    'use strict';

    const ZERO_WIDTH_RE = /[\u200B-\u200F\u202A-\u202E\u2066-\u2069\uFEFF]/g;
    const RTL_CHAR_RE = /[\u0591-\u07FF\u08A0-\u08FF\uFB1D-\uFDFD\uFE70-\uFEFC]/;
    const LTR_CHAR_RE = /[A-Za-z\u00C0-\u024F\u0370-\u052F]/;
    const URL_RE = /[a-z][a-z0-9+.-]*:\/\/\S+/gi;
    const PATH_RE = /(?:~|\.{1,2})?(?:\/[\w.@+-]+){2,}/g;
    const FLAG_RE = /(?:^|\s)--?[A-Za-z0-9][A-Za-z0-9_.-]*/g;

    const SKIP_PROSE_TAGS = new Set(['PRE', 'CODE', 'KBD', 'SAMP', 'SVG', 'PATH', 'SCRIPT', 'STYLE', 'TEXTAREA']);
    const SKIP_PROSE_CLASS = /\b(?:katex|katex-display|monaco-editor|xterm|md-table-menu|markdown-alert-title|user-input-buttons-container|context-scope-mention)\b/;

    const EXCLUDED_ANCESTOR_SEL = [
        'pre', 'code', 'kbd', 'samp',
        '.monaco-editor', '.monaco-diff-editor',
        '.part.terminal', '.terminal-wrapper', '.xterm',
        '.katex',
        '[data-testid="markdown-table-menu"]',
        '.user-input-buttons-container',
        '#rtl-topbar-wrapper', '#rtl-dropdown-panel',
        '#antigravity-rtl-settings-panel', '#ag-rtl-font-menu',
        '#antigravity-account-pill', '#antigravity-account-dropdown'
    ].join(', ');

    const CHAT_CONTAINER_SEL = [
        '.leading-relaxed',
        '.prose',
        '.markdown-body',
        '.rendered-markdown',
        '[data-testid="conversation-view"]',
        '[data-testid="artifact-view"]',
        '[data-testid="commentable-content"]',
        '[data-aux-pane-open]',
        '[data-testid="user-input-step"]',
        '[data-testid="user-message-bubble"]',
        '[data-testid="chat-message"]'
    ].join(', ');

    const BLOCK_TAGS_SEL = [
        'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'li', 'blockquote', '.markdown-alert', 'summary', 'dt', 'dd',
        '.artifact-card > span.line-clamp-3',
        'label[for^="ask-opt-"]', 'div[role="radiogroup"] > div'
    ].join(', ');

    const UI_TITLE_SEL = [
        '[role="navigation"][aria-label="Sidebar"] .truncate',
        '[data-testid^="conversation-row-"] .truncate',
        '[data-testid="section-header"] .truncate',
        '[data-testid="breadcrumb-segment"] .truncate',
        '[data-testid="diff-view-mode-detail"]',
        '[data-aux-pane-open] .truncate[title]'
    ].join(', ');

    const BROAD_CONTAINER_SEL = [
        CHAT_CONTAINER_SEL,
        '[role="navigation"][aria-label="Sidebar"]',
        '[data-testid^="conversation-row-"]',
        '[data-testid="breadcrumb-segment"]',
        '.artifact-card',
        'table'
    ].join(', ');

    const DIRTY_TARGET_SEL = [
        'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', '.markdown-alert', '.artifact-card', 'table',
        '[data-testid="user-input-step"]', '[data-testid="user-message-bubble"]',
        '.leading-relaxed', '.prose', '.markdown-body', '.rendered-markdown',
        '[data-testid="chat-message"]', '[data-testid="conversation-view"]',
        '[data-testid="artifact-view"]', '[data-testid="commentable-content"]',
        '[data-aux-pane-open]', '[data-testid="breadcrumb-segment"]',
        '[data-testid^="conversation-row-"]', '[role="navigation"][aria-label="Sidebar"]'
    ].join(', ');

    const LIST_SEL = 'ul, ol';
    const TABLE_SEL = 'table';
    const INPUT_SEL = '[contenteditable="true"] p, [contenteditable="true"], textarea[data-testid="ask-question-writein"]';

    // O(1) WeakMap memoization for blocks, user prompt bubbles, and tables
    const blockMemo = new WeakMap();
    const stepMemo = new WeakMap();
    const tableMemo = new WeakMap();

    function setDir(el, dir) {
        if (!el || typeof el.getAttribute !== 'function') return;
        if (dir === null || dir === undefined) {
            if (el.hasAttribute('dir')) el.removeAttribute('dir');
            return;
        }
        if (el.getAttribute('dir') !== dir) el.setAttribute('dir', dir);
    }

    function setDataAttr(el, attr, val) {
        if (!el || typeof el.setAttribute !== 'function') return;
        if (val === null) {
            if (el.hasAttribute(attr)) el.removeAttribute(attr);
            return;
        }
        if (el.getAttribute(attr) !== val) el.setAttribute(attr, val);
    }

    function isOwnUiNode(node) {
        if (!node) return false;
        const el = node.nodeType === 1 ? node : node.parentElement;
        if (!el) return false;
        const id = el.id || '';
        if (id.startsWith('antigravity-rtl') || id.startsWith('rtl-') || id.startsWith('ag-rtl-')) return true;
        return Boolean(el.closest && el.closest('#rtl-topbar-wrapper, #rtl-dropdown-panel, #antigravity-rtl-settings-panel, #ag-rtl-font-menu, #antigravity-account-pill, #antigravity-account-dropdown'));
    }

    function isExcluded(el) {
        if (!el || el.nodeType !== 1) return true;
        if (SKIP_PROSE_TAGS.has(el.tagName)) return true;
        if (el.classList && (el.classList.contains('md-table-host') || el.classList.contains('md-table-scroll'))) return true;
        if (el.hasAttribute && el.hasAttribute('data-md-table')) return true;
        if (el.closest && el.closest(EXCLUDED_ANCESTOR_SEL)) return true;
        return false;
    }

    function extractProseText(node, limit) {
        const cap = limit || 600;
        let out = '';
        function walk(cur) {
            if (!cur || out.length >= cap) return;
            if (cur.nodeType === 3) {
                out += cur.nodeValue || '';
                return;
            }
            if (cur.nodeType !== 1) return;
            if (SKIP_PROSE_TAGS.has(cur.tagName)) return;
            const cls = typeof cur.className === 'string' ? cur.className : '';
            if (cls && SKIP_PROSE_CLASS.test(cls)) return;
            if (!cur.children || cur.children.length === 0) {
                out += cur.textContent || '';
                return;
            }
            const children = cur.childNodes || [];
            for (let i = 0; i < children.length && out.length < cap; i++) {
                walk(children[i]);
            }
        }
        walk(node);
        return out;
    }

    function classifyText(rawText) {
        if (!rawText) return null;
        const cleaned = rawText
            .replace(ZERO_WIDTH_RE, '')
            .replace(URL_RE, ' ')
            .replace(PATH_RE, ' ')
            .replace(FLAG_RE, ' ');

        let firstStrong = null;
        let rtlCount = 0;
        let ltrCount = 0;

        for (let i = 0; i < cleaned.length && (rtlCount + ltrCount) < 400; i++) {
            const ch = cleaned[i];
            if (RTL_CHAR_RE.test(ch)) {
                if (!firstStrong) firstStrong = 'rtl';
                rtlCount++;
            } else if (LTR_CHAR_RE.test(ch)) {
                if (!firstStrong) firstStrong = 'ltr';
                ltrCount++;
            }
        }

        if (rtlCount === 0 && ltrCount === 0) return null;
        if (rtlCount === 0) return 'ltr';
        if (firstStrong === 'rtl') return 'rtl';
        if (rtlCount >= 2 && (rtlCount / (rtlCount + ltrCount)) >= 0.25) return 'rtl';
        return 'ltr';
    }

    function detectDirection(el) {
        if (!el) return null;
        const prose = extractProseText(el, 600);
        const dir = classifyText(prose);
        if (dir !== null) return dir;
        const full = (el.textContent || '').replace(ZERO_WIDTH_RE, '');
        if (LTR_CHAR_RE.test(full) && !RTL_CHAR_RE.test(full)) return 'ltr';
        return null;
    }

    function detectWithMemo(el, isRTL, forceRTL, defaultDir) {
        const textLen = (el.textContent || '').length;
        const childCnt = el.children ? el.children.length : 0;
        const sig = `${isRTL ? 1 : 0}:${forceRTL ? 1 : 0}:${textLen}:${childCnt}`;
        const prev = blockMemo.get(el);
        if (prev && prev.sig === sig && el.getAttribute('dir') === prev.dir) {
            return prev.dir;
        }
        let dir;
        if (!isRTL) {
            dir = 'ltr';
        } else if (forceRTL) {
            dir = 'rtl';
        } else if (el.classList && el.classList.contains('markdown-alert-title')) {
            const alertHost = el.closest && el.closest('.markdown-alert');
            dir = (alertHost && detectDirection(alertHost)) || defaultDir;
        } else {
            dir = detectDirection(el) || defaultDir;
        }
        setDir(el, dir);
        blockMemo.set(el, { sig, dir });
        return dir;
    }

    function queryWithinScope(doc, scopeEl, selector) {
        if (!scopeEl || scopeEl === doc || scopeEl === doc.body) {
            return Array.from(doc.querySelectorAll(selector));
        }
        const results = [];
        if (scopeEl.matches && scopeEl.matches(selector)) results.push(scopeEl);
        if (scopeEl.querySelectorAll) {
            const inner = scopeEl.querySelectorAll(selector);
            for (let i = 0; i < inner.length; i++) results.push(inner[i]);
        }
        return results;
    }

    function keepTopmostElements(elements) {
        if (elements.length <= 1) return elements;
        const set = new Set(elements);
        const out = [];
        for (let i = 0; i < elements.length; i++) {
            const el = elements[i];
            let nested = false;
            let cur = el.parentElement;
            while (cur) {
                if (set.has(cur)) { nested = true; break; }
                cur = cur.parentElement;
            }
            if (!nested) out.push(el);
        }
        return out;
    }

    function updateInputElement(el, forceRTL, isRTL) {
        if (!el || !el.tagName) return;
        const raw = el.tagName === 'TEXTAREA' ? el.value : el.textContent;
        const text = (raw || '').replace(ZERO_WIDTH_RE, '').trim();
        if (!isRTL) {
            setDir(el, 'ltr');
            return;
        }
        if (text.length === 0) {
            setDir(el, forceRTL ? 'rtl' : null);
            return;
        }
        setDir(el, forceRTL ? 'rtl' : (classifyText(text) || 'ltr'));
    }

    function updateInputs(doc, scopeEl, forceRTL, isRTL) {
        const inputs = queryWithinScope(doc, scopeEl, INPUT_SEL);
        for (let i = 0; i < inputs.length; i++) {
            updateInputElement(inputs[i], forceRTL, isRTL);
        }
    }

    function updateUserInputStep(stepOrBubbleEl, forceRTL, isRTL) {
        if (!stepOrBubbleEl || isExcluded(stepOrBubbleEl)) return;
        const stepEl = (stepOrBubbleEl.closest && stepOrBubbleEl.closest('[data-testid="user-input-step"]')) || stepOrBubbleEl;
        const bubbleEl = (stepEl.matches && stepEl.matches('[data-testid="user-message-bubble"]'))
            ? stepEl
            : (stepEl.querySelector ? stepEl.querySelector('[data-testid="user-message-bubble"]') : null);
        const textEl =
            (stepEl.querySelector && (
                stepEl.querySelector('[data-quotable="true"]') ||
                stepEl.querySelector('.whitespace-pre-wrap')
            )) || bubbleEl || stepEl;

        const sig = `${isRTL ? 1 : 0}:${forceRTL ? 1 : 0}:${(textEl.textContent || '').length}`;
        const prev = stepMemo.get(stepEl);
        if (prev && prev.sig === sig && stepEl.getAttribute('dir') === prev.dir) {
            return;
        }

        const dir = !isRTL
            ? 'ltr'
            : (forceRTL ? 'rtl' : (detectDirection(textEl) || detectDirection(stepEl) || 'ltr'));

        setDir(stepEl, dir);
        if (bubbleEl && bubbleEl !== stepEl) setDir(bubbleEl, dir);
        if (textEl && textEl !== stepEl && textEl !== bubbleEl) setDir(textEl, dir);

        // Tag the bubble and its intermediate wrappers up to user-input-step so RTL bubbles snap to the physical right edge
        const rtlFlag = (isRTL && dir === 'rtl') ? '1' : null;
        if (bubbleEl) {
            let cur = bubbleEl;
            let depth = 0;
            while (cur && depth < 5) {
                setDataAttr(cur, 'data-ag-rtl-bubble', rtlFlag);
                if (cur === stepEl) break;
                cur = cur.parentElement;
                depth++;
            }
        } else {
            setDataAttr(stepEl, 'data-ag-rtl-bubble', rtlFlag);
        }
        // If Antigravity wraps user-input-step inside an outer rounded card, align that card right too
        const outerCard = stepEl.parentElement;
        if (outerCard && outerCard.getAttribute && outerCard.getAttribute('data-testid') !== 'conversation-view' &&
            /\b(?:rounded|bg-card|max-w-)/.test(outerCard.className || '')) {
            setDataAttr(outerCard, 'data-ag-rtl-bubble', rtlFlag);
        }

        stepMemo.set(stepEl, { sig, dir });
    }

    function updateTable(table, forceRTL, isRTL) {
        if (!table || isExcluded(table)) return;
        const host = table.closest ? table.closest('.md-table-host') : null;
        const scroll = table.closest ? table.closest('.md-table-scroll') : null;
        const inner = table.closest ? table.closest('[data-md-table]') : null;
        if (host && host.hasAttribute('dir')) host.removeAttribute('dir');
        if (scroll && scroll.hasAttribute('dir')) scroll.removeAttribute('dir');
        if (inner && inner.hasAttribute('dir')) inner.removeAttribute('dir');

        const cells = Array.from(table.querySelectorAll('th, td'));
        const sig = `${isRTL ? 1 : 0}:${forceRTL ? 1 : 0}:${cells.length}:${(table.textContent || '').length}`;
        const prev = tableMemo.get(table);
        if (prev && prev.sig === sig && table.getAttribute('dir') === prev.dir) {
            return;
        }

        if (!isRTL) {
            setDir(table, 'ltr');
            for (let i = 0; i < cells.length; i++) setDir(cells[i], 'ltr');
            tableMemo.set(table, { sig, dir: 'ltr' });
            return;
        }

        const cellDirs = new Array(cells.length);
        let rtlCells = 0;
        let ltrCells = 0;
        let rtlHeaders = 0;
        let ltrHeaders = 0;

        for (let i = 0; i < cells.length; i++) {
            const cell = cells[i];
            const d = detectDirection(cell);
            cellDirs[i] = d;
            if (d === 'rtl') {
                rtlCells++;
                if (cell.tagName === 'TH') rtlHeaders++;
            } else if (d === 'ltr') {
                ltrCells++;
                if (cell.tagName === 'TH') ltrHeaders++;
            }
        }

        let tableDir = 'ltr';
        if (forceRTL) {
            tableDir = 'rtl';
        } else if (rtlCells > 0 && (rtlCells >= ltrCells || (rtlHeaders > 0 && rtlHeaders >= ltrHeaders))) {
            tableDir = 'rtl';
        }

        setDir(table, tableDir);

        for (let i = 0; i < cells.length; i++) {
            const cell = cells[i];
            if (forceRTL) {
                const firstChild = cell.firstElementChild || (cell.children && cell.children[0]) || null;
                const onlyCode = Boolean(
                    firstChild &&
                    cell.children &&
                    cell.children.length === 1 &&
                    (firstChild.tagName === 'CODE' || firstChild.tagName === 'PRE') &&
                    cell.textContent.trim() === firstChild.textContent.trim()
                );
                setDir(cell, onlyCode ? 'ltr' : 'rtl');
            } else {
                setDir(cell, cellDirs[i] || tableDir);
            }
        }

        tableMemo.set(table, { sig, dir: tableDir });
    }

    function orientList(list, forceRTL, isRTL) {
        if (!isRTL) {
            setDir(list, 'ltr');
            return;
        }
        if (forceRTL) {
            setDir(list, 'rtl');
            return;
        }
        let rtlLi = 0;
        let ltrLi = 0;
        const children = list.children || [];
        for (let j = 0; j < children.length; j++) {
            if (children[j].tagName !== 'LI') continue;
            const ld = children[j].getAttribute('dir');
            if (ld === 'rtl') rtlLi++;
            else if (ld === 'ltr') ltrLi++;
        }
        if (rtlLi > 0 && rtlLi >= ltrLi) setDir(list, 'rtl');
        else if (ltrLi > 0) setDir(list, 'ltr');
        else {
            const fallback = detectDirection(list);
            if (fallback) setDir(list, fallback);
        }
    }

    function updateUiTitles(doc, rootEl, forceRTL, isRTL) {
        const seen = new Set();
        const applyTitle = (el) => {
            if (!el || seen.has(el) || isExcluded(el) || isOwnUiNode(el)) return;
            seen.add(el);
            detectWithMemo(el, isRTL, forceRTL, 'ltr');
        };

        const direct = queryWithinScope(doc, rootEl, UI_TITLE_SEL);
        for (let i = 0; i < direct.length; i++) applyTitle(direct[i]);

        // Artifact card prose summary (any span/p/leaf div outside .pointer-events-none filename row & buttons)
        const cards = queryWithinScope(doc, rootEl, '.artifact-card');
        for (let i = 0; i < cards.length; i++) {
            const cardNodes = queryWithinScope(doc, cards[i], 'span, p, div');
            for (let j = 0; j < cardNodes.length; j++) {
                const cn = cardNodes[j];
                if (cn === cards[i] || seen.has(cn) || isExcluded(cn) || isOwnUiNode(cn)) continue;
                if (cn.closest && cn.closest('button, .pointer-events-none')) continue;
                if (cn.classList && cn.classList.contains('pointer-events-none')) continue;
                if (cn.querySelector && cn.querySelector('span, p, div, button')) continue;
                seen.add(cn);
                detectWithMemo(cn, isRTL, forceRTL, 'auto');
            }
        }

        // Leaf prose divs inside Artifact Viewer (e.g. raw markdown / CodeFileViewer lines without <p>)
        const artRoots = queryWithinScope(doc, rootEl, '[data-testid="artifact-view"], [data-testid="commentable-content"]');
        for (let i = 0; i < artRoots.length; i++) {
            const artDivs = queryWithinScope(doc, artRoots[i], 'div');
            for (let j = 0; j < artDivs.length; j++) {
                const dv = artDivs[j];
                if (dv === artRoots[i] || seen.has(dv) || isExcluded(dv) || isOwnUiNode(dv)) continue;
                if (dv.closest && dv.closest('button, .pointer-events-none, table')) continue;
                if (dv.querySelector && dv.querySelector('p, h1, h2, h3, h4, h5, h6, ul, ol, table, blockquote, pre, div, button')) continue;
                if (!(dv.textContent || '').trim()) continue;
                seen.add(dv);
                detectWithMemo(dv, isRTL, forceRTL, 'auto');
            }
        }

        // "For Turn" Review filter chip: [div "For Turn", div.truncate[title], button[aria-label="Clear filter"]]
        const clearBtns = queryWithinScope(doc, rootEl, 'button[aria-label="Clear filter"]');
        for (let i = 0; i < clearBtns.length; i++) {
            const prev = clearBtns[i].previousElementSibling;
            if (prev && prev.tagName === 'DIV') applyTitle(prev);
        }

        // Home screen Recent Conversations list (UKa/DKa) shares container with "Search conversations..."
        const searchInputs = queryWithinScope(doc, rootEl, 'input[placeholder="Search conversations..."]');
        for (let i = 0; i < searchInputs.length; i++) {
            const host = searchInputs[i].parentElement && searchInputs[i].parentElement.parentElement;
            if (!host) continue;
            const homeTitles = queryWithinScope(doc, host, '.truncate');
            for (let j = 0; j < homeTitles.length; j++) applyTitle(homeTitles[j]);
        }
    }

    function updateScope(doc, scopeEl, opts) {
        const isRTL = opts && opts.isRTL !== false;
        const forceRTL = Boolean(opts && opts.forceRTL);
        const skipInputs = Boolean(opts && opts.skipInputs);
        const rootEl = scopeEl || doc.body;
        if (!rootEl) return;

        if (!skipInputs) {
            updateInputs(doc, rootEl, forceRTL, isRTL);
        }

        // Fast targeted paths for incremental dirty roots
        if (rootEl.matches) {
            if (rootEl.matches('table')) {
                updateTable(rootEl, forceRTL, isRTL);
                return;
            }
            if (rootEl.matches('[data-testid="user-input-step"], [data-testid="user-message-bubble"]')) {
                updateUserInputStep(rootEl, forceRTL, isRTL);
                return;
            }
            if (rootEl.matches('p, h1, h2, h3, h4, h5, h6, li, blockquote, .markdown-alert, .artifact-card > span.line-clamp-3') && !isExcluded(rootEl)) {
                if (!(rootEl.closest && rootEl.closest('table'))) {
                    detectWithMemo(rootEl, isRTL, forceRTL, 'auto');
                }
                const parentList = rootEl.tagName === 'LI' && rootEl.parentElement;
                if (parentList && (parentList.tagName === 'UL' || parentList.tagName === 'OL')) {
                    orientList(parentList, forceRTL, isRTL);
                }
                return;
            }
        }

        let containers = [];
        if (rootEl.closest && rootEl.closest(CHAT_CONTAINER_SEL)) {
            containers = [rootEl];
        } else {
            containers = keepTopmostElements(queryWithinScope(doc, rootEl, CHAT_CONTAINER_SEL));
        }

        const seenBlocks = new Set();
        const seenLists = new Set();
        const seenTables = new Set();
        const seenSteps = new Set();

        for (let c = 0; c < containers.length; c++) {
            const container = containers[c];

            const userSteps = queryWithinScope(doc, container, '[data-testid="user-input-step"], [data-testid="user-message-bubble"]');
            for (let i = 0; i < userSteps.length; i++) {
                const st = (userSteps[i].closest && userSteps[i].closest('[data-testid="user-input-step"]')) || userSteps[i];
                if (seenSteps.has(st)) continue;
                seenSteps.add(st);
                updateUserInputStep(st, forceRTL, isRTL);
            }

            const blocks = queryWithinScope(doc, container, BLOCK_TAGS_SEL);
            for (let i = 0; i < blocks.length; i++) {
                const el = blocks[i];
                if (seenBlocks.has(el)) continue;
                seenBlocks.add(el);
                if (isExcluded(el)) continue;
                if (el.closest && el.closest('table')) continue;
                detectWithMemo(el, isRTL, forceRTL, 'auto');
            }

            const lists = queryWithinScope(doc, container, LIST_SEL);
            for (let i = 0; i < lists.length; i++) {
                const list = lists[i];
                if (seenLists.has(list)) continue;
                seenLists.add(list);
                if (isExcluded(list)) continue;
                orientList(list, forceRTL, isRTL);
            }

            const tables = queryWithinScope(doc, container, TABLE_SEL);
            for (let i = 0; i < tables.length; i++) {
                const tbl = tables[i];
                if (seenTables.has(tbl)) continue;
                seenTables.add(tbl);
                updateTable(tbl, forceRTL, isRTL);
            }
        }

        updateUiTitles(doc, rootEl, forceRTL, isRTL);
    }

    function clearAll(doc) {
        const rootEl = doc.body || doc.documentElement;
        if (!rootEl) return;
        const targets = rootEl.querySelectorAll('[dir], [data-ag-rtl-bubble]');
        for (let i = 0; i < targets.length; i++) {
            if (!isOwnUiNode(targets[i])) {
                targets[i].removeAttribute('dir');
                targets[i].removeAttribute('data-ag-rtl-bubble');
            }
        }
    }

    function createWatcher(doc, getState, onTick) {
        let blockTimer = null;
        let blockMaxTimer = null;
        let inputTimer = null;
        let dirtyRoots = new Set();
        let lastCascadeId = null;

        function resolveDirtyRoot(node) {
            const el = node && node.nodeType === 1 ? node : node && node.parentElement;
            if (!el || SKIP_PROSE_TAGS.has(el.tagName) || isOwnUiNode(el)) return null;
            if (el.closest && el.closest('.monaco-editor, .monaco-diff-editor, .xterm, .part.terminal')) return null;
            return el.closest ? el.closest(DIRTY_TARGET_SEL) : null;
        }

        function flushBlocks() {
            if (blockTimer) { clearTimeout(blockTimer); blockTimer = null; }
            if (blockMaxTimer) { clearTimeout(blockMaxTimer); blockMaxTimer = null; }
            const roots = keepTopmostElements(Array.from(dirtyRoots));
            dirtyRoots.clear();
            const state = getState();
            if (roots.length > 0) {
                for (let i = 0; i < roots.length; i++) {
                    const r = roots[i];
                    if (r && r.isConnected !== false) {
                        updateScope(doc, r, { isRTL: state.isRTL, forceRTL: state.forceRTL, skipInputs: true });
                    }
                }
            } else {
                updateScope(doc, doc.body, { isRTL: state.isRTL, forceRTL: state.forceRTL, skipInputs: true });
            }
            if (typeof onTick === 'function') onTick();
        }

        function scheduleBlocks(rootCandidate) {
            if (rootCandidate) dirtyRoots.add(rootCandidate);
            if (blockTimer) clearTimeout(blockTimer);
            blockTimer = setTimeout(flushBlocks, 100);
            if (!blockMaxTimer) {
                blockMaxTimer = setTimeout(flushBlocks, 250);
            }
        }

        function flushInputs() {
            if (inputTimer) { clearTimeout(inputTimer); inputTimer = null; }
            const state = getState();
            const active = doc.activeElement;
            if (active && active.closest && active.closest('[contenteditable="true"], textarea[data-testid="ask-question-writein"]')) {
                const target = active.closest('[contenteditable="true"], textarea[data-testid="ask-question-writein"]');
                updateInputs(doc, target, state.forceRTL, state.isRTL);
            } else {
                updateInputs(doc, doc.body, state.forceRTL, state.isRTL);
            }
        }

        function scheduleInputs() {
            if (inputTimer) clearTimeout(inputTimer);
            inputTimer = setTimeout(flushInputs, 35);
        }

        const targetBody = doc.body || doc.documentElement;
        if (targetBody && targetBody.addEventListener) {
            targetBody.addEventListener('input', scheduleInputs, { capture: true });
            targetBody.addEventListener('focusin', scheduleInputs, { capture: true });
        }

        const Observer = (doc.defaultView && doc.defaultView.MutationObserver) || (typeof MutationObserver !== 'undefined' ? MutationObserver : null);
        let observer = null;
        if (Observer && targetBody) {
            observer = new Observer((mutations) => {
                let needFullChat = false;
                let needInput = false;

                for (let i = 0; i < mutations.length; i++) {
                    const m = mutations[i];
                    const tEl = m.target && (m.target.nodeType === 1 ? m.target : m.target.parentElement);
                    if (!tEl || SKIP_PROSE_TAGS.has(tEl.tagName) || isOwnUiNode(tEl)) continue;

                    if (tEl.closest && tEl.closest('[contenteditable="true"], textarea[data-testid="ask-question-writein"]')) {
                        needInput = true;
                        continue;
                    }

                    if (m.type === 'characterData') {
                        const r = resolveDirtyRoot(tEl);
                        if (r) scheduleBlocks(r);
                        continue;
                    }

                    if (m.type === 'attributes') {
                        if (m.attributeName === 'data-cascade-id') {
                            const cid = tEl.getAttribute && tEl.getAttribute('data-cascade-id');
                            if (cid && cid !== lastCascadeId) {
                                lastCascadeId = cid;
                                needFullChat = true;
                            }
                        } else if (m.attributeName === 'data-aux-pane-open' || m.attributeName === 'data-state' || m.attributeName === 'hidden' || m.attributeName === 'aria-hidden') {
                            const r = resolveDirtyRoot(tEl);
                            if (r) scheduleBlocks(r);
                            else needFullChat = true;
                        }
                        continue;
                    }

                    const added = m.addedNodes || [];
                    for (let j = 0; j < added.length; j++) {
                        const node = added[j];
                        if (node.nodeType === 1 && SKIP_PROSE_TAGS.has(node.tagName)) continue;
                        if (isOwnUiNode(node)) continue;
                        if (node.nodeType === 1 && ((node.matches && node.matches(BROAD_CONTAINER_SEL)) || (node.querySelector && node.querySelector(BROAD_CONTAINER_SEL)))) {
                            scheduleBlocks(node);
                            continue;
                        }
                        if (node.nodeType === 1 && node.querySelector && node.querySelector('button[aria-label="Clear filter"], input[placeholder="Search conversations..."]')) {
                            scheduleBlocks(node);
                            continue;
                        }
                        const r = resolveDirtyRoot(node) || resolveDirtyRoot(tEl);
                        if (r) {
                            scheduleBlocks(r);
                        } else if (node.nodeType === 1 && node.querySelector && node.querySelector(CHAT_CONTAINER_SEL)) {
                            needFullChat = true;
                        }
                    }
                }

                if (needInput) scheduleInputs();
                if (needFullChat) {
                    scheduleBlocks(doc.body || doc.documentElement);
                }
            });

            observer.observe(targetBody, {
                childList: true,
                subtree: true,
                characterData: true,
                attributes: true,
                attributeFilter: ['data-cascade-id', 'data-aux-pane-open', 'data-state', 'hidden', 'aria-hidden']
            });
        }

        return {
            flushAll: () => {
                const state = getState();
                updateScope(doc, doc.body, { isRTL: state.isRTL, forceRTL: state.forceRTL, skipInputs: false });
            },
            disconnect: () => {
                if (observer) observer.disconnect();
                if (blockTimer) clearTimeout(blockTimer);
                if (blockMaxTimer) clearTimeout(blockMaxTimer);
                if (inputTimer) clearTimeout(inputTimer);
            }
        };
    }

    function onToggleShortcut(doc, fn) {
        doc.addEventListener('keydown', (e) => {
            if (e.altKey && !e.metaKey && !e.ctrlKey && e.code === 'KeyR') {
                e.preventDefault();
                fn();
            }
        });
    }

    const api = {
        ZERO_WIDTH_RE,
        RTL_CHAR_RE,
        LTR_CHAR_RE,
        extractProseText,
        classifyText,
        detectDirection,
        updateInputElement,
        updateInputs,
        updateUserInputStep,
        updateTable,
        updateScope,
        clearAll,
        createWatcher,
        onToggleShortcut
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }

    if (root) {
        root.__antigravityRtlEngine = api;
        root.__antigravityRtlCore = {
            _nativeTypingIsolation: true,
            updateDir: (forceRTL) => {
                if (root.document) updateScope(root.document, root.document.body, { isRTL: true, forceRTL: Boolean(forceRTL) });
            },
            watch: (fn) => {
                if (root.document) createWatcher(root.document, () => ({ isRTL: true, forceRTL: false }), fn);
            },
            onToggleShortcut: (fn) => {
                if (root.document) onToggleShortcut(root.document, fn);
            }
        };
    }
})(typeof window !== 'undefined' ? window : globalThis);
