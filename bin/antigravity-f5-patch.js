#!/usr/bin/env node
// ==============================================================================
// Antigravity F5 Manual Backend Sync & Profile Isolation Patcher
// ==============================================================================

// Reference: execFile('xprop', ['-id', String(xid), '-f', 'WM_CLASS', '8s', '-set', 'WM_CLASS', wmClass]
// Reference: let _lsPort = 0;
const fs = require('fs');
const { patchLanguageServer } = require('./lib/patch/patch_ls');
const { patchIpcHandlers } = require('./lib/patch/patch_ipc');
const { patchKeybindings } = require('./lib/patch/patch_keybindings');
const { patchUtils } = require('./lib/patch/patch_utils');
const { patchTray } = require('./lib/patch/patch_tray');
const { patchMain } = require('./lib/patch/patch_main');

const dir = process.argv[2];
if (!dir || !fs.existsSync(dir)) {
    console.error('Target directory not specified or does not exist:', dir);
    process.exit(1);
}

console.log('[Patch] Patching unpacked asar in:', dir);
patchLanguageServer(dir);
patchIpcHandlers(dir);
patchKeybindings(dir);
patchUtils(dir);
patchTray(dir);
patchMain(dir);
try {
    const markerPath = require('path').join(dir, 'dist', 'antigravity_f5_patch.marker');
    fs.writeFileSync(markerPath, 'ANTIGRAVITY_SUITE_F5_PATCH_V2\n', 'utf8');
} catch (_) {}
console.log('[Patch] All patches completed successfully.');
