#!/usr/bin/env node
// ==============================================================================
// Antigravity Conversation Forking Subsystem Patcher (App & IDE)
// ==============================================================================
const fs = require('fs');
const path = require('path');
const {
    patchIdeConversationForking,
    unpatchIdeConversationForking,
    patchAppConversationForking,
    unpatchAppConversationForking
} = require('./lib/patch/patch_conversation_forking');

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
        console.log('[Fork] Reverting IDE Conversation Forking patch in:', dir);
        unpatchIdeConversationForking(dir);
        console.log('[Fork] IDE Conversation Forking patch reverted.');
    } else {
        const prodPath = path.join(dir, 'resources', 'app', 'product.json');
        let ideVer = null;
        if (fs.existsSync(prodPath)) {
            try {
                const prod = JSON.parse(fs.readFileSync(prodPath, 'utf8'));
                ideVer = prod.ideVersion || prod.version || null;
            } catch (_) {}
        }
        const nums = (String(ideVer || '').match(/\d+/g) || []).map(Number);
        while (nums.length < 3) nums.push(0);
        if (nums[0] < 2 || (nums[0] === 2 && nums[1] < 6)) {
            console.error(`[Error] Antigravity IDE v2.6.0+ is required for conversation forking patch (detected: v${ideVer || 'Unknown'}). Aborting.`);
            process.exit(1);
        }
        console.log('[Fork] Applying IDE Conversation Forking patch in:', dir);
        patchIdeConversationForking(dir);
        console.log('[Fork] IDE Conversation Forking patch applied successfully.');
    }
} else {
    if (isUnpatch) {
        console.log('[Fork] Reverting App Conversation Forking patch in:', dir);
        unpatchAppConversationForking(dir);
        console.log('[Fork] App Conversation Forking patch reverted.');
    } else {
        console.log('[Fork] Applying App Conversation Forking patch in:', dir);
        patchAppConversationForking(dir);
        console.log('[Fork] App Conversation Forking patch applied successfully.');
    }
}
