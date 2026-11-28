#!/usr/bin/env node
// ==============================================================================
// Antigravity Experiment Flags, DevUI Server & Cost Repricer Patcher (App & IDE)
// ==============================================================================
const fs = require('fs');
const path = require('path');
const {
    patchAppExperiments,
    unpatchAppExperiments,
    patchIdeExperiments,
    unpatchIdeExperiments,
} = require('./lib/patch/patch_experiments');

const isUnpatch = process.argv.includes('--unpatch') || process.argv.includes('unpatch');
const isIde = process.argv.includes('--ide');
const isApp = process.argv.includes('--app');
const dir = process.argv.find((a) => !a.startsWith('--') && a !== 'unpatch' && !a.endsWith('node') && !a.endsWith('.js'));

if (!dir || !fs.existsSync(dir)) {
    console.error('Target directory not specified or does not exist:', dir);
    process.exit(1);
}

const targetIsIde = isIde || (!isApp && fs.existsSync(path.join(dir, 'resources', 'app', 'out')));

if (targetIsIde) {
    if (isUnpatch) {
        console.log('[Experiments] Reverting IDE Experiment Flags patch in:', dir);
        unpatchIdeExperiments(dir);
        console.log('[Experiments] IDE Experiment Flags patch reverted.');
    } else {
        console.log('[Experiments] Applying IDE Experiment Flags patch in:', dir);
        patchIdeExperiments(dir);
        console.log('[Experiments] IDE Experiment Flags patch applied successfully.');
    }
} else {
    if (isUnpatch) {
        console.log('[Experiments] Reverting App Experiment Flags patch in:', dir);
        unpatchAppExperiments(dir);
        console.log('[Experiments] App Experiment Flags patch reverted.');
    } else {
        console.log('[Experiments] Applying App Experiment Flags patch in:', dir);
        patchAppExperiments(dir);
        console.log('[Experiments] App Experiment Flags patch applied successfully.');
    }
}
