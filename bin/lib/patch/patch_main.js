const fs = require('fs');
const path = require('path');

function patchMain(dir) {
    const mainPath = path.join(dir, 'dist', 'main.js');
    if (!fs.existsSync(mainPath)) return;
    let mainCode = fs.readFileSync(mainPath, 'utf8');
    if (mainCode.includes('process.env.ANTIGRAVITY_DESKTOP_NAME')) {
        console.log('[Patch] dist/main.js already has setDesktopName.');
        return;
    }
    mainCode = mainCode.replace(
        'const gotTheLock = electron_1.app.requestSingleInstanceLock();',
        'if (process.env.ANTIGRAVITY_DESKTOP_NAME && electron_1.app.setDesktopName) {\n    try { electron_1.app.setDesktopName(process.env.ANTIGRAVITY_DESKTOP_NAME); } catch (_) {}\n}\nconst gotTheLock = electron_1.app.requestSingleInstanceLock();'
    );
    fs.writeFileSync(mainPath, mainCode, 'utf8');
    console.log('[Patch] dist/main.js patched with setDesktopName.');
}

module.exports = { patchMain };
