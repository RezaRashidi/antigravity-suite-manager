// Antigravity Experimental Conversation Forking Patcher
const fs = require('fs');
const path = require('path');

const FORK_TARGET = '.get("conversationForking")?.enabled??!1';
const FORK_REPLACEMENT = '.get("conversationForking")?.enabled??/*FORK_EXP*/!0';
const FORK_LEGACY_BAD = '(/*FORK_EXP*/!0)';

const IDE_TARGET_FILES = [
    'main.js',
    'vs/workbench/workbench.desktop.main.js',
    'jetskiAgent/main.js'
];

function patchIdeConversationForking(ideDir) {
    const outDir = path.join(ideDir, 'resources/app/out');
    if (!fs.existsSync(outDir)) return;
    for (const rel of IDE_TARGET_FILES) {
        const full = path.join(outDir, rel);
        if (fs.existsSync(full)) {
            let code = fs.readFileSync(full, 'utf8');
            let modified = false;
            if (code.includes(FORK_LEGACY_BAD)) {
                code = code.replaceAll(FORK_LEGACY_BAD, FORK_REPLACEMENT);
                modified = true;
            }
            if (code.includes(FORK_TARGET)) {
                code = code.replaceAll(FORK_TARGET, FORK_REPLACEMENT);
                modified = true;
            }
            if (modified) {
                fs.writeFileSync(full, code, 'utf8');
                console.log(`[Fork] Enabled conversationForking in: ${rel}`);
            }
        }
    }
}

function unpatchIdeConversationForking(ideDir) {
    const outDir = path.join(ideDir, 'resources/app/out');
    if (!fs.existsSync(outDir)) return;
    for (const rel of IDE_TARGET_FILES) {
        const full = path.join(outDir, rel);
        if (fs.existsSync(full)) {
            let code = fs.readFileSync(full, 'utf8');
            let modified = false;
            if (code.includes(FORK_REPLACEMENT)) {
                code = code.replaceAll(FORK_REPLACEMENT, FORK_TARGET);
                modified = true;
            }
            if (code.includes(FORK_LEGACY_BAD)) {
                code = code.replaceAll(FORK_LEGACY_BAD, FORK_TARGET);
                modified = true;
            }
            if (modified) {
                fs.writeFileSync(full, code, 'utf8');
                console.log(`[Fork] Restored conversationForking in: ${rel}`);
            }
        }
    }
}

const PRELOAD_FORK_SNIPPET = `/* FORK_EXP_PRELOAD_START */
try {
    const k = 'jetski.developer.customFlagOverrides';
    let f = {};
    try { f = JSON.parse(window.localStorage.getItem(k) || '{}'); } catch (_) {}
    f['enable-conversation-forking'] = true;
    f['enable-fork-in-new-worktree'] = true;
    f['enable-fork-at-historical-step'] = true;
    delete f['enable-battle-mode'];
    delete f['enable-battle-contrib-variants'];
    delete f['enable-battle-mode-custom-agents'];
    delete f['jetski-autonomous-mode'];
    delete f['labs-autonomous-mode'];
    delete f['enable-aux-pane-redesign'];
    delete f['enable-thought-editing'];
    delete f['enable-thought-steering-from-selection'];
    window.localStorage.setItem(k, JSON.stringify(f));

    const envKey = 'jetski.developer.featureEnvironmentOverride';
    window.localStorage.removeItem(envKey);
} catch (_) {}
/* FORK_EXP_PRELOAD_END */
`;

function resolveDistDir(targetDir) {
    if (!targetDir) return null;
    if (fs.existsSync(path.join(targetDir, 'dist', 'preload.js'))) return path.join(targetDir, 'dist');
    if (fs.existsSync(path.join(targetDir, 'preload.js'))) return targetDir;
    return null;
}

function patchAppConversationForking(targetDir) {
    const distDir = resolveDistDir(targetDir);
    if (!distDir || !fs.existsSync(distDir)) return;

    const lsPath = path.join(distDir, 'languageServer.js');
    if (fs.existsSync(lsPath)) {
        let code = fs.readFileSync(lsPath, 'utf8');
        if (code.includes("'--dev_mode'")) {
            code = code.replace("\n            '--dev_mode',", "");
            fs.writeFileSync(lsPath, code, 'utf8');
            console.log('[Fork] Cleaned --dev_mode flag from languageServer.js');
        }
    }

    const preloadPath = path.join(distDir, 'preload.js');
    if (fs.existsSync(preloadPath)) {
        let code = fs.readFileSync(preloadPath, 'utf8');
        if (code.includes('/* FORK_EXP_PRELOAD_START */')) {
            code = code.replace(/\/\* FORK_EXP_PRELOAD_START \*\/[\s\S]*?\/\* FORK_EXP_PRELOAD_END \*\/\n?/, '');
        }
        code = PRELOAD_FORK_SNIPPET + code;
        fs.writeFileSync(preloadPath, code, 'utf8');
        console.log('[Fork] Injected early main-world flag initializer in preload.js');
    }

    try {
        const markerPath = path.join(distDir, 'antigravity_fork_patch.marker');
        fs.writeFileSync(markerPath, 'ANTIGRAVITY_SUITE_FORK_PATCH_V1\n', 'utf8');
    } catch (_) {}
}

function unpatchAppConversationForking(targetDir) {
    const distDir = resolveDistDir(targetDir);
    if (!distDir || !fs.existsSync(distDir)) return;

    const lsPath = path.join(distDir, 'languageServer.js');
    if (fs.existsSync(lsPath)) {
        let code = fs.readFileSync(lsPath, 'utf8');
        if (code.includes("'--dev_mode'")) {
            code = code.replace("\n            '--dev_mode',", "");
            fs.writeFileSync(lsPath, code, 'utf8');
            console.log('[Fork] Removed --dev_mode flag from languageServer.js');
        }
    }

    const preloadPath = path.join(distDir, 'preload.js');
    if (fs.existsSync(preloadPath)) {
        let code = fs.readFileSync(preloadPath, 'utf8');
        if (code.includes('/* FORK_EXP_PRELOAD_START */')) {
            code = code.replace(/\/\* FORK_EXP_PRELOAD_START \*\/[\s\S]*?\/\* FORK_EXP_PRELOAD_END \*\/\n?/, '');
            fs.writeFileSync(preloadPath, code, 'utf8');
            console.log('[Fork] Removed early flag initializer from preload.js');
        }
    }

    try {
        const markerPath = path.join(distDir, 'antigravity_fork_patch.marker');
        if (fs.existsSync(markerPath)) fs.unlinkSync(markerPath);
    } catch (_) {}
}


module.exports = {
    patchIdeConversationForking,
    unpatchIdeConversationForking,
    patchAppConversationForking,
    unpatchAppConversationForking,
    FORK_TARGET,
    FORK_REPLACEMENT
};
