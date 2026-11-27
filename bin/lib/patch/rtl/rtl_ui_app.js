/**
 * Antigravity App (Standalone) RTL Topbar Control UI
 * No network calls, no third-party telemetry, debounced config saves, system font autocomplete.
 */
(function (root) {
    'use strict';

    function mountAppRtl(fontBase64, rtlConfig, systemFonts) {
        if (window.__ANTIGRAVITY_SUITE_RTL_LOADED__) return;
        window.__ANTIGRAVITY_SUITE_RTL_LOADED__ = true;

        const engine = window.__antigravityRtlEngine;
        const styles = window.__antigravityRtlStyles;
        if (!engine || !styles) return;

        function getFonts() {
            if (systemFonts && (Array.isArray(systemFonts) || Array.isArray(systemFonts.all))) return systemFonts;
            return window.__AGY_RTL_FONTS__ || { all: [], fa: [], en: [], code: [] };
        }

        function isAntigravityReady() {
            try {
                if (!document || !document.body) return false;
                const r = document.getElementById('root');
                if (!r || !r.children || r.children.length === 0) return false;
                return Boolean(
                    document.querySelector('[role="navigation"]') ||
                    document.querySelector('[role="main"]') ||
                    document.querySelector('[contenteditable="true"]')
                );
            } catch (_) {
                return false;
            }
        }

        function init() {
            const state = {
                isRTL: rtlConfig.isRTL !== false,
                forceRTL: Boolean(rtlConfig.forceRTL),
                faFont: rtlConfig.faFont || '',
                enFont: rtlConfig.enFont || '',
                codeFont: rtlConfig.codeFont || '',
                lh: rtlConfig.lh || '1.6',
                fs: rtlConfig.fs || '16',
                fw: rtlConfig.fw || '',
                panelSeen: Boolean(rtlConfig.panelSeen)
            };

            let widgetStyle = document.getElementById('rtl-widget-style');
            if (!widgetStyle) {
                widgetStyle = document.createElement('style');
                widgetStyle.id = 'rtl-widget-style';
                widgetStyle.textContent = `
                    #rtl-topbar-btn {
                        font-family: ui-sans-serif, system-ui, -apple-system, sans-serif !important;
                        line-height: 1 !important;
                    }
                    #rtl-dropdown-panel.ag-rtl-panel {
                        position: fixed;
                        z-index: 999999;
                        width: 288px;
                        padding: 12px;
                        border-radius: 10px;
                        direction: ltr;
                        app-region: no-drag;
                        -webkit-app-region: no-drag;
                        font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
                        font-size: 13px;
                        background-color: var(--popover, var(--card, #18181b));
                        color: var(--popover-foreground, var(--foreground, #f4f4f5));
                        border: 1px solid var(--border, rgba(255, 255, 255, 0.12));
                        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
                        box-sizing: border-box;
                        transition: transform 0.14s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.14s ease;
                        transform-origin: top right;
                    }
                    #rtl-dropdown-panel * {
                        app-region: no-drag;
                        -webkit-app-region: no-drag;
                    }
                    #rtl-dropdown-panel.ag-rtl-hidden {
                        transform: scale(0.95);
                        opacity: 0;
                        pointer-events: none;
                        visibility: hidden;
                    }
                    #rtl-dropdown-panel.ag-rtl-visible {
                        transform: scale(1);
                        opacity: 1;
                        pointer-events: auto;
                        visibility: visible;
                    }
                    .ag-rtl-sep {
                        height: 1px;
                        background-color: var(--border, rgba(255, 255, 255, 0.1));
                        margin: 8px -12px;
                    }
                    .ag-rtl-row {
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        gap: 8px;
                        min-height: 28px;
                        padding: 0 2px;
                    }
                    .ag-rtl-label {
                        font-size: 12px;
                        font-weight: 500;
                        opacity: 0.88;
                        white-space: nowrap;
                    }
                    .ag-rtl-input {
                        width: 128px;
                        height: 24px;
                        padding: 3px 8px;
                        font-size: 12px;
                        border-radius: 5px;
                        background-color: var(--muted, #27272a);
                        color: var(--foreground, #f4f4f5);
                        border: 1px solid var(--border, rgba(255, 255, 255, 0.15));
                        outline: none;
                        box-sizing: border-box;
                    }
                    .ag-rtl-input:focus {
                        border-color: var(--color-primary, var(--primary, #3b82f6));
                    }
                    .ag-rtl-switch {
                        position: relative;
                        display: inline-flex;
                        align-items: center;
                        width: 40px;
                        height: 22px;
                        padding: 0;
                        border: none;
                        border-radius: 9999px;
                        cursor: pointer;
                        background-color: rgba(156, 163, 175, 0.4);
                        transition: background-color 0.18s ease;
                        outline: none;
                        flex-shrink: 0;
                    }
                    .ag-rtl-switch[aria-checked="true"] {
                        background-color: var(--color-primary, var(--primary, #2563eb));
                    }
                    .ag-rtl-knob {
                        width: 16px;
                        height: 16px;
                        border-radius: 9999px;
                        background: #ffffff;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.3);
                        transition: transform 0.18s ease;
                        transform: translateX(3px);
                    }
                    .ag-rtl-switch[aria-checked="true"] .ag-rtl-knob {
                        transform: translateX(21px);
                    }
                    .ag-rtl-range {
                        -webkit-appearance: none;
                        appearance: none;
                        width: 72px;
                        height: 16px;
                        background: transparent;
                        cursor: pointer;
                        outline: none;
                        margin: 0;
                    }
                    .ag-rtl-range::-webkit-slider-runnable-track {
                        height: 4px;
                        border-radius: 9999px;
                        background: var(--muted, rgba(255, 255, 255, 0.22));
                    }
                    .ag-rtl-range::-webkit-slider-thumb {
                        -webkit-appearance: none;
                        appearance: none;
                        width: 12px;
                        height: 12px;
                        border-radius: 9999px;
                        margin-top: -4px;
                        background: var(--color-primary, var(--primary, #3b82f6));
                        border: 1.5px solid #ffffff;
                    }
                    .ag-rtl-val {
                        font-size: 11px;
                        opacity: 0.72;
                        min-width: 28px;
                        text-align: right;
                        font-variant-numeric: tabular-nums;
                    }
                    .ag-rtl-reset {
                        background: none;
                        border: none;
                        color: inherit;
                        opacity: 0.55;
                        cursor: pointer;
                        padding: 2px;
                        font-size: 12px;
                        line-height: 1;
                    }
                    .ag-rtl-reset:hover {
                        opacity: 1;
                    }
                    .ag-rtl-step {
                        width: 18px;
                        height: 18px;
                        border-radius: 4px;
                        border: 1px solid var(--border, rgba(255, 255, 255, 0.16));
                        background: var(--muted, rgba(255, 255, 255, 0.06));
                        color: inherit;
                        font-size: 12px;
                        line-height: 1;
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        cursor: pointer;
                        padding: 0;
                    }
                    .ag-rtl-step:hover {
                        background: var(--secondary, rgba(255, 255, 255, 0.14));
                    }
                    .ag-rtl-kbd {
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        min-width: 18px;
                        height: 18px;
                        padding: 0 5px;
                        font-size: 10px;
                        font-weight: 600;
                        color: var(--muted-foreground, #a1a1aa);
                        background-color: var(--muted, rgba(255,255,255,0.08));
                        border: 1px solid var(--border, rgba(255,255,255,0.15));
                        border-radius: 4px;
                    }
                    .ag-rtl-disabled {
                        opacity: 0.42;
                        pointer-events: none;
                    }
                `;
                document.head.appendChild(widgetStyle);
            }

            let baseFontStyle = document.getElementById('antigravity-rtl-base-font');
            if (!baseFontStyle && fontBase64) {
                baseFontStyle = document.createElement('style');
                baseFontStyle.id = 'antigravity-rtl-base-font';
                baseFontStyle.textContent = styles.buildBaseFontCSS(fontBase64);
                document.head.appendChild(baseFontStyle);
            }

            let rtlStyle = document.getElementById('antigravity-rtl-style');
            if (!rtlStyle) {
                rtlStyle = document.createElement('style');
                rtlStyle.id = 'antigravity-rtl-style';
                document.head.appendChild(rtlStyle);
            }

            let saveTimer = null;
            function saveConfig(immediate) {
                const flush = () => {
                    saveTimer = null;
                    try { console.log('SAVE_RTL_CONFIG|' + JSON.stringify(state)); } catch (_) {}
                };
                if (saveTimer) clearTimeout(saveTimer);
                if (immediate) flush();
                else saveTimer = setTimeout(flush, 250);
            }

            function applyStyles() {
                rtlStyle.textContent = state.isRTL
                    ? styles.buildDynamicCSS(state, '')
                    : styles.buildDisabledCSS();
            }

            function el(tag, props, children) {
                const node = document.createElement(tag);
                if (props) {
                    for (const k of Object.keys(props)) {
                        if (k === 'className') node.className = props[k];
                        else if (k === 'text') node.textContent = props[k];
                        else if (k === 'style') node.style.cssText = props[k];
                        else if (k.startsWith('aria-') || k === 'role' || k === 'type' || k === 'id' || k === 'title' || k === 'placeholder' || k === 'min' || k === 'max' || k === 'step') {
                            node.setAttribute(k, String(props[k]));
                        } else {
                            node[k] = props[k];
                        }
                    }
                }
                if (Array.isArray(children)) {
                    for (const c of children) {
                        if (c) node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
                    }
                }
                return node;
            }

            // First-visit dot disappears permanently once the RTL panel is opened
            const statusDot = el('span', {
                id: 'rtl-status-dot',
                className: `absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full ${(!state.panelSeen && state.isRTL) ? 'bg-sky-400' : 'hidden'}`
            });

            const svgNS = 'http://www.w3.org/2000/svg';
            const globeSvg = document.createElementNS(svgNS, 'svg');
            globeSvg.setAttribute('width', '14');
            globeSvg.setAttribute('height', '14');
            globeSvg.setAttribute('viewBox', '0 0 24 24');
            globeSvg.setAttribute('fill', 'none');
            globeSvg.setAttribute('stroke', 'currentColor');
            globeSvg.setAttribute('stroke-width', '2');
            globeSvg.setAttribute('stroke-linecap', 'round');
            globeSvg.setAttribute('stroke-linejoin', 'round');
            for (const attrs of [
                ['circle', { cx: '12', cy: '12', r: '10' }],
                ['path', { d: 'M2 12h20' }],
                ['path', { d: 'M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z' }]
            ]) {
                const shape = document.createElementNS(svgNS, attrs[0]);
                for (const ak of Object.keys(attrs[1])) shape.setAttribute(ak, attrs[1][ak]);
                globeSvg.appendChild(shape);
            }

            const topbarBtn = el('button', {
                id: 'rtl-topbar-btn',
                type: 'button',
                title: 'Antigravity RTL (Alt+R)',
                className: 'inline-flex items-center font-medium transition-colors select-none outline-none cursor-pointer justify-center disabled:opacity-50 border border-border bg-transparent text-secondary-foreground hover:text-foreground hover:bg-secondary h-7 rounded-md gap-1.5 px-2.5 text-[13px] whitespace-nowrap',
                style: 'app-region: no-drag;'
            }, [
                el('div', {
                    className: 'relative flex items-center justify-center shrink-0',
                    style: 'width: 14px; height: 14px;'
                }, [globeSvg, statusDot]),
                el('span', { text: 'RTL' })
            ]);

            const widgetWrapper = el('div', {
                id: 'rtl-topbar-wrapper',
                className: 'relative inline-flex items-center',
                style: 'app-region: no-drag;'
            }, [topbarBtn]);

            const isMac = /Mac/i.test(navigator.userAgent || navigator.platform || '');
            const kbdGroup = el('span', { style: 'display:inline-flex;align-items:center;gap:4px;' }, [
                el('kbd', { className: 'ag-rtl-kbd', text: isMac ? '⌥' : 'Alt' }),
                el('kbd', { className: 'ag-rtl-kbd', text: 'R' })
            ]);

            const toggleLabel = el('span', { id: 'rtl-toggle-label', className: 'ag-rtl-label', text: state.isRTL ? 'Enabled' : 'Disabled' });
            const toggleBtn = el('button', {
                id: 'rtl-toggle-btn',
                type: 'button',
                role: 'switch',
                'aria-checked': state.isRTL ? 'true' : 'false',
                className: 'ag-rtl-switch'
            }, [el('span', { id: 'rtl-toggle-knob', className: 'ag-rtl-knob' })]);

            const forceBtn = el('button', {
                id: 'rtl-force-btn',
                type: 'button',
                role: 'switch',
                'aria-checked': state.forceRTL ? 'true' : 'false',
                className: 'ag-rtl-switch'
            }, [el('span', { id: 'rtl-force-knob', className: 'ag-rtl-knob' })]);
            const forceRow = el('div', {
                id: 'rtl-force-row',
                className: `ag-rtl-row ${state.isRTL ? '' : 'ag-rtl-disabled'}`
            }, [
                el('span', { className: 'ag-rtl-label', text: 'Force RTL', title: 'Force RTL direction (tables stay intact)' }),
                forceBtn
            ]);

            const faInput = el('input', { id: 'rtl-fafont-input', type: 'text', placeholder: 'Default: Vazirmatn', className: 'ag-rtl-input', value: state.faFont });
            const fwSelect = el('select', { id: 'rtl-fw-select', className: 'ag-rtl-input', style: 'cursor:pointer;padding:2px 6px;' });
            const enInput = el('input', { id: 'rtl-enfont-input', type: 'text', placeholder: 'Default: System', className: 'ag-rtl-input', value: state.enFont });
            const codeInput = el('input', { id: 'rtl-codefont-input', type: 'text', placeholder: 'Default: System', className: 'ag-rtl-input', value: state.codeFont });
            const lhInput = el('input', { id: 'rtl-lh-input', type: 'range', min: '1.2', max: '2.5', step: '0.1', className: 'ag-rtl-range', style: 'width:58px;' });
            lhInput.value = state.lh;
            const lhVal = el('span', { id: 'rtl-lh-val', className: 'ag-rtl-val', text: state.lh });
            const lhDec = el('button', { id: 'rtl-lh-dec', type: 'button', className: 'ag-rtl-step', text: '−', title: 'Decrease Line Height' });
            const lhInc = el('button', { id: 'rtl-lh-inc', type: 'button', className: 'ag-rtl-step', text: '+', title: 'Increase Line Height' });
            const lhReset = el('button', { id: 'rtl-lh-reset', type: 'button', className: 'ag-rtl-reset', text: '↺', title: 'Reset Line Height to 1.6' });
            const fsInput = el('input', { id: 'rtl-fs-input', type: 'range', min: '11', max: '24', step: '1', className: 'ag-rtl-range', style: 'width:58px;' });
            fsInput.value = state.fs;
            const fsVal = el('span', { id: 'rtl-fs-val', className: 'ag-rtl-val', text: `${state.fs}px` });
            const fsDec = el('button', { id: 'rtl-fs-dec', type: 'button', className: 'ag-rtl-step', text: '−', title: 'Decrease Font Size' });
            const fsInc = el('button', { id: 'rtl-fs-inc', type: 'button', className: 'ag-rtl-step', text: '+', title: 'Increase Font Size' });
            const fsReset = el('button', { id: 'rtl-fs-reset', type: 'button', className: 'ag-rtl-reset', text: '↺', title: 'Reset Font Size to 16px' });

            function rebuildWeightOptions() {
                const opts = typeof styles.getAvailableWeights === 'function'
                    ? styles.getAvailableWeights(getFonts(), state.faFont)
                    : [{ value: '', label: 'Auto' }];
                fwSelect.textContent = '';
                let hasSaved = state.fw === '';
                for (const o of opts) {
                    if (o.value === state.fw) hasSaved = true;
                    fwSelect.appendChild(el('option', { value: o.value, text: o.label }));
                }
                if (!hasSaved && state.fw) {
                    fwSelect.appendChild(el('option', { value: state.fw, text: state.fw }));
                }
                fwSelect.value = state.fw || '';
            }
            rebuildWeightOptions();

            const settingsWrapper = el('div', {
                id: 'rtl-settings-wrapper',
                className: state.isRTL ? '' : 'ag-rtl-disabled',
                style: 'display:flex;flex-direction:column;gap:6px;'
            }, [
                el('div', { className: 'ag-rtl-row' }, [el('span', { className: 'ag-rtl-label', text: 'FA/AR Font' }), faInput]),
                el('div', { className: 'ag-rtl-row' }, [el('span', { className: 'ag-rtl-label', text: 'Font Weight' }), fwSelect]),
                el('div', { className: 'ag-rtl-row' }, [el('span', { className: 'ag-rtl-label', text: 'EN Font' }), enInput]),
                el('div', { className: 'ag-rtl-row' }, [el('span', { className: 'ag-rtl-label', text: 'Code Font' }), codeInput]),
                el('div', { className: 'ag-rtl-row' }, [
                    el('span', { className: 'ag-rtl-label', text: 'Line Height' }),
                    el('div', { style: 'display:flex;align-items:center;gap:4px;' }, [lhVal, lhDec, lhInput, lhInc, lhReset])
                ]),
                el('div', { className: 'ag-rtl-row' }, [
                    el('span', { className: 'ag-rtl-label', text: 'Font Size' }),
                    el('div', { style: 'display:flex;align-items:center;gap:4px;' }, [fsVal, fsDec, fsInput, fsInc, fsReset])
                ])
            ]);

            const dropdownPanel = el('div', {
                id: 'rtl-dropdown-panel',
                className: 'ag-rtl-panel ag-rtl-hidden'
            }, [
                el('div', { style: 'display:flex;align-items:center;justify-content:space-between;padding-bottom:2px;' }, [
                    el('span', { style: 'font-size:11px;font-weight:600;letter-spacing:0.04em;opacity:0.7;', text: 'ANTIGRAVITY RTL' }),
                    kbdGroup
                ]),
                el('div', { className: 'ag-rtl-sep' }),
                el('div', { style: 'display:flex;flex-direction:column;gap:6px;' }, [
                    el('div', { className: 'ag-rtl-row' }, [toggleLabel, toggleBtn]),
                    forceRow
                ]),
                el('div', { className: 'ag-rtl-sep' }),
                settingsWrapper
            ]);

            function attachElements() {
                if (!document.getElementById('rtl-topbar-wrapper')) {
                    const anchor =
                        document.querySelector('[data-testid="titlebar-more-actions"]') ||
                        document.querySelector('[data-testid="install-editor"]');
                    if (anchor && anchor.parentElement) anchor.parentElement.appendChild(widgetWrapper);
                }
                if (!document.getElementById('rtl-dropdown-panel') && document.body) {
                    document.body.appendChild(dropdownPanel);
                }
            }

            const watcher = engine.createWatcher(
                document,
                () => ({ isRTL: state.isRTL, forceRTL: state.forceRTL }),
                () => attachElements()
            );

            function syncUiControls() {
                toggleLabel.textContent = state.isRTL ? 'Enabled' : 'Disabled';
                toggleBtn.setAttribute('aria-checked', state.isRTL ? 'true' : 'false');
                forceBtn.setAttribute('aria-checked', state.forceRTL ? 'true' : 'false');
                forceRow.classList.toggle('ag-rtl-disabled', !state.isRTL);
                settingsWrapper.classList.toggle('ag-rtl-disabled', !state.isRTL);
                statusDot.className = `absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full ${(!state.panelSeen && state.isRTL) ? 'bg-sky-400' : 'hidden'}`;
            }

            function refreshAll() {
                syncUiControls();
                applyStyles();
                if (!state.isRTL) engine.clearAll(document);
                watcher.flushAll();
            }

            function setRTLActive(active) {
                state.isRTL = Boolean(active);
                saveConfig(true);
                refreshAll();
            }

            toggleBtn.addEventListener('click', () => setRTLActive(!state.isRTL));
            forceBtn.addEventListener('click', () => {
                if (!state.isRTL) return;
                state.forceRTL = !state.forceRTL;
                saveConfig(true);
                refreshAll();
            });

            const fontMenus = [];
            for (const [inp, key, kind] of [[faInput, 'faFont', 'fa'], [enInput, 'enFont', 'en'], [codeInput, 'codeFont', 'code']]) {
                const applyFont = (val, immediate) => {
                    state[key] = val.trim();
                    if (key === 'faFont') rebuildWeightOptions();
                    saveConfig(immediate);
                    applyStyles();
                };
                inp.addEventListener('input', () => applyFont(inp.value, false));
                if (typeof styles.attachFontAutocomplete === 'function') {
                    fontMenus.push(styles.attachFontAutocomplete(document, inp, kind, getFonts, (chosen) => {
                        applyFont(chosen, true);
                    }, false));
                }
            }
            fwSelect.addEventListener('change', () => {
                state.fw = fwSelect.value;
                saveConfig(true);
                applyStyles();
            });

            const updateLh = (immediate) => { state.lh = lhInput.value; lhVal.textContent = state.lh; saveConfig(immediate); applyStyles(); };
            lhInput.addEventListener('input', () => updateLh(false));
            lhInput.addEventListener('change', () => updateLh(true));
            lhDec.addEventListener('click', () => { lhInput.value = String(Math.max(1.2, Math.round((Number(lhInput.value) - 0.1) * 10) / 10)); updateLh(true); });
            lhInc.addEventListener('click', () => { lhInput.value = String(Math.min(2.5, Math.round((Number(lhInput.value) + 0.1) * 10) / 10)); updateLh(true); });
            lhReset.addEventListener('click', () => { lhInput.value = '1.6'; updateLh(true); });
            const updateFs = (immediate) => { state.fs = fsInput.value; fsVal.textContent = `${state.fs}px`; saveConfig(immediate); applyStyles(); };
            fsInput.addEventListener('input', () => updateFs(false));
            fsInput.addEventListener('change', () => updateFs(true));
            fsDec.addEventListener('click', () => { fsInput.value = String(Math.max(11, Number(fsInput.value) - 1)); updateFs(true); });
            fsInc.addEventListener('click', () => { fsInput.value = String(Math.min(24, Number(fsInput.value) + 1)); updateFs(true); });
            fsReset.addEventListener('click', () => { fsInput.value = '16'; updateFs(true); });

            let isDropdownOpen = false;

            function updateDropdownPosition() {
                const rect = topbarBtn.getBoundingClientRect();
                dropdownPanel.style.top = (rect.bottom + 6) + 'px';
                dropdownPanel.style.right = Math.max(8, window.innerWidth - rect.right) + 'px';
            }

            function toggleDropdown(show) {
                const next = show !== undefined ? show : !isDropdownOpen;
                if (next === isDropdownOpen) return;
                isDropdownOpen = next;
                if (next) {
                    if (!state.panelSeen) {
                        state.panelSeen = true;
                        syncUiControls();
                        saveConfig(true);
                    }
                    updateDropdownPosition();
                    dropdownPanel.classList.remove('ag-rtl-hidden');
                    dropdownPanel.classList.add('ag-rtl-visible');
                    topbarBtn.classList.add('bg-secondary');
                    topbarBtn.setAttribute('aria-expanded', 'true');
                } else {
                    for (const fm of fontMenus) fm.close();
                    dropdownPanel.classList.remove('ag-rtl-visible');
                    dropdownPanel.classList.add('ag-rtl-hidden');
                    topbarBtn.classList.remove('bg-secondary');
                    topbarBtn.setAttribute('aria-expanded', 'false');
                }
            }

            topbarBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleDropdown();
            });
            dropdownPanel.addEventListener('click', (e) => e.stopPropagation());
            document.addEventListener('click', (e) => {
                if (!isDropdownOpen) return;
                const fontMenu = document.getElementById('ag-rtl-font-menu');
                if (fontMenu && fontMenu.contains(e.target)) return;
                if (!dropdownPanel.contains(e.target) && !topbarBtn.contains(e.target)) {
                    toggleDropdown(false);
                }
            });
            document.addEventListener('keydown', (e) => {
                if (isDropdownOpen && e.key === 'Escape') toggleDropdown(false);
            });
            window.addEventListener('resize', () => {
                if (isDropdownOpen) updateDropdownPosition();
            }, { passive: true });

            engine.onToggleShortcut(document, () => setRTLActive(!state.isRTL));
            attachElements();
            refreshAll();
        }

        let mounted = false;
        let timer = null;
        let startupObs = null;

        function tryMount() {
            if (mounted) return;
            if (isAntigravityReady()) {
                mounted = true;
                if (timer) clearInterval(timer);
                if (startupObs) try { startupObs.disconnect(); } catch (_) {}
                init();
            }
        }

        tryMount();
        if (!mounted) {
            let attempts = 0;
            try {
                startupObs = new MutationObserver(() => tryMount());
                startupObs.observe(document.documentElement || document.body, { childList: true, subtree: true });
            } catch (_) {}
            timer = setInterval(() => {
                attempts++;
                if (attempts > 120) {
                    clearInterval(timer);
                    if (startupObs) try { startupObs.disconnect(); } catch (_) {}
                    return;
                }
                tryMount();
            }, 350);
        }
    }

    if (root) {
        root.__antigravityMountAppRtl = mountAppRtl;
    }
})(typeof window !== 'undefined' ? window : globalThis);
