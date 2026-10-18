#!/usr/bin/env node
// ==============================================================================
// Antigravity F5 Manual Backend Sync & Profile Isolation Patcher
// ==============================================================================

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
console.log('[Patch] All patches completed successfully.');
