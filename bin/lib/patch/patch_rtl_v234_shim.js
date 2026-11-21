#!/usr/bin/env node
// Compatibility shim for antigravity-rtl on Antigravity App >= v2.34.0
// where `void win.loadURL(url);` was refactored to `await win.loadURL(url);`.
const fs = require('fs');
const path = require('path');

const mode = process.argv[2];
const unpackedDir = process.argv[3];
if (!mode || !unpackedDir) {
    console.error('Usage: patch_rtl_v234_shim.js <--prepare|--finalize> <unpacked_dir>');
    process.exit(1);
}

const utilsPath = path.join(unpackedDir, 'dist', 'utils.js');
if (!fs.existsSync(utilsPath)) process.exit(0);

let code = fs.readFileSync(utilsPath, 'utf8');

if (mode === '--prepare') {
    if (!code.includes('/* ANTIGRAVITY RTL PATCH */') &&
        !code.includes('void win.loadURL(url);') &&
        code.includes('await win.loadURL(url);')) {
        code = code.replace('await win.loadURL(url);', 'void win.loadURL(url);');
        fs.writeFileSync(utilsPath, code, 'utf8');
        console.log('PREPARED');
    } else {
        console.log('NOOP');
    }
} else if (mode === '--finalize') {
    const startTag = '/* ANTIGRAVITY RTL PATCH */';
    const endTag = '/* END ANTIGRAVITY RTL PATCH */';
    const sIdx = code.indexOf(startTag);
    const eIdx = code.indexOf(endTag);
    if (sIdx !== -1 && eIdx !== -1 && eIdx > sIdx) {
        let block = code.slice(sIdx, eIdx);
        if (block.includes('void win.loadURL(url);')) {
            // Register dom-ready before awaiting loadURL so dom-ready is never missed.
            block = block.replace(/\n[ \t]*void win\.loadURL\(url\);/, '');
            code = code.slice(0, sIdx) + block.trimEnd() + '\n    await win.loadURL(url);\n' + code.slice(eIdx);
            fs.writeFileSync(utilsPath, code, 'utf8');
            console.log('FINALIZED');
        }
    }
}
