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

module.exports = {
    patchIdeConversationForking,
    unpatchIdeConversationForking,
    FORK_TARGET,
    FORK_REPLACEMENT
};
