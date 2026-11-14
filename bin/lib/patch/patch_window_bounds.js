#!/usr/bin/env node
// Antigravity X11 BaseWindow / WebContentsView Maximize & Resize Bounds Patcher
const fs = require('fs');
const path = require('path');

const MARKER = 'antigravity_window_bounds_patch.marker';
const PATCH_ID = 'ANTIGRAVITY_SUITE_WINDOW_BOUNDS_PATCH_V1';
const PATCH_START = '/* WINDOW_BOUNDS_PATCH_START */';
const PATCH_END = '/* WINDOW_BOUNDS_PATCH_END */';
const CLEAN_START = '/* WINDOW_BOUNDS_CLEANUP_START */';
const CLEAN_END = '/* WINDOW_BOUNDS_CLEANUP_END */';

const ORIG_SYNC_BLOCK = [
    '    const syncHubViewBounds = () => {',
    '        if (!baseWin.isDestroyed?.() && !hubWcv.webContents?.isDestroyed?.()) {',
    '            const [width, height] = baseWin.getContentSize();',
    '            curtainView.setBounds({ x: 0, y: 0, width, height });',
    '            hubWcv.setBounds({ x: 0, y: 0, width, height });',
    '        }',
    '    };',
    '    syncHubViewBounds();',
    "    baseWin.on('resize', syncHubViewBounds);"
].join('\n');

const ORIG_SYNC_FLEX_RE = /([ \t]*)(?:const\s+)?syncHubViewBounds\s*=\s*\(\)\s*=>\s*\{[\s\S]*?baseWin\.on\(['"]resize['"],\s*syncHubViewBounds\);/;
const CLEAN_LINE_RE = /([ \t]*)win\.off\?\.?\(['"]resize['"],\s*syncHubViewBounds\);/;
const UNPATCH_RE = /[ \t]*\/\* WINDOW_BOUNDS_PATCH_START \*\/[\s\S]*?\/\* WINDOW_BOUNDS_ORIG_START \*\/\r?\n[ \t]*\/\*\r?\n([\s\S]*?)\r?\n[ \t]*\*\/\r?\n[ \t]*\/\* WINDOW_BOUNDS_ORIG_END \*\/\r?\n[ \t]*\/\* WINDOW_BOUNDS_PATCH_END \*\//;
const PATCH_BLOCK_RE = /[ \t]*\/\* WINDOW_BOUNDS_PATCH_START \*\/[\s\S]*?\/\* WINDOW_BOUNDS_PATCH_END \*\//;
const CLEAN_BLOCK_RE = /[ \t]*\/\* WINDOW_BOUNDS_CLEANUP_START \*\/[\s\S]*?\/\* WINDOW_BOUNDS_CLEANUP_END \*\/\r?\n?/;

function resolveDist(dir) {
    if (!dir) return null;
    if (fs.existsSync(path.join(dir, 'dist', 'utils.js'))) return path.join(dir, 'dist');
    if (fs.existsSync(path.join(dir, 'utils.js'))) return dir;
    return null;
}

function buildPatchedSyncBlock(origText) {
    const match = origText.match(ORIG_SYNC_FLEX_RE);
    const indent = match ? match[1] : '    ';
    const hasConst = /^\s*const\s+/.test(origText);
    const decl = hasConst ? 'const syncHubViewBounds =' : 'syncHubViewBounds =';
    return `${indent}${PATCH_START}\n` +
           `${indent}const _wbTimers = [];\n` +
           `${indent}const _wbClearTimers = () => { while (_wbTimers.length) clearTimeout(_wbTimers.pop()); };\n` +
           `${indent}const _wbApplyBounds = () => {\n` +
           `${indent}    if (!baseWin.isDestroyed?.() && !hubWcv.webContents?.isDestroyed?.()) {\n` +
           `${indent}        const [width, height] = baseWin.getContentSize();\n` +
           `${indent}        if (width <= 0 || height <= 0) return;\n` +
           `${indent}        const cur = typeof hubWcv.getBounds === 'function' ? hubWcv.getBounds() : null;\n` +
           `${indent}        if (cur && cur.x === 0 && cur.y === 0 && cur.width === width && cur.height === height) return;\n` +
           `${indent}        const bounds = { x: 0, y: 0, width, height };\n` +
           `${indent}        curtainView?.setBounds?.(bounds);\n` +
           `${indent}        hubWcv?.setBounds?.(bounds);\n` +
           `${indent}    }\n` +
           `${indent}};\n` +
           `${indent}${decl} () => {\n` +
           `${indent}    _wbApplyBounds();\n` +
           `${indent}    _wbClearTimers();\n` +
           `${indent}    for (const ms of [16, 80, 200, 450]) _wbTimers.push(setTimeout(_wbApplyBounds, ms));\n` +
           `${indent}};\n` +
           `${indent}syncHubViewBounds();\n` +
           `${indent}baseWin.on('resize', syncHubViewBounds);\n` +
           `${indent}for (const _ev of ['maximize', 'unmaximize', 'enter-full-screen', 'leave-full-screen', 'show']) {\n` +
           `${indent}    baseWin.on(_ev, syncHubViewBounds);\n` +
           `${indent}}\n` +
           `${indent}/* WINDOW_BOUNDS_ORIG_START */\n` +
           `${indent}/*\n${origText}\n${indent}*/\n` +
           `${indent}/* WINDOW_BOUNDS_ORIG_END */\n` +
           `${indent}${PATCH_END}`;
}

function stripWindowBoundsPatch(code) {
    let out = code;
    if (UNPATCH_RE.test(out)) {
        out = out.replace(UNPATCH_RE, '$1');
    } else if (PATCH_BLOCK_RE.test(out)) {
        out = out.replace(PATCH_BLOCK_RE, ORIG_SYNC_BLOCK);
    }
    out = out.replace(CLEAN_BLOCK_RE, '');
    return out;
}

function patchAppWindowBounds(targetDir) {
    const dist = resolveDist(targetDir);
    if (!dist) {
        console.error('[WindowBounds] dist/utils.js not found in:', targetDir);
        return false;
    }
    const utilsPath = path.join(dist, 'utils.js');
    let code = stripWindowBoundsPatch(fs.readFileSync(utilsPath, 'utf8'));

    const match = code.match(ORIG_SYNC_FLEX_RE);
    if (match) {
        code = code.replace(match[0], buildPatchedSyncBlock(match[0]));
    } else {
        console.error('[WindowBounds] Could not locate syncHubViewBounds in dist/utils.js');
        return false;
    }

    const cleanMatch = code.match(CLEAN_LINE_RE);
    if (cleanMatch && !code.includes(CLEAN_START)) {
        const indent = cleanMatch[1] || '        ';
        const cleanBlock = `${indent}${CLEAN_START}\n` +
            `${indent}_wbClearTimers();\n` +
            `${indent}for (const _ev of ['maximize', 'unmaximize', 'enter-full-screen', 'leave-full-screen', 'show']) {\n` +
            `${indent}    win.off?.(_ev, syncHubViewBounds);\n` +
            `${indent}}\n` +
            `${indent}${CLEAN_END}\n` +
            cleanMatch[0];
        code = code.replace(cleanMatch[0], cleanBlock);
    }

    fs.writeFileSync(utilsPath, code, 'utf8');
    fs.writeFileSync(path.join(dist, MARKER), `${PATCH_ID}\n`, 'utf8');
    return true;
}

function unpatchAppWindowBounds(targetDir) {
    const dist = resolveDist(targetDir);
    if (!dist) return false;
    const utilsPath = path.join(dist, 'utils.js');
    if (fs.existsSync(utilsPath)) {
        const code = fs.readFileSync(utilsPath, 'utf8');
        if (code.includes(PATCH_START) || code.includes(CLEAN_START)) {
            fs.writeFileSync(utilsPath, stripWindowBoundsPatch(code), 'utf8');
        }
    }
    const markerPath = path.join(dist, MARKER);
    if (fs.existsSync(markerPath)) fs.unlinkSync(markerPath);
    return true;
}

if (require.main === module) {
    const args = process.argv.slice(2);
    const dir = args.find(a => !a.startsWith('--'));
    const ok = dir ? (args.includes('--unpatch') ? unpatchAppWindowBounds(dir) : patchAppWindowBounds(dir)) : false;
    if (!ok) process.exit(1);
}

module.exports = { patchAppWindowBounds, unpatchAppWindowBounds };
