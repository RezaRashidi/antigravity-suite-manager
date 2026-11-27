/**
 * Antigravity Suite Internal RTL Stylesheet Builder & Shared Font Autocomplete
 * Table-safe, zero :has(), zero global Tailwind class overrides.
 */
(function (root) {
    'use strict';

    const SAFE_VAL_RE = /^[\p{L}\p{N} ._-]{0,64}$/u;
    const UNICODE_RANGE_FA = 'U+0600-06FF, U+0750-077F, U+08A0-08FF, U+FB50-FDFF, U+FE70-FEFF';

    function sanitizeFontOrMetric(val, fallback) {
        if (typeof val !== 'string') return fallback;
        const trimmed = val.trim();
        return SAFE_VAL_RE.test(trimmed) ? trimmed : fallback;
    }

    function uniqLocals(names) {
        const seen = new Set();
        const out = [];
        for (const n of names) {
            if (!n) continue;
            const key = n.toLowerCase();
            if (seen.has(key)) continue;
            seen.add(key);
            out.push(`local('${n}')`);
        }
        return out.join(', ');
    }

    function buildUserFontRules(faFont) {
        if (!faFont) return '';
        const base = faFont.replace(/[-\s]?(?:Variable|Regular|Bold|Medium|SemiBold|Light|Thin|Black)$/i, '').trim() || faFont;
        const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
        const baseCap = cap(base);
        const rawCap = cap(faFont);

        const thinSrc = uniqLocals([
            `${baseCap} Thin`, `${baseCap}-Thin`, `${base} Thin`, `${base}-Thin`,
            `${baseCap} Light`, `${baseCap}-Light`, `${baseCap} Regular`, `${baseCap}-Regular`, baseCap, base
        ]);
        const lightSrc = uniqLocals([
            `${baseCap} Light`, `${baseCap}-Light`, `${baseCap} ExtraLight`, `${baseCap}-ExtraLight`,
            `${base} Light`, `${base}-Light`, `${baseCap} Regular`, `${baseCap}-Regular`, baseCap, base
        ]);
        const regSrc = uniqLocals([
            `${baseCap} Regular`, `${baseCap}-Regular`, `${baseCap}Regular`,
            `${base} Regular`, `${base}-Regular`, `${base}Regular`,
            `${rawCap}`, faFont, baseCap, base
        ]);
        const medSrc = uniqLocals([
            `${baseCap} Medium`, `${baseCap}-Medium`, `${base} Medium`, `${base}-Medium`,
            `${baseCap} SemiBold`, `${baseCap}-SemiBold`,
            `${baseCap} Regular`, `${baseCap}-Regular`, baseCap, base
        ]);
        const semiSrc = uniqLocals([
            `${baseCap} SemiBold`, `${baseCap}-SemiBold`, `${base} SemiBold`, `${base}-SemiBold`,
            `${baseCap} Bold`, `${baseCap}-Bold`, `${baseCap}Bold`,
            `${base} Bold`, `${base}-Bold`, `${base}Bold`
        ]);
        const boldSrc = uniqLocals([
            `${baseCap} Bold`, `${baseCap}-Bold`, `${baseCap}Bold`,
            `${base} Bold`, `${base}-Bold`, `${base}Bold`
        ]);
        const blackSrc = uniqLocals([
            `${baseCap} Black`, `${baseCap}-Black`, `${base} Black`, `${base}-Black`,
            `${baseCap} ExtraBold`, `${baseCap}-ExtraBold`,
            `${baseCap} Bold`, `${baseCap}-Bold`, `${base} Bold`, `${base}-Bold`
        ]);

        return `
            @font-face {
                font-family: 'UserPersianFont';
                src: ${thinSrc};
                font-weight: 100 199;
                unicode-range: ${UNICODE_RANGE_FA};
            }
            @font-face {
                font-family: 'UserPersianFont';
                src: ${lightSrc};
                font-weight: 200 399;
                unicode-range: ${UNICODE_RANGE_FA};
            }
            @font-face {
                font-family: 'UserPersianFont';
                src: ${regSrc};
                font-weight: 400 499;
                unicode-range: ${UNICODE_RANGE_FA};
            }
            @font-face {
                font-family: 'UserPersianFont';
                src: ${medSrc};
                font-weight: 500 599;
                unicode-range: ${UNICODE_RANGE_FA};
            }
            @font-face {
                font-family: 'UserPersianFont';
                src: ${semiSrc};
                font-weight: 600 699;
                unicode-range: ${UNICODE_RANGE_FA};
            }
            @font-face {
                font-family: 'UserPersianFont';
                src: ${boldSrc};
                font-weight: 700 799;
                unicode-range: ${UNICODE_RANGE_FA};
            }
            @font-face {
                font-family: 'UserPersianFont';
                src: ${blackSrc};
                font-weight: 800 900;
                unicode-range: ${UNICODE_RANGE_FA};
            }
        `;
    }

    function buildBaseFontCSS(fontBase64) {
        const embeddedSrc = fontBase64
            ? `local('Vazirmatn'), local('Vazirmatn Variable'), local('Vazirmatn-Regular'), local('Vazir'), url('data:font/woff2;base64,${fontBase64}') format('woff2')`
            : `local('Vazirmatn'), local('Vazirmatn Variable'), local('Vazirmatn-Regular'), local('Vazir')`;
        return `
            @font-face {
                font-family: 'PersianOnlyFont';
                src: ${embeddedSrc};
                font-weight: 100 900;
                unicode-range: ${UNICODE_RANGE_FA};
            }
        `;
    }

    function buildDisabledCSS() {
        return `
            [data-testid="conversation-view"] p,
            [data-testid="conversation-view"] li,
            [data-testid="conversation-view"] blockquote,
            [data-testid="user-input-step"],
            [data-testid="user-message-bubble"],
            [data-testid="user-input-step"] [data-quotable="true"],
            .leading-relaxed p,
            .leading-relaxed li,
            .prose p,
            .prose li,
            .markdown-body p,
            .markdown-body li,
            [contenteditable="true"],
            [contenteditable="true"] p {
                direction: ltr !important;
                text-align: left !important;
                unicode-bidi: normal !important;
            }
            .md-table-host,
            .md-table-scroll,
            [data-md-table],
            table {
                direction: ltr !important;
            }
        `;
    }

    function buildDynamicCSS(config, fontBase64) {
        const cfg = config || {};
        const faFont = sanitizeFontOrMetric(cfg.faFont, '');
        const enFont = sanitizeFontOrMetric(cfg.enFont, '');
        const codeFont = sanitizeFontOrMetric(cfg.codeFont, '');
        const lh = sanitizeFontOrMetric(String(cfg.lh || '1.6'), '1.6') || '1.6';
        const fsNum = Number(cfg.fs);
        const fs = Number.isFinite(fsNum) && fsNum >= 11 && fsNum <= 24 ? String(fsNum) : '16';
        const fwNum = Number(cfg.fw);
        const hasCustomFw = Number.isInteger(fwNum) && fwNum >= 100 && fwNum <= 900;
        const fwStr = hasCustomFw ? String(fwNum) : '';
        const boldFwStr = hasCustomFw ? (fwNum >= 700 ? '900' : '700') : '';
        const forceRTL = Boolean(cfg.forceRTL);

        const faFontRule = buildUserFontRules(faFont);
        const faFontName = faFont ? "'UserPersianFont', 'PersianOnlyFont'" : "'PersianOnlyFont'";
        const inlineFontFace = fontBase64 ? buildBaseFontCSS(fontBase64) : '';

        const enFontStr = enFont ? `'${enFont}', ui-sans-serif, system-ui, sans-serif` : 'ui-sans-serif, system-ui, sans-serif';
        const fontStack = `${faFontName}, ${enFontStr}, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"`;
        const codeFontStr = codeFont
            ? `'${codeFont}', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace`
            : 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace';

        const forceRule = forceRTL ? `
            .leading-relaxed p:not([dir="ltr"]),
            .leading-relaxed li:not([dir="ltr"]),
            .leading-relaxed h1:not([dir="ltr"]),
            .leading-relaxed h2:not([dir="ltr"]),
            .leading-relaxed h3:not([dir="ltr"]),
            .leading-relaxed h4:not([dir="ltr"]),
            .leading-relaxed h5:not([dir="ltr"]),
            .leading-relaxed h6:not([dir="ltr"]),
            .leading-relaxed blockquote:not([dir="ltr"]),
            .prose p, .prose li, .prose blockquote,
            .markdown-body p, .markdown-body li, .markdown-body blockquote,
            [data-testid="user-input-step"],
            [data-testid="user-message-bubble"],
            [data-testid="user-input-step"] [data-quotable="true"],
            [data-testid="user-input-step"] .whitespace-pre-wrap,
            label[for^="ask-opt-"],
            textarea[data-testid="ask-question-writein"] {
                direction: rtl !important;
                text-align: right !important;
                unicode-bidi: isolate !important;
            }
            .leading-relaxed table,
            .prose table,
            .markdown-body table,
            [data-testid="conversation-view"] table {
                direction: rtl !important;
            }
        ` : '';

        const weightRule = hasCustomFw ? `
            .leading-relaxed,
            .leading-relaxed p,
            .leading-relaxed li,
            .prose p, .prose li,
            .markdown-body p, .markdown-body li,
            [data-testid="user-input-step"] [data-quotable="true"],
            [data-testid="user-input-step"] .whitespace-pre-wrap,
            [contenteditable="true"],
            [contenteditable="true"] p {
                font-weight: ${fwStr} !important;
            }
            .leading-relaxed strong, .leading-relaxed b,
            .leading-relaxed h1, .leading-relaxed h2, .leading-relaxed h3,
            .leading-relaxed th,
            .prose strong, .prose b, .prose h1, .prose h2, .prose th,
            .markdown-body strong, .markdown-body b, .markdown-body h1, .markdown-body h2, .markdown-body th,
            [data-testid="user-input-step"] strong, [data-testid="user-input-step"] b {
                font-weight: ${boldFwStr} !important;
            }
        ` : '';

        return `
            ${inlineFontFace}
            ${faFontRule}

            :root {
                --vscode-chat-font-family: ${fontStack};
            }

            /* Apply Persian-safe font stack across all weights (protect icon fonts & code) */
            [dir="rtl"],
            [dir="rtl"] *:not(.codicon):not([class*="codicon-"]):not(.google-symbols):not(pre):not(code):not(kbd):not(samp):not(.monaco-editor):not(.monaco-editor *):not(.xterm):not(.xterm *),
            [data-testid="conversation-view"] p,
            [data-testid="conversation-view"] li,
            [data-testid="conversation-view"] span:not(.codicon):not([class*="codicon-"]),
            [data-testid="conversation-view"] h1,
            [data-testid="conversation-view"] h2,
            [data-testid="conversation-view"] h3,
            [data-testid="conversation-view"] h4,
            [data-testid="conversation-view"] th,
            [data-testid="conversation-view"] td,
            .leading-relaxed,
            .leading-relaxed p,
            .leading-relaxed li,
            .leading-relaxed th,
            .leading-relaxed td,
            .rendered-markdown,
            .rendered-markdown p,
            .rendered-markdown li,
            .prose, .prose p, .prose li, .prose th, .prose td,
            .markdown-body, .markdown-body p, .markdown-body li, .markdown-body th, .markdown-body td,
            [data-testid="user-input-step"],
            [data-testid="user-message-bubble"],
            [data-testid="user-input-step"] [data-quotable="true"],
            [data-testid="user-input-step"] .whitespace-pre-wrap,
            [contenteditable="true"],
            [contenteditable="true"] p,
            [contenteditable="true"] span,
            [data-lexical-text="true"],
            label[for^="ask-opt-"],
            textarea[data-testid="ask-question-writein"] {
                font-family: ${fontStack} !important;
            }

            .leading-relaxed,
            .prose,
            .markdown-body,
            [data-testid="chat-message"],
            [contenteditable="true"],
            [contenteditable="true"] p {
                font-size: ${fs}px !important;
            }

            .leading-relaxed,
            .leading-relaxed p,
            .leading-relaxed li,
            .prose p,
            .prose li,
            .markdown-body p,
            .markdown-body li,
            [data-testid="user-input-step"] p,
            [data-testid="user-input-step"] .whitespace-pre-wrap,
            [data-lexical-text="true"],
            [contenteditable="true"],
            [contenteditable="true"] p,
            label[for^="ask-opt-"] {
                line-height: ${lh} !important;
            }

            [dir="rtl"] {
                direction: rtl !important;
                text-align: right !important;
                unicode-bidi: isolate;
            }
            [dir="ltr"] {
                direction: ltr !important;
                text-align: left !important;
                unicode-bidi: isolate;
            }

            /* User Prompt Bubbles: align Persian bubble card itself to the physical RIGHT edge */
            [data-testid="user-input-step"][dir="rtl"],
            [data-testid="user-input-step"][dir="rtl"] [data-ag-rtl-bubble="1"],
            [data-ag-rtl-bubble="1"],
            [data-testid="user-message-bubble"][dir="rtl"] {
                margin-left: auto !important;
                margin-right: 0 !important;
                direction: rtl !important;
                text-align: right !important;
            }
            [data-testid="user-input-step"][dir="rtl"] > div,
            [data-testid="user-input-step"][dir="rtl"] > div > div,
            [data-testid="user-message-bubble"][dir="rtl"] [data-quotable="true"],
            [data-testid="user-message-bubble"][dir="rtl"] .whitespace-pre-wrap {
                margin-left: auto !important;
                margin-right: 0 !important;
                direction: rtl !important;
                text-align: right !important;
            }
            [data-testid="user-message-bubble"][dir="rtl"] .user-input-buttons-container {
                right: auto !important;
                left: 0.25rem !important;
                margin-left: 0 !important;
                direction: ltr !important;
            }

            ${weightRule}
            ${forceRule}

            /* Table Safety: host & scroll container ALWAYS stay LTR */
            .md-table-host,
            .md-table-scroll,
            [data-md-table],
            .md-table-host .sticky,
            [data-testid="markdown-table-menu"] {
                direction: ltr !important;
            }

            /* Reversed RTL table columns & border correction */
            table[dir="rtl"] {
                direction: rtl !important;
            }
            table[dir="rtl"] th:first-child:not(:last-child),
            table[dir="rtl"] td:first-child:not(:last-child) {
                border-left-width: 1px !important;
                border-right-width: 0px !important;
            }
            table[dir="rtl"] th:last-child:not(:first-child),
            table[dir="rtl"] td:last-child:not(:first-child) {
                border-right-width: 1px !important;
                border-left-width: 0px !important;
            }
            table[dir="rtl"] th:only-child,
            table[dir="rtl"] td:only-child {
                border-left-width: 0px !important;
                border-right-width: 0px !important;
            }

            table th[dir="rtl"],
            table td[dir="rtl"],
            table th[dir="rtl"] > div,
            table td[dir="rtl"] > div {
                direction: rtl !important;
                text-align: right !important;
            }
            table th[dir="ltr"],
            table td[dir="ltr"],
            table th[dir="ltr"] > div,
            table td[dir="ltr"] > div {
                direction: ltr !important;
                text-align: left !important;
            }

            /* RTL List Padding Fix */
            ul[dir="rtl"], ol[dir="rtl"],
            [dir="rtl"] > ul:not([dir="ltr"]), [dir="rtl"] > ol:not([dir="ltr"]) {
                padding-left: 0 !important;
                padding-right: 1.5rem !important;
            }
            ul[dir="rtl"] ul[dir="rtl"], ul[dir="rtl"] ol[dir="rtl"],
            ol[dir="rtl"] ul[dir="rtl"], ol[dir="rtl"] ol[dir="rtl"] {
                padding-left: 0 !important;
                padding-right: 1.75rem !important;
            }

            /* RTL Blockquote & Markdown Alert Border Flip */
            blockquote[dir="rtl"] {
                border-left: none !important;
                border-right: 4px solid var(--border) !important;
                text-align: right !important;
            }
            .markdown-alert[dir="rtl"] {
                border-left: none !important;
                border-right: 0.25em solid var(--borderColor-default, var(--color-border-border, var(--border))) !important;
            }

            /* Prompt Lexical Input */
            [contenteditable="true"][dir="rtl"],
            [contenteditable="true"] p[dir="rtl"],
            textarea[data-testid="ask-question-writein"][dir="rtl"] {
                direction: rtl !important;
                text-align: right !important;
                unicode-bidi: isolate !important;
            }
            [contenteditable="true"][dir="ltr"],
            [contenteditable="true"] p[dir="ltr"],
            textarea[data-testid="ask-question-writein"][dir="ltr"] {
                direction: ltr !important;
                text-align: left !important;
                unicode-bidi: isolate !important;
            }

            /* Sidebar & Truncated Titles */
            [role="navigation"][aria-label="Sidebar"] .truncate {
                unicode-bidi: plaintext !important;
                text-align: start !important;
            }

            /* Thinking / Edit Badges Keep LTR */
            .cursor-edit.text-secondary-foreground,
            .cursor-edit.text-secondary-foreground * {
                direction: ltr !important;
                text-align: left !important;
                unicode-bidi: isolate !important;
            }

            /* Protect Icon Fonts */
            .codicon, [class*="codicon-"] {
                font-family: codicon !important;
            }
            .google-symbols {
                font-family: "Google Symbols" !important;
            }

            /* Inline Code & Code Blocks Stay Strictly LTR */
            pre, code, kbd, samp,
            pre *, code *,
            .monaco-editor, .monaco-editor *,
            .monaco-diff-editor, .monaco-diff-editor *,
            .part.terminal, .part.terminal *,
            .terminal-wrapper, .terminal-wrapper *,
            .xterm, .xterm * {
                direction: ltr !important;
                text-align: left !important;
                unicode-bidi: isolate !important;
                font-family: ${codeFontStr} !important;
            }
        `;
    }

    function filterFonts(fontCatalog, query, kind) {
        const isObj = fontCatalog && !Array.isArray(fontCatalog) && typeof fontCatalog === 'object';
        const all = isObj ? (Array.isArray(fontCatalog.all) ? fontCatalog.all : []) : (Array.isArray(fontCatalog) ? fontCatalog : []);
        const preferred = isObj && Array.isArray(fontCatalog[kind]) ? fontCatalog[kind] : [];
        const preferredSet = new Set(preferred);
        const q = (query || '').trim().toLowerCase();

        // When query is empty, show OS-classified fonts for this field (e.g. lang=fa/ar for FA, spacing=mono for Code)
        if (!q && preferred.length > 0) {
            return preferred.slice(0, 60);
        }

        const prefixPref = [];
        const prefixOther = [];
        const subPref = [];
        const subOther = [];

        for (let i = 0; i < all.length; i++) {
            const name = all[i];
            const lower = name.toLowerCase();
            if (q && !lower.includes(q)) continue;
            const isPref = preferredSet.has(name);
            const isPrefix = !q || lower.startsWith(q);
            if (isPrefix && isPref) prefixPref.push(name);
            else if (isPrefix) prefixOther.push(name);
            else if (isPref) subPref.push(name);
            else subOther.push(name);
        }

        return prefixPref.concat(prefixOther, subPref, subOther).slice(0, 60);
    }

    /**
     * Lightweight themed autocomplete menu shared by App & IDE font inputs.
     * Renders zero DOM rows while closed.
     */
    function attachFontAutocomplete(doc, input, kind, getFonts, onSelect, openUpward) {
        if (!doc || !input) return { close: () => {} };

        let menu = doc.getElementById('ag-rtl-font-menu');
        if (!menu) {
            menu = doc.createElement('div');
            menu.id = 'ag-rtl-font-menu';
            menu.style.cssText = `
                display: none;
                position: fixed;
                z-index: 1000005;
                max-height: 184px;
                overflow-y: auto;
                border-radius: 6px;
                padding: 4px;
                box-sizing: border-box;
                direction: ltr;
                font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
                font-size: 12px;
                background: var(--popover, var(--vscode-editorWidget-background, #18181b));
                color: var(--popover-foreground, var(--vscode-editorWidget-foreground, #f4f4f5));
                border: 1px solid var(--border, var(--vscode-widget-border, rgba(255,255,255,0.16)));
                box-shadow: 0 10px 26px rgba(0, 0, 0, 0.42);
            `;
            (doc.body || doc.documentElement).appendChild(menu);
        }

        let activeIdx = -1;
        let currentItems = [];

        function isMine() {
            return menu._ownerInput === input && menu.style.display === 'block';
        }

        function close() {
            if (menu._ownerInput === input) {
                menu.style.display = 'none';
                menu.textContent = '';
                menu._ownerInput = null;
                activeIdx = -1;
                currentItems = [];
            }
        }

        function highlight(idx) {
            const rows = menu.children;
            for (let i = 0; i < rows.length; i++) {
                rows[i].style.background = i === idx
                    ? 'var(--secondary, var(--vscode-list-activeSelectionBackground, rgba(59,130,246,0.28)))'
                    : 'transparent';
            }
            activeIdx = idx;
            if (idx >= 0 && rows[idx] && rows[idx].scrollIntoView) {
                rows[idx].scrollIntoView({ block: 'nearest' });
            }
        }

        function pick(fontName) {
            input.value = fontName;
            close();
            if (typeof onSelect === 'function') onSelect(fontName);
        }

        function render() {
            const matches = filterFonts(getFonts(), input.value, kind);
            currentItems = matches;
            menu.textContent = '';
            if (matches.length === 0) {
                close();
                return;
            }
            const rect = input.getBoundingClientRect();
            const width = Math.max(rect.width, 168);
            menu.style.width = width + 'px';
            menu.style.left = Math.max(6, Math.min(rect.left, (doc.defaultView ? doc.defaultView.innerWidth : 1024) - width - 8)) + 'px';
            if (openUpward) {
                menu.style.top = 'auto';
                menu.style.bottom = ((doc.defaultView ? doc.defaultView.innerHeight : 768) - rect.top + 4) + 'px';
            } else {
                menu.style.bottom = 'auto';
                menu.style.top = (rect.bottom + 4) + 'px';
            }

            const frag = doc.createDocumentFragment();
            for (let i = 0; i < matches.length; i++) {
                const name = matches[i];
                const row = doc.createElement('div');
                row.textContent = name;
                row.style.cssText = 'padding: 5px 8px; border-radius: 4px; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;';
                row.addEventListener('mouseenter', () => highlight(i));
                row.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    pick(name);
                });
                frag.appendChild(row);
            }
            menu.appendChild(frag);
            menu._ownerInput = input;
            menu.style.display = 'block';
            activeIdx = -1;
        }

        input.setAttribute('autocomplete', 'off');
        input.addEventListener('focus', render);
        input.addEventListener('input', render);
        input.addEventListener('blur', () => {
            setTimeout(() => { if (isMine()) close(); }, 120);
        });
        input.addEventListener('keydown', (e) => {
            if (!isMine()) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                highlight((activeIdx + 1) % currentItems.length);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                highlight(activeIdx <= 0 ? currentItems.length - 1 : activeIdx - 1);
            } else if (e.key === 'Enter' && activeIdx >= 0 && currentItems[activeIdx]) {
                e.preventDefault();
                e.stopPropagation();
                pick(currentItems[activeIdx]);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                close();
            }
        });

        return { close };
    }

    const WEIGHT_LABELS = {
        100: '100 - Thin',
        200: '200 - ExtraLight',
        300: '300 - Light',
        400: '400 - Regular',
        500: '500 - Medium',
        600: '600 - SemiBold',
        700: '700 - Bold',
        800: '800 - ExtraBold',
        900: '900 - Black'
    };
    const ALL_CSS_WEIGHTS = [100, 200, 300, 400, 500, 600, 700, 800, 900];

    function getAvailableWeights(fontCatalog, faFont) {
        const raw = (faFont || '').trim();
        let list = ALL_CSS_WEIGHTS;
        if (raw && fontCatalog && fontCatalog.weights) {
            const base = raw.replace(/[-\s]?(?:Variable|Regular|Bold|Medium|SemiBold|Light|Thin|Black)$/i, '').trim().toLowerCase();
            const found = fontCatalog.weights[raw.toLowerCase()] || fontCatalog.weights[base];
            if (Array.isArray(found) && found.length > 0) {
                list = found;
            }
        }
        return [{ value: '', label: 'Auto' }].concat(
            list.map((w) => ({ value: String(w), label: WEIGHT_LABELS[w] || String(w) }))
        );
    }

    const api = {
        sanitizeFontOrMetric,
        buildBaseFontCSS,
        buildDynamicCSS,
        buildDisabledCSS,
        filterFonts,
        getAvailableWeights,
        attachFontAutocomplete
    };
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }
    if (root) {
        root.__antigravityRtlStyles = api;
    }
})(typeof window !== 'undefined' ? window : globalThis);
