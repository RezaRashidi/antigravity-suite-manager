const fs = require('fs');
const path = require('path');

function patchLanguageServer(dir) {
    const lsPath = path.join(dir, 'dist', 'languageServer.js');
    if (!fs.existsSync(lsPath)) return;
    let lsCode = fs.readFileSync(lsPath, 'utf8');
    if (lsCode.includes('exports.restartLanguageServer = restartLanguageServer;')) {
        console.log('[Patch] dist/languageServer.js already has restartLanguageServer.');
        return;
    }
    let varsDeclaration = '\nlet _lastPort = 0;\nlet _lastCsrf = "";\nlet _lastOptions = null;\nlet _isRestarting = false;\n';
    if (!lsCode.includes('let _lsPort')) varsDeclaration += 'let _lsPort = 0;\n';
    if (!lsCode.includes('let _restartCount')) varsDeclaration += 'let _restartCount = 0;\n';

    const restartFunc = varsDeclaration + `
async function restartLanguageServer() {
    if (_isRestarting) return;
    _isRestarting = true;
    try { _restartCount = 0; } catch (_) {}
    console.log('[LanguageServer] Clean restart requested...');
    try {
        try { if (typeof setIntentionalTermination === 'function') setIntentionalTermination(true); } catch (_) {}
        await killLanguageServer();
        try { if (typeof setIntentionalTermination === 'function') setIntentionalTermination(false); } catch (_) {}
        const newHandle = await startLanguageServer(_lastPort, _lastCsrf, _lastOptions);
        _lsPort = newHandle.port;
        if (_lastOptions && _lastOptions.onPortChanged) _lastOptions.onPortChanged(_lsPort);
        monitorLsCrashInternal(newHandle, _lsPort, _lastCsrf, _lastOptions);
        console.log('[LanguageServer] Restarted successfully on port ' + _lsPort);
    } catch (err) {
        console.error('[LanguageServer] Restart failed: ' + err.message);
    } finally {
        _isRestarting = false;
    }
}
exports.restartLanguageServer = restartLanguageServer;
`;
    const startMonitorRegex = /async\s+function\s+startAndMonitorLanguageServer\s*\(([^)]*)\)\s*\{/;
    if (startMonitorRegex.test(lsCode)) {
        lsCode = lsCode.replace(
            startMonitorRegex,
            'async function startAndMonitorLanguageServer($1) {\n    _lastPort = arguments[0];\n    _lastCsrf = arguments[1];\n    _lastOptions = arguments[2];'
        );
    }
    lsCode = lsCode.replace(
        'function monitorLsCrashInternal(handle, port, csrf, options) {',
        restartFunc + '\nfunction monitorLsCrashInternal(handle, port, csrf, options) {'
    );
    fs.writeFileSync(lsPath, lsCode, 'utf8');
    console.log('[Patch] dist/languageServer.js patched.');
}

module.exports = { patchLanguageServer };
