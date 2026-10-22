// Antigravity Multi-Account Subsystem Master Patcher
const fs = require('fs');
const path = require('path');
const { patchLanguageServer, unpatchLanguageServer } = require('./patch_multi_account_ls');
const { patchIpcAndPreload, unpatchIpcAndPreload } = require('./patch_multi_account_ipc');
const { patchUiInjection, unpatchUiInjection } = require('./patch_multi_account_ui_inject');
const { patchMain, unpatchMain } = require('./patch_main');

function patchMultiAccount(dir) {
    console.log('[Patch] Applying Multi-Account subsystem patches in:', dir);
    const distDir = path.join(dir, 'dist');
    if (!fs.existsSync(distDir)) return;

    patchMain(dir);
    patchUiInjection(distDir);
    patchLanguageServer(distDir);
    patchIpcAndPreload(distDir);

    try {
        const markerPath = path.join(distDir, 'antigravity_selector_patch.marker');
        fs.writeFileSync(markerPath, 'ANTIGRAVITY_SUITE_SELECTOR_PATCH_V1\n', 'utf8');
    } catch (_) {}
}

function unpatchMultiAccount(dir) {
    console.log('[Patch] Removing Multi-Account subsystem patches in:', dir);
    const distDir = path.join(dir, 'dist');
    if (!fs.existsSync(distDir)) return;

    unpatchMain(dir);
    unpatchLanguageServer(distDir);
    unpatchIpcAndPreload(distDir);
    unpatchUiInjection(distDir);

    try {
        const markerPath = path.join(distDir, 'antigravity_selector_patch.marker');
        if (fs.existsSync(markerPath)) fs.unlinkSync(markerPath);
    } catch (_) {}
    console.log('[Patch] Multi-account files and markers removed from dist.');
}

const { patchIdeMultiAccount, unpatchIdeMultiAccount } = require('./patch_multi_account_ide');

module.exports = { patchMultiAccount, unpatchMultiAccount, patchIdeMultiAccount, unpatchIdeMultiAccount };
