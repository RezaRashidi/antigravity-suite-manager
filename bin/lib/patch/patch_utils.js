const fs = require('fs');
const path = require('path');
const { patchUtilsWindow } = require('./patch_utils_window');
const { patchUtilsReload } = require('./patch_utils_reload');

function patchUtils(dir) {
    const utilsPath = path.join(dir, 'dist', 'utils.js');
    if (!fs.existsSync(utilsPath)) return;
    let utilsCode = fs.readFileSync(utilsPath, 'utf8');
    const initialCode = utilsCode;

    utilsCode = patchUtilsWindow(utilsCode);
    utilsCode = patchUtilsReload(utilsCode);

    if (utilsCode !== initialCode) {
        fs.writeFileSync(utilsPath, utilsCode, 'utf8');
        console.log('[Patch] dist/utils.js successfully patched.');
    } else {
        console.log('[Patch] dist/utils.js already patched.');
    }
}

module.exports = { patchUtils };
