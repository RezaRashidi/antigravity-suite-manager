const fs = require('fs');
const path = require('path');

function patchKeybindings(dir) {
    const kbPath = path.join(dir, 'dist', 'keybindings.js');
    if (!fs.existsSync(kbPath)) return;
    let kbCode = fs.readFileSync(kbPath, 'utf8');
    if (kbCode.includes("input.key === 'F5'") || kbCode.includes('onRestartRequested')) {
        console.log('[Patch] dist/keybindings.js already includes F5 keybinding.');
        return;
    }
    const targetRegex = /(if\s*\(\s*isCmdOrCtrl\s*&&\s*input\.key\.toLowerCase\(\)\s*===\s*['"]q['"]\s*\)\s*\{[\s\S]*?actions\.onQuitRequested\(\);[\s\S]*?event\.preventDefault\(\);(?:\s*return;)?\s*\})/;
    const extraBindings = `
            if ((isCmdOrCtrl && input.key.toLowerCase() === 'r') || input.key === 'F5') {
                if (actions && typeof actions.onRestartRequested === 'function') {
                    actions.onRestartRequested();
                } else if (win && !win.isDestroyed() && win.webContents) {
                    if (input.shift) win.webContents.reloadIgnoringCache();
                    else win.webContents.reload();
                }
                event.preventDefault();
                return;
            }
            if ((isCmdOrCtrl && input.shift && input.key.toLowerCase() === 'i') || input.key === 'F12') {
                if (win && !win.isDestroyed() && win.webContents) {
                    win.webContents.toggleDevTools();
                }
                event.preventDefault();
                return;
            }`;

    if (targetRegex.test(kbCode)) {
        kbCode = kbCode.replace(targetRegex, `$1${extraBindings}`);
        fs.writeFileSync(kbPath, kbCode, 'utf8');
        console.log('[Patch] dist/keybindings.js successfully patched with F5 and Ctrl+R.');
    } else {
        console.error('[Patch ERROR] dist/keybindings.js target pattern not found!');
    }
}

module.exports = { patchKeybindings };
