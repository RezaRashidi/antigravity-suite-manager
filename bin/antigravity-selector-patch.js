#!/usr/bin/env node
// Antigravity Selector & Multi-Account Subsystem Patcher
const fs = require('fs');
const path = require('path');
const { patchMultiAccount, unpatchMultiAccount, patchIdeMultiAccount, unpatchIdeMultiAccount } = require('./lib/patch/patch_multi_account');

const isUnpatch = process.argv.includes('--unpatch') || process.argv.includes('unpatch');
const isIde = process.argv.includes('--ide');
const isApp = process.argv.includes('--app');
const dir = process.argv.find(a => !a.startsWith('--') && a !== 'unpatch' && !a.endsWith('node') && !a.endsWith('.js'));

if (!dir || !fs.existsSync(dir)) {
    console.error('Target directory not specified or does not exist:', dir);
    process.exit(1);
}

const targetIsIde = isIde || (!isApp && fs.existsSync(path.join(dir, 'resources', 'app', 'out')));

if (targetIsIde) {
    if (isUnpatch) {
        console.log('[Patch] Unpatching IDE Multi-Account selector in:', dir);
        unpatchIdeMultiAccount(dir);
        console.log('[Patch] IDE Multi-Account selector unpatched successfully.');
    } else {
        console.log('[Patch] Patching IDE Multi-Account selector in:', dir);
        patchIdeMultiAccount(dir);
        console.log('[Patch] IDE Multi-Account selector patched successfully.');
    }
} else {
    if (isUnpatch) {
        console.log('[Patch] Unpatching Multi-Account selector in:', dir);
        unpatchMultiAccount(dir);
        console.log('[Patch] Multi-Account selector unpatched successfully.');
    } else {
        console.log('[Patch] Patching Multi-Account selector in:', dir);
        patchMultiAccount(dir);
        console.log('[Patch] Multi-Account selector patched successfully.');
    }
}
