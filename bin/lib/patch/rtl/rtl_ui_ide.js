/**
 * Antigravity IDE RTL Client UI
 * Injected into workbench window & chat subframes.
 * Uses pure DOM builders (Trusted Types safe), debounced saves, and system font autocomplete.
 */
(function (root) {
    'use strict';

    function mountIdeRtl(fontBase64, rtlConfig, systemFonts) {
        if (window.__antigravity_rtl_injected) return;
        window.__antigravity_rtl_injected = true;

        const engine = window.__antigravityRtlEngine;
        const styles = window.__antigravityRtlStyles;
        if (!engine || !styles) return;

        function getFonts() {
            if (systemFonts && (Array.isArray(systemFonts) || Array.isArray(systemFonts.all))) return systemFonts;
            return window.__AGY_RTL_FONTS__ || { all: [], fa: [], en: [], code: [] };
        }

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

        let baseFontStyle = document.getElementById('antigravity-rtl-base-font');
        if (!baseFontStyle && fontBase64) {
            baseFontStyle = document.createElement('style');
            baseFontStyle.id = 'antigravity-rtl-base-font';
            baseFontStyle.textContent = styles.buildBaseFontCSS(fontBase64);
            (document.head || document.documentElement).appendChild(baseFontStyle);
        }

        let rtlStyle = document.getElementById('antigravity-rtl-style');
        if (!rtlStyle) {
            rtlStyle = document.createElement('style');
            rtlStyle.id = 'antigravity-rtl-style';
            (document.head || document.documentElement).appendChild(rtlStyle);
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

        function el(tag, css, children, attrs) {
            const node = document.createElement(tag);
            if (css) node.style.cssText = css;
            if (attrs) Object.assign(node, attrs);
            if (Array.isArray(children)) {
                for (const c of children) {
                    if (c) node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
                }
            } else if (typeof children === 'string') {
                node.textContent = children;
            }
            return node;
        }

        const fontMenus = [];
        let isPanelOpen = false;

        function closePanel() {
            const panel = document.getElementById('antigravity-rtl-settings-panel');
            if (panel) panel.style.display = 'none';
            for (const fm of fontMenus) fm.close();
            isPanelOpen = false;
        }

        function ensureSettingsPanel() {
            let panel = document.getElementById('antigravity-rtl-settings-panel');
            if (panel) return panel;

            panel = el('div', `
                display: none;
                position: fixed;
                z-index: 100000;
                bottom: 28px;
                right: 12px;
                width: 280px;
                background: var(--vscode-editorWidget-background, #1e293b);
                color: var(--vscode-editorWidget-foreground, #f3f4f6);
                border: 1px solid var(--vscode-widget-border, #334155);
                border-radius: 10px;
                box-shadow: 0 14px 34px rgba(0, 0, 0, 0.55);
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 12px;
                padding: 12px 14px;
                direction: ltr;
                box-sizing: border-box;
                user-select: none;
            `, null, { id: 'antigravity-rtl-settings-panel' });

            const closeBtn = el('button', 'background:none;border:none;color:inherit;cursor:pointer;font-size:15px;line-height:1;opacity:0.7;padding:2px;', '✕', { id: 'rtl-panel-close-btn', type: 'button', title: 'Close' });
            const header = el('div', 'display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--vscode-widget-border, rgba(255,255,255,0.14));', [
                el('div', null, [
                    el('span', 'font-weight:600;font-size:12px;display:block;', 'Antigravity RTL'),
                    el('span', 'font-size:10px;opacity:0.65;', 'Alt+R to toggle')
                ]),
                closeBtn
            ]);
            panel.appendChild(header);

            const toggleLabel = el('span', 'font-weight:500;font-size:12px;', state.isRTL ? 'Enabled' : 'Disabled', { id: 'rtl-panel-toggle-label' });
            const masterKnob = el('span', `display:block;width:16px;height:16px;border-radius:50%;background:#ffffff;position:absolute;top:3px;left:${state.isRTL ? '21px' : '3px'};transition:left 0.18s;`, null, { id: 'rtl-panel-master-knob' });
            const masterBtn = el('button', `cursor:pointer;width:40px;height:22px;border-radius:11px;border:none;background:${state.isRTL ? 'var(--vscode-button-background, #3b82f6)' : '#64748b'};position:relative;padding:0;outline:none;`, [masterKnob], { id: 'rtl-panel-master-btn', type: 'button' });
            panel.appendChild(el('div', 'display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;', [toggleLabel, masterBtn]));

            const panelBody = el('div', `display:flex;flex-direction:column;gap:8px;opacity:${state.isRTL ? '1' : '0.4'};pointer-events:${state.isRTL ? 'auto' : 'none'};`, null, { id: 'rtl-panel-body' });

            const forceKnob = el('span', `display:block;width:12px;height:12px;border-radius:50%;background:#ffffff;position:absolute;top:3px;left:${state.forceRTL ? '19px' : '3px'};transition:left 0.18s;`, null, { id: 'rtl-panel-force-knob' });
            const forceBtn = el('button', `cursor:pointer;width:34px;height:18px;border-radius:9px;border:none;background:${state.forceRTL ? 'var(--vscode-button-background, #3b82f6)' : '#64748b'};position:relative;padding:0;outline:none;`, [forceKnob], { id: 'rtl-panel-force-btn', type: 'button' });
            panelBody.appendChild(el('div', 'display:flex;align-items:center;justify-content:space-between;', [
                el('span', 'font-size:11px;opacity:0.85;', 'Force RTL', { title: 'Force RTL direction (tables stay intact)' }),
                forceBtn
            ]));

            const inputStyle = 'width:136px;padding:4px 8px;font-size:11px;border-radius:5px;border:1px solid var(--vscode-input-border,#334155);background:var(--vscode-input-background,#0f172a);color:var(--vscode-input-foreground,#f3f4f6);outline:none;box-sizing:border-box;';
            const faInput = el('input', inputStyle, null, { id: 'rtl-panel-fa-font', type: 'text', placeholder: 'Default: Vazirmatn', value: state.faFont });
            const fwSelect = el('select', inputStyle + 'cursor:pointer;padding:3px 6px;', null, { id: 'rtl-panel-fw' });
            const enInput = el('input', inputStyle, null, { id: 'rtl-panel-en-font', type: 'text', placeholder: 'Default: System', value: state.enFont });
            const codeInput = el('input', inputStyle, null, { id: 'rtl-panel-code-font', type: 'text', placeholder: 'Default: System', value: state.codeFont });
            const stepBtnCss = 'width:18px;height:18px;border-radius:4px;border:1px solid var(--vscode-widget-border,rgba(255,255,255,0.16));background:var(--vscode-input-background,rgba(255,255,255,0.06));color:inherit;font-size:12px;line-height:1;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;padding:0;';
            const lhInput = el('input', 'width:58px;cursor:pointer;accent-color:var(--vscode-button-background,#3b82f6);', null, { id: 'rtl-panel-lh', type: 'range', min: '1.2', max: '2.5', step: '0.1' });
            lhInput.value = state.lh;
            const lhVal = el('span', 'font-size:10px;opacity:0.75;min-width:26px;text-align:right;', state.lh, { id: 'rtl-panel-lh-val' });
            const lhDec = el('button', stepBtnCss, '−', { id: 'rtl-panel-lh-dec', type: 'button', title: 'Decrease Line Height' });
            const lhInc = el('button', stepBtnCss, '+', { id: 'rtl-panel-lh-inc', type: 'button', title: 'Increase Line Height' });
            const lhReset = el('button', 'background:none;border:none;color:inherit;opacity:0.65;cursor:pointer;padding:0;font-size:11px;', '↺', { id: 'rtl-panel-lh-reset', type: 'button' });
            const fsInput = el('input', 'width:58px;cursor:pointer;accent-color:var(--vscode-button-background,#3b82f6);', null, { id: 'rtl-panel-fs', type: 'range', min: '11', max: '24', step: '1' });
            fsInput.value = state.fs;
            const fsVal = el('span', 'font-size:10px;opacity:0.75;min-width:26px;text-align:right;', `${state.fs}px`, { id: 'rtl-panel-fs-val' });
            const fsDec = el('button', stepBtnCss, '−', { id: 'rtl-panel-fs-dec', type: 'button', title: 'Decrease Font Size' });
            const fsInc = el('button', stepBtnCss, '+', { id: 'rtl-panel-fs-inc', type: 'button', title: 'Increase Font Size' });
            const fsReset = el('button', 'background:none;border:none;color:inherit;opacity:0.65;cursor:pointer;padding:0;font-size:11px;', '↺', { id: 'rtl-panel-fs-reset', type: 'button' });

            function rebuildWeightOptions() {
                const opts = typeof styles.getAvailableWeights === 'function'
                    ? styles.getAvailableWeights(getFonts(), state.faFont)
                    : [{ value: '', label: 'Auto' }];
                fwSelect.textContent = '';
                let hasSaved = state.fw === '';
                for (const o of opts) {
                    if (o.value === state.fw) hasSaved = true;
                    fwSelect.appendChild(el('option', null, o.label, { value: o.value }));
                }
                if (!hasSaved && state.fw) {
                    fwSelect.appendChild(el('option', null, state.fw, { value: state.fw }));
                }
                fwSelect.value = state.fw || '';
            }
            rebuildWeightOptions();

            panelBody.appendChild(el('div', 'display:flex;align-items:center;justify-content:space-between;gap:8px;', [el('span', 'font-size:11px;', 'FA Font'), faInput]));
            panelBody.appendChild(el('div', 'display:flex;align-items:center;justify-content:space-between;gap:8px;', [el('span', 'font-size:11px;', 'Weight'), fwSelect]));
            panelBody.appendChild(el('div', 'display:flex;align-items:center;justify-content:space-between;gap:8px;', [el('span', 'font-size:11px;', 'EN Font'), enInput]));
            panelBody.appendChild(el('div', 'display:flex;align-items:center;justify-content:space-between;gap:8px;', [el('span', 'font-size:11px;', 'Code Font'), codeInput]));
            panelBody.appendChild(el('div', 'display:flex;align-items:center;justify-content:space-between;', [
                el('span', 'font-size:11px;', 'Line Height'),
                el('div', 'display:flex;align-items:center;gap:4px;', [lhVal, lhDec, lhInput, lhInc, lhReset])
            ]));
            panelBody.appendChild(el('div', 'display:flex;align-items:center;justify-content:space-between;', [
                el('span', 'font-size:11px;', 'Font Size'),
                el('div', 'display:flex;align-items:center;gap:4px;', [fsVal, fsDec, fsInput, fsInc, fsReset])
            ]));

            panel.appendChild(panelBody);
            document.body.appendChild(panel);

            closeBtn.addEventListener('click', closePanel);
            masterBtn.addEventListener('click', () => setRTLActive(!state.isRTL));
            forceBtn.addEventListener('click', () => {
                if (!state.isRTL) return;
                state.forceRTL = !state.forceRTL;
                saveConfig(true);
                refreshAll();
            });

            for (const [inp, key, kind] of [[faInput, 'faFont', 'fa'], [enInput, 'enFont', 'en'], [codeInput, 'codeFont', 'code']]) {
                inp.addEventListener('input', () => {
                    state[key] = inp.value.trim();
                    if (key === 'faFont') rebuildWeightOptions();
                    saveConfig(false);
                    applyStyles();
                });
                if (typeof styles.attachFontAutocomplete === 'function') {
                    fontMenus.push(styles.attachFontAutocomplete(document, inp, kind, getFonts, (chosen) => {
                        state[key] = chosen.trim();
                        if (key === 'faFont') rebuildWeightOptions();
                        saveConfig(true);
                        applyStyles();
                    }, true));
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

            return panel;
        }

        function syncPanelAndStatusBar() {
            const statusLink = document.getElementById('antigravity-rtl-statusbar-btn');
            if (statusLink) {
                statusLink.textContent = state.isRTL ? '⇄ RTL: On' : '⇄ RTL: Off';
                statusLink.style.color = state.isRTL ? '#38bdf8' : 'inherit';
            }
            const toggleLabel = document.getElementById('rtl-panel-toggle-label');
            if (toggleLabel) toggleLabel.textContent = state.isRTL ? 'Enabled' : 'Disabled';
            const masterBtn = document.getElementById('rtl-panel-master-btn');
            const masterKnob = document.getElementById('rtl-panel-master-knob');
            if (masterBtn && masterKnob) {
                masterBtn.style.background = state.isRTL ? 'var(--vscode-button-background, #3b82f6)' : '#64748b';
                masterKnob.style.left = state.isRTL ? '21px' : '3px';
            }
            const panelBody = document.getElementById('rtl-panel-body');
            if (panelBody) {
                panelBody.style.opacity = state.isRTL ? '1' : '0.4';
                panelBody.style.pointerEvents = state.isRTL ? 'auto' : 'none';
            }
            const forceBtn = document.getElementById('rtl-panel-force-btn');
            const forceKnob = document.getElementById('rtl-panel-force-knob');
            if (forceBtn && forceKnob) {
                forceBtn.style.background = state.forceRTL ? 'var(--vscode-button-background, #3b82f6)' : '#64748b';
                forceKnob.style.left = state.forceRTL ? '19px' : '3px';
            }
        }

        function tryInsertStatusBarItem() {
            if (document.getElementById('antigravity-rtl-statusbar-btn')) return;
            const bar =
                document.querySelector('.part.statusbar .right-items') ||
                document.querySelector('.part.statusbar .items-container.right-items') ||
                document.querySelector('[id="workbench.parts.statusbar"] .right-items') ||
                document.querySelector('.part.statusbar') ||
                document.querySelector('[id="workbench.parts.statusbar"]');
            if (!bar) return;

            const item = document.createElement('a');
            item.id = 'antigravity-rtl-statusbar-btn';
            item.className = 'statusbar-item right';
            item.href = '#';
            item.style.cssText = `
                cursor: pointer !important; padding: 0 8px !important;
                display: inline-flex !important; align-items: center !important; justify-content: center !important;
                font-size: 11px !important; height: 100% !important; line-height: 22px !important;
                user-select: none !important; text-decoration: none !important; white-space: nowrap !important;
                color: ${state.isRTL ? '#38bdf8' : 'inherit'} !important; opacity: 0.95; box-sizing: border-box !important;
            `;
            item.title = 'Antigravity RTL (Click for settings, Alt+R to toggle)';
            item.textContent = state.isRTL ? '⇄ RTL: On' : '⇄ RTL: Off';
            item.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const panel = ensureSettingsPanel();
                if (isPanelOpen) {
                    closePanel();
                } else {
                    syncPanelAndStatusBar();
                    panel.style.display = 'block';
                    isPanelOpen = true;
                }
            });
            bar.prepend(item);
        }

        const watcher = engine.createWatcher(
            document,
            () => ({ isRTL: state.isRTL, forceRTL: state.forceRTL }),
            () => tryInsertStatusBarItem()
        );

        function refreshAll() {
            applyStyles();
            if (!state.isRTL) engine.clearAll(document);
            watcher.flushAll();
            syncPanelAndStatusBar();
        }

        function setRTLActive(active) {
            state.isRTL = Boolean(active);
            saveConfig(true);
            refreshAll();
        }

        document.addEventListener('click', (e) => {
            if (!isPanelOpen) return;
            const panel = document.getElementById('antigravity-rtl-settings-panel');
            const item = document.getElementById('antigravity-rtl-statusbar-btn');
            const fontMenu = document.getElementById('ag-rtl-font-menu');
            if (fontMenu && fontMenu.contains(e.target)) return;
            if (panel && panel.contains(e.target)) return;
            if (item && (item === e.target || item.contains(e.target))) return;
            closePanel();
        });
        document.addEventListener('keydown', (e) => {
            if (isPanelOpen && e.key === 'Escape') closePanel();
        });

        engine.onToggleShortcut(document, () => setRTLActive(!state.isRTL));
        refreshAll();
        tryInsertStatusBarItem();
    }

    if (root) {
        root.__antigravityMountIdeRtl = mountIdeRtl;
    }
})(typeof window !== 'undefined' ? window : globalThis);
