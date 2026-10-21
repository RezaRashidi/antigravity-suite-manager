#!/usr/bin/env node
// Antigravity Selector & Multi-Account Subsystem Patcher
const fs = require('fs');
const path = require('path');
const { patchMultiAccount, unpatchMultiAccount, patchIdeMultiAccount, unpatchIdeMultiAccount } = require('./lib/patch/patch_multi_account');

function ensureKeyringDecoupled() {
    try {
        const home = process.env.REAL_HOME || process.env.HOME || require('os').homedir();
        const cacheDirs = [
            path.join(home, '.gemini', 'cache'),
            path.join(home, '.gemide', 'cache'),
            path.join(home, '.gemini', 'antigravity-ide', 'cache')
        ];
        for (const cDir of cacheDirs) {
            try {
                if (!fs.existsSync(cDir)) fs.mkdirSync(cDir, { recursive: true });
                fs.writeFileSync(path.join(cDir, 'antigravity-keyring-unavailable'), '');
            } catch (_) {}
        }

        const tokenFile = path.join(home, '.gemini', 'jetski-standalone-oauth-token');
        if (!fs.existsSync(tokenFile)) {
            const { spawnSync } = require('child_process');
            const sDirs = [
                process.env.ANTIGRAVITY_SUITE_DIR,
                path.join(home, 'PhpstormProjects', 'antigravity-suite-manager'),
                path.join(home, '.antigravity-suite-manager'),
                path.resolve(__dirname, '..')
            ].filter(Boolean);
            const env = {
                ...process.env,
                PYTHONPATH: sDirs.map(d => path.join(d, 'src')).join(':') + (process.env.PYTHONPATH ? ':' + process.env.PYTHONPATH : '')
            };
            spawnSync('python3', [
                '-c',
                'from antigravity_suite.auth.keyring_apply import apply_mode_for_app1; apply_mode_for_app1("normal", migrate_token=True)'
            ], { stdio: 'ignore', env });
        }
    } catch (_) {}
}

const isUnpatch = process.argv.includes('--unpatch') || process.argv.includes('unpatch');
const isIde = process.argv.includes('--ide');
const isApp = process.argv.includes('--app');
const dir = process.argv.find(a => !a.startsWith('--') && a !== 'unpatch' && !a.endsWith('node') && !a.endsWith('.js'));

if (!dir || !fs.existsSync(dir)) {
    console.error('Target directory not specified or does not exist:', dir);
    process.exit(1);
}

if (!isUnpatch) {
    ensureKeyringDecoupled();
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
