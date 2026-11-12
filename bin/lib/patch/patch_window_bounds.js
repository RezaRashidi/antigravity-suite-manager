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

const PATCHED_SYNC_BLOCK = `    ${PATCH_START}
    const _wbTimers = [];
    const _wbClearTimers = () => { while (_wbTimers.length) clearTimeout(_wbTimers.pop()); };
    const _wbApplyBounds = () => {
        if (!baseWin.isDestroyed?.() && !hubWcv.webContents?.isDestroyed?.()) {
            const [width, height] = baseWin.getContentSize();
            if (width <= 0 || height <= 0) return;
            const cur = typeof hubWcv.getBounds === 'function' ? hubWcv.getBounds() : null;
            if (cur && cur.x === 0 && cur.y === 0 && cur.width === width && cur.height === height) return;
            const bounds = { x: 0, y: 0, width, height };
            curtainView.setBounds(bounds);
            hubWcv.setBounds(bounds);
        }
    };
    const syncHubViewBounds = () => {
        _wbApplyBounds();
        _wbClearTimers();
        for (const ms of [16, 80, 200, 450]) _wbTimers.push(setTimeout(_wbApplyBounds, ms));
    };
    syncHubViewBounds();
    baseWin.on('resize', syncHubViewBounds);
    for (const _ev of ['maximize', 'unmaximize', 'enter-full-screen', 'leave-full-screen', 'show']) {
        baseWin.on(_ev, syncHubViewBounds);
    }
    ${PATCH_END}`;

const ORIG_CLEANUP_LINE = "        win.off?.('resize', syncHubViewBounds);";
const PATCHED_CLEANUP_BLOCK = `        ${CLEAN_START}
        _wbClearTimers();
        for (const _ev of ['maximize', 'unmaximize', 'enter-full-screen', 'leave-full-screen', 'show']) {
            win.off?.(_ev, syncHubViewBounds);
        }
        ${CLEAN_END}
${ORIG_CLEANUP_LINE}`;

const PATCH_BLOCK_RE = /    \/\* WINDOW_BOUNDS_PATCH_START \*\/[\s\S]*?\/\* WINDOW_BOUNDS_PATCH_END \*\//;
const CLEAN_BLOCK_RE = /[ \t]*\/\* WINDOW_BOUNDS_CLEANUP_START \*\/[\s\S]*?\/\* WINDOW_BOUNDS_CLEANUP_END \*\/\r?\n?/;
const ORIG_SYNC_FLEX_RE = /    const syncHubViewBounds = \(\) => \{\r?\n[\s\S]*?baseWin\.on\('resize', syncHubViewBounds\);/;

function resolveDist(dir) {
    if (!dir) return null;
    if (fs.existsSync(path.join(dir, 'dist', 'utils.js'))) return path.join(dir, 'dist');
    if (fs.existsSync(path.join(dir, 'utils.js'))) return dir;
    return null;
}

function stripWindowBoundsPatch(code) {
    let out = code.replace(PATCH_BLOCK_RE, ORIG_SYNC_BLOCK);
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

    if (code.includes(ORIG_SYNC_BLOCK)) {
        code = code.replace(ORIG_SYNC_BLOCK, PATCHED_SYNC_BLOCK);
    } else if (ORIG_SYNC_FLEX_RE.test(code)) {
        code = code.replace(ORIG_SYNC_FLEX_RE, PATCHED_SYNC_BLOCK);
    } else {
        console.error('[WindowBounds] Could not locate syncHubViewBounds in dist/utils.js');
        return false;
    }

    if (code.includes(ORIG_CLEANUP_LINE) && !code.includes(CLEAN_START)) {
        code = code.replace(ORIG_CLEANUP_LINE, PATCHED_CLEANUP_BLOCK);
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
