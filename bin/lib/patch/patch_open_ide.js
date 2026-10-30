// Antigravity Native "Open in IDE" Titlebar Button Patcher
const fs = require('fs'), path = require('path');
const MARKER = 'antigravity_open_ide_patch.marker';
const PRE_START = '/* OPEN_IDE_PRELOAD_START */', PRE_END = '/* OPEN_IDE_PRELOAD_END */';
const CST_START = '/* OPEN_IDE_CONST_START */', CST_END = '/* OPEN_IDE_CONST_END */';

const SNIPPET = `${PRE_START}
try {
    const { webFrame } = require('electron');
    if (webFrame && typeof webFrame.executeJavaScriptInIsolatedWorld === 'function') {
        webFrame.executeJavaScriptInIsolatedWorld(0, [{
            code: \`(function() {
                try {
                    const os = Map.prototype.set, og = Map.prototype.get;
                    Map.prototype.set = function(k, v) {
                        if (k === 'titlebarComponent' && v && typeof v === 'object') v.showOpenIde = true;
                        return os.call(this, k, v);
                    };
                    Map.prototype.get = function(k) {
                        const v = og.call(this, k);
                        if (k === 'titlebarComponent' && v && typeof v === 'object') { v.showOpenIde = true; return v; }
                        return v;
                    };
                } catch (_) {}
            })();\`
        }]);
    }
} catch (_) {}
${PRE_END}\n`;

function resolveDist(dir) {
    if (!dir) return null;
    return fs.existsSync(path.join(dir, 'dist', 'preload.js')) ? path.join(dir, 'dist') : (fs.existsSync(path.join(dir, 'preload.js')) ? dir : null);
}

function patchAppOpenIde(targetDir) {
    const dist = resolveDist(targetDir);
    if (!dist) return false;
    const pPath = path.join(dist, 'preload.js'), cPath = path.join(dist, 'ideInstall', 'constants.js');
    if (fs.existsSync(pPath)) {
        let code = fs.readFileSync(pPath, 'utf8');
        if (code.includes(PRE_START)) code = code.replace(/\/\* OPEN_IDE_PRELOAD_START \*\/[\s\S]*?\/\* OPEN_IDE_PRELOAD_END \*\/\n?/, '');
        fs.writeFileSync(pPath, SNIPPET + code, 'utf8');
    }
    if (fs.existsSync(cPath)) {
        let code = fs.readFileSync(cPath, 'utf8');
        if (!code.includes(CST_START) && code.includes("case 'linux':")) {
            fs.writeFileSync(cPath, code.replace("case 'linux':", `case 'linux':\n            ${CST_START} if (fs.existsSync('/opt/antigravity-ide')) return '/opt/antigravity-ide'; ${CST_END}`), 'utf8');
        }
    }
    try { fs.writeFileSync(path.join(dist, MARKER), 'ANTIGRAVITY_SUITE_OPEN_IDE_PATCH_V1\n', 'utf8'); } catch (_) {}
    return true;
}

function unpatchAppOpenIde(targetDir) {
    const dist = resolveDist(targetDir);
    if (!dist) return false;
    const pPath = path.join(dist, 'preload.js'), cPath = path.join(dist, 'ideInstall', 'constants.js');
    if (fs.existsSync(pPath)) {
        let code = fs.readFileSync(pPath, 'utf8');
        if (code.includes(PRE_START)) fs.writeFileSync(pPath, code.replace(/\/\* OPEN_IDE_PRELOAD_START \*\/[\s\S]*?\/\* OPEN_IDE_PRELOAD_END \*\/\n?/, ''), 'utf8');
    }
    if (fs.existsSync(cPath)) {
        let code = fs.readFileSync(cPath, 'utf8');
        if (code.includes(CST_START)) fs.writeFileSync(cPath, code.replace(/\s*\/\* OPEN_IDE_CONST_START \*\/[\s\S]*?\/\* OPEN_IDE_CONST_END \*\//, ''), 'utf8');
    }
    try { const m = path.join(dist, MARKER); if (fs.existsSync(m)) fs.unlinkSync(m); } catch (_) {}
    return true;
}

if (require.main === module) {
    const args = process.argv.slice(2), dir = args.find(a => !a.startsWith('--'));
    if (dir) (args.includes('--unpatch') ? unpatchAppOpenIde(dir) : patchAppOpenIde(dir));
}

module.exports = { patchAppOpenIde, unpatchAppOpenIde };
