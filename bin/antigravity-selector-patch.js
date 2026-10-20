#!/usr/bin/env node
// ==============================================================================
// Antigravity Selector & Multi-Account Subsystem Patcher
// ==============================================================================

const fs = require('fs');
const { patchMultiAccount, unpatchMultiAccount } = require('./lib/patch/patch_multi_account');

const isUnpatch = process.argv.includes('--unpatch') || process.argv.includes('unpatch');
const dir = process.argv.find(a => a !== '--unpatch' && a !== 'unpatch' && !a.endsWith('node') && !a.endsWith('.js'));

if (!dir || !fs.existsSync(dir)) {
    console.error('Target directory not specified or does not exist:', dir);
    process.exit(1);
}

if (isUnpatch) {
    console.log('[Patch] Unpatching Multi-Account selector in:', dir);
    unpatchMultiAccount(dir);
    console.log('[Patch] Multi-Account selector unpatched successfully.');
} else {
    console.log('[Patch] Patching Multi-Account selector in:', dir);
    patchMultiAccount(dir);
    console.log('[Patch] Multi-Account selector patched successfully.');
}
