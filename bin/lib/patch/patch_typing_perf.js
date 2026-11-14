#!/usr/bin/env node
// Standalone Patcher: Prompt Input Typing Lag & Reflow Optimization
const fs = require('fs');
const path = require('path');

const APP_MARKER = 'antigravity_typing_perf_patch.marker';
const APP_MARKER_CONTENT = 'ANTIGRAVITY_SUITE_TYPING_PERF_PATCH_V1\n';
const IDE_MARKER = 'antigravity_ide_typing_perf_patch.marker';
const IDE_MARKER_CONTENT = 'ANTIGRAVITY_SUITE_IDE_TYPING_PERF_PATCH_V1\n';

function getRendererFixPayload() {
    return `// Antigravity Standalone Typing Performance & Reflow Guard
(function initTypingPerfFix() {
    if (window.__ANTIGRAVITY_TYPING_PERF_PATCH__) return;
    window.__ANTIGRAVITY_TYPING_PERF_PATCH__ = true;

    function optimizeRtlEngine() {
        if (window.__antigravityRtlCore && !window.__antigravityRtlCore._agyWrapped && typeof window.__antigravityRtlCore.updateDir === 'function') {
            const origUpdateDir = window.__antigravityRtlCore.updateDir;
            window.__antigravityRtlCore._agyWrapped = true;
            window.__antigravityRtlCore.updateDir = function(forceRTL) {
                const active = document.activeElement;
                const isTyping = active && (
                    active.tagName === 'TEXTAREA' ||
                    active.tagName === 'INPUT' ||
                    active.isContentEditable ||
                    active.closest?.('[contenteditable], .monaco-editor, [data-lexical-editor], [role="textbox"]')
                );
                if (isTyping) {
                    const el = active.closest?.('[contenteditable="true"], textarea') || active;
                    const raw = el.tagName === 'TEXTAREA' ? el.value : el.textContent;
                    const text = (raw || '').replace(/[\\u200B-\\u200F\\uFEFF]/g, '').trim();
                    if (text.length > 0) {
                        const dir = /^[^a-zA-Z]*[\\u0591-\\u07FF\\uFB1D-\\uFDFD\\uFE70-\\uFEFC]/.test(text) ? 'rtl' : 'ltr';
                        if (el.getAttribute('dir') !== dir) el.setAttribute('dir', dir);
                    } else if (el.hasAttribute('dir')) {
                        el.removeAttribute('dir');
                    }
                    return;
                }
                return origUpdateDir(forceRTL);
            };
        }
    }

    optimizeRtlEngine();
    setTimeout(optimizeRtlEngine, 500);
    setTimeout(optimizeRtlEngine, 1500);
    setTimeout(optimizeRtlEngine, 3000);
})();
`;
}

function unpatchAppTypingPerf(unpackedDir) {
    const distDir = path.join(unpackedDir, 'dist');
    if (!fs.existsSync(distDir)) return;

    const utilsPath = path.join(distDir, 'utils.js');
    if (fs.existsSync(utilsPath)) {
        let code = fs.readFileSync(utilsPath, 'utf8');
        code = code.replace(/\/\* AGY_TYPING_PERF_START \*\/[\s\S]*?\/\* AGY_TYPING_PERF_END \*\/\n?/g, '');
        fs.writeFileSync(utilsPath, code, 'utf8');
    }

    const fixPath = path.join(distDir, 'typing_perf_fix.js');
    if (fs.existsSync(fixPath)) fs.unlinkSync(fixPath);

    const markerPath = path.join(distDir, APP_MARKER);
    if (fs.existsSync(markerPath)) fs.unlinkSync(markerPath);
}

function patchAppTypingPerf(unpackedDir) {
    unpatchAppTypingPerf(unpackedDir);
    const distDir = path.join(unpackedDir, 'dist');
    if (!fs.existsSync(distDir)) {
        throw new Error(`dist directory not found in ${unpackedDir}`);
    }

    const utilsPath = path.join(distDir, 'utils.js');
    if (!fs.existsSync(utilsPath)) {
        throw new Error(`dist/utils.js not found in ${unpackedDir}`);
    }

    fs.writeFileSync(path.join(distDir, 'typing_perf_fix.js'), getRendererFixPayload(), 'utf8');

    let code = fs.readFileSync(utilsPath, 'utf8');
    const snippet = `/* AGY_TYPING_PERF_START */
    const __injectTypingPerf = () => {
        try {
            const tpPath = require('path').join(__dirname, 'typing_perf_fix.js');
            if (require('fs').existsSync(tpPath)) void win.webContents.executeJavaScript(require('fs').readFileSync(tpPath, 'utf8')).catch(() => {});
        } catch (_) {}
    };
    win.webContents.on('dom-ready', __injectTypingPerf);
    win.webContents.on('did-finish-load', __injectTypingPerf);
    /* AGY_TYPING_PERF_END */\n`;

    if (code.includes("win.webContents.on('dom-ready', () => {")) {
        code = code.replace("win.webContents.on('dom-ready', () => {", snippet + "win.webContents.on('dom-ready', () => {");
    } else if (code.includes('void win.loadURL(url);')) {
        code = code.replace('void win.loadURL(url);', 'void win.loadURL(url);\n    ' + snippet);
    } else {
        throw new Error('Could not find dom-ready or loadURL hook in dist/utils.js');
    }

    fs.writeFileSync(utilsPath, code, 'utf8');
    fs.writeFileSync(path.join(distDir, APP_MARKER), APP_MARKER_CONTENT, 'utf8');
}

function unpatchIdeTypingPerf(ideDir) {
    const outDir = path.join(ideDir, 'resources', 'app', 'out');
    if (!fs.existsSync(outDir)) return;

    const rtlClient = path.join(outDir, 'antigravity-rtl-client.js');
    if (fs.existsSync(rtlClient)) {
        let code = fs.readFileSync(rtlClient, 'utf8');
        code = code.replace(/\n?\/\* AGY_TYPING_PERF_START \*\/[\s\S]*?\/\* AGY_TYPING_PERF_END \*\/\n?/g, '');
        fs.writeFileSync(rtlClient, code, 'utf8');
    }

    const markerPath = path.join(outDir, IDE_MARKER);
    if (fs.existsSync(markerPath)) fs.unlinkSync(markerPath);
}

function patchIdeTypingPerf(ideDir) {
    unpatchIdeTypingPerf(ideDir);
    const outDir = path.join(ideDir, 'resources', 'app', 'out');
    if (!fs.existsSync(outDir)) {
        throw new Error(`IDE out directory not found in ${ideDir}`);
    }

    const rtlClient = path.join(outDir, 'antigravity-rtl-client.js');
    if (fs.existsSync(rtlClient)) {
        let code = fs.readFileSync(rtlClient, 'utf8');
        code += `\n/* AGY_TYPING_PERF_START */\n${getRendererFixPayload()}/* AGY_TYPING_PERF_END */\n`;
        fs.writeFileSync(rtlClient, code, 'utf8');
    }

    fs.writeFileSync(path.join(outDir, IDE_MARKER), IDE_MARKER_CONTENT, 'utf8');
}

if (require.main === module) {
    const args = process.argv.slice(2);
    const isUnpatch = args.includes('--unpatch');
    const isIde = args.includes('--ide');
    const targetDir = args.find(a => !a.startsWith('--'));
    if (!targetDir) {
        console.error('Usage: patch_typing_perf.js [--ide] [--unpatch] <target_dir>');
        process.exit(1);
    }
    if (isIde) {
        if (isUnpatch) unpatchIdeTypingPerf(targetDir);
        else patchIdeTypingPerf(targetDir);
    } else {
        if (isUnpatch) unpatchAppTypingPerf(targetDir);
        else patchAppTypingPerf(targetDir);
    }
}

module.exports = {
    patchAppTypingPerf,
    unpatchAppTypingPerf,
    patchIdeTypingPerf,
    unpatchIdeTypingPerf,
};
