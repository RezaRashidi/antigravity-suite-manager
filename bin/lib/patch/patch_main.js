// Main Process Patcher (Desktop Name, EPIPE Error Suppression, electron-log guards)
const fs = require('fs');
const path = require('path');

function patchMain(dir) {
    const mainPath = path.join(dir, 'dist', 'main.js');
    if (fs.existsSync(mainPath)) {
        let mainCode = fs.readFileSync(mainPath, 'utf8');
        if (!mainCode.includes('EPIPE_SUPPRESSION_START')) {
            const epipeHead = `/* EPIPE_SUPPRESSION_START */
['stdout', 'stderr'].forEach(function(s) {
    if (process[s] && typeof process[s].on === 'function') {
        process[s].on('error', function(e) { if (e && (e.code === 'EPIPE' || e.code === 'ERR_STREAM_DESTROYED')) return; });
    }
});
process.on('uncaughtException', function(e) { if (e && (e.code === 'EPIPE' || (e.message && e.message.includes('EPIPE')))) return; });
/* EPIPE_SUPPRESSION_END */\n`;
            mainCode = epipeHead + mainCode;
        }
        if (!mainCode.includes('process.env.ANTIGRAVITY_DESKTOP_NAME')) {
            mainCode = mainCode.replace(
                'const gotTheLock = electron_1.app.requestSingleInstanceLock();',
                'if (process.env.ANTIGRAVITY_DESKTOP_NAME && electron_1.app.setDesktopName) {\n    try { electron_1.app.setDesktopName(process.env.ANTIGRAVITY_DESKTOP_NAME); } catch (_) {}\n}\nconst gotTheLock = electron_1.app.requestSingleInstanceLock();'
            );
        }
        if (mainCode.includes('Object.assign(console, main_1.default.functions);') && !mainCode.includes('__guardedConsoleWrite')) {
            const guard = `Object.assign(console, main_1.default.functions);
    try {
        if (main_1?.default?.transports?.console) {
            const _ow = main_1.default.transports.console.writeFn;
            main_1.default.transports.console.writeFn = function(a) {
                try { _ow.call(this, a); } catch (err) { if (err && (err.code === 'EPIPE' || (err.message && err.message.includes('EPIPE')))) return; throw err; }
            };
            main_1.default.transports.console.__guardedConsoleWrite = true;
        }
    } catch (_) {}`;
            mainCode = mainCode.replace('Object.assign(console, main_1.default.functions);', guard);
        }
        fs.writeFileSync(mainPath, mainCode, 'utf8');
        console.log('[Patch] dist/main.js patched with desktop name and EPIPE suppression.');
    }

    const logConsole = path.join(dir, 'node_modules', 'electron-log', 'src', 'node', 'transports', 'console.js');
    if (fs.existsSync(logConsole)) {
        let code = fs.readFileSync(logConsole, 'utf8');
        if (!code.includes('/* EPIPE_LOG_GUARD */')) {
            code = code.replace(
                'const consoleLogFn = consoleMethods[message.level] || consoleMethods.info;\n      consoleLogFn(...message.data);',
                `try { /* EPIPE_LOG_GUARD */\n        const consoleLogFn = consoleMethods[message.level] || consoleMethods.info;\n        consoleLogFn(...message.data);\n      } catch (e) { if (e && (e.code === 'EPIPE' || (e.message && e.message.includes('EPIPE')))) return; throw e; }`
            );
            fs.writeFileSync(logConsole, code, 'utf8');
            console.log('[Patch] electron-log console transport patched against EPIPE.');
        }
    }
}

function unpatchMain(dir) {
    const mainPath = path.join(dir, 'dist', 'main.js');
    if (fs.existsSync(mainPath)) {
        let mainCode = fs.readFileSync(mainPath, 'utf8');
        mainCode = mainCode.replace(/\/\* EPIPE_SUPPRESSION_START \*\/[\s\S]*?\/\* EPIPE_SUPPRESSION_END \*\/\n?/g, '');
        mainCode = mainCode.replace(/if \(process\.env\.ANTIGRAVITY_DESKTOP_NAME[\s\S]*?requestSingleInstanceLock\(\);/, 'const gotTheLock = electron_1.app.requestSingleInstanceLock();');
        mainCode = mainCode.replace(/\n\s*try \{\s*if \(main_1[\s\S]*?__guardedConsoleWrite = true;\s*\}\s*\} catch \(_\) \{\}/g, '');
        fs.writeFileSync(mainPath, mainCode, 'utf8');
    }
}

module.exports = { patchMain, unpatchMain };
