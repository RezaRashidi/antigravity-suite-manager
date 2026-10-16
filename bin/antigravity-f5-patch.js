#!/usr/bin/env node
// ==============================================================================
// Antigravity F5 Manual Backend Sync & Profile Isolation Patcher
// Injects:
//   1. Clean backend reload (restartLanguageServer) into languageServer.js
//   2. Active agent count tracking into ipcHandlers.js
//   3. F5 / Ctrl+R keybinding into keybindings.js
//   4. Native Account 2 window title, icon, and WM_CLASS into utils.js
//   5. Native Account 2 tray icon & tooltip into tray.js
//   6. Native setDesktopName into main.js
// ==============================================================================

const fs = require('fs');
const path = require('path');

const dir = process.argv[2];
if (!dir || !fs.existsSync(dir)) {
    console.error('Target directory not specified or does not exist:', dir);
    process.exit(1);
}

console.log('[Patch] Patching unpacked asar in:', dir);

// ------------------------------------------------------------------------------
// 1. dist/languageServer.js
// ------------------------------------------------------------------------------
const lsPath = path.join(dir, 'dist', 'languageServer.js');
if (fs.existsSync(lsPath)) {
    let lsCode = fs.readFileSync(lsPath, 'utf8');
    if (!lsCode.includes('exports.restartLanguageServer = restartLanguageServer;')) {
        const varsDeclaration = `
let _lsPort = 0;
let _lastPort = 0;
let _lastCsrf = '';
let _lastOptions = null;
let _isRestarting = false;
let _restartCount = 0;
`;
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
        if (_lastOptions && _lastOptions.onPortChanged) {
            _lastOptions.onPortChanged(_lsPort);
        }
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
                `async function startAndMonitorLanguageServer($1) {\n    _lastPort = arguments[0];\n    _lastCsrf = arguments[1];\n    _lastOptions = arguments[2];`
            );
        }
        lsCode = lsCode.replace(
            'function monitorLsCrashInternal(handle, port, csrf, options) {',
            restartFunc + '\nfunction monitorLsCrashInternal(handle, port, csrf, options) {'
        );
        fs.writeFileSync(lsPath, lsCode, 'utf8');
        console.log('[Patch] dist/languageServer.js patched.');
    } else {
        console.log('[Patch] dist/languageServer.js already has restartLanguageServer.');
    }
}

// ------------------------------------------------------------------------------
// 2. dist/ipcHandlers.js
// ------------------------------------------------------------------------------
const ipcPath = path.join(dir, 'dist', 'ipcHandlers.js');
if (fs.existsSync(ipcPath)) {
    let ipcCode = fs.readFileSync(ipcPath, 'utf8');
    if (!ipcCode.includes('global.__active_agent_count__ =')) {
        ipcCode = ipcCode.replace(
            "electron_1.ipcMain.handle('agent:update-active-count', async (_event, count) => {",
            `global.__active_agent_count__ = 0;\n    electron_1.ipcMain.handle('agent:update-active-count', async (_event, count) => {\n        global.__active_agent_count__ = typeof count === 'number' ? count : 0;`
        );
        fs.writeFileSync(ipcPath, ipcCode, 'utf8');
        console.log('[Patch] dist/ipcHandlers.js patched.');
    } else {
        console.log('[Patch] dist/ipcHandlers.js already tracks active agent count.');
    }
}

// ------------------------------------------------------------------------------
// 3. dist/keybindings.js
// ------------------------------------------------------------------------------
const kbPath = path.join(dir, 'dist', 'keybindings.js');
if (fs.existsSync(kbPath)) {
    let kbCode = fs.readFileSync(kbPath, 'utf8');
    if (!kbCode.includes("input.key === 'F5'") && !kbCode.includes('onRestartRequested')) {
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
    } else {
        console.log('[Patch] dist/keybindings.js already includes F5 keybinding.');
    }
}

// ------------------------------------------------------------------------------
// 4. dist/utils.js
// ------------------------------------------------------------------------------
const utilsPath = path.join(dir, 'dist', 'utils.js');
if (fs.existsSync(utilsPath)) {
    let utilsCode = fs.readFileSync(utilsPath, 'utf8');

    // 4.1 Custom window title & icon support in BrowserWindow config
    if (!utilsCode.includes('process.env.ANTIGRAVITY_WINDOW_TITLE')) {
        utilsCode = utilsCode.replace(
            'title: electron_1.app.getName() + wslBadge,',
            `title: (process.env.ANTIGRAVITY_WINDOW_TITLE ? ("[" + process.env.ANTIGRAVITY_WINDOW_TITLE + "] ") : "") + electron_1.app.getName() + wslBadge,`
        );
        utilsCode = utilsCode.replace(
            "icon: path_1.default.join(__dirname, '..', 'icon.png'),",
            `icon: process.env.ANTIGRAVITY_ICON_PATH || path_1.default.join(__dirname, '..', 'icon.png'),`
        );
    }

    // 4.2 Preserve [Account 2] prefix across page-title-updated events
    if (!utilsCode.includes('const prefix = process.env.ANTIGRAVITY_WINDOW_TITLE')) {
        const titleUpdateRegex = /win\.on\('page-title-updated',\s*\([^)]*\)\s*=>\s*\{[\s\S]*?win\.setTitle\([^)]*\);[\s\S]*?\}\);/;
        const titleUpdateReplacement = `win.on('page-title-updated', (event, title) => {
        const maxLength = 25;
        const truncated = title.length > maxLength ? title.substring(0, maxLength) + '...' : title;
        const prefix = process.env.ANTIGRAVITY_WINDOW_TITLE ? ("[" + process.env.ANTIGRAVITY_WINDOW_TITLE + "] ") : "";
        event.preventDefault();
        win.setTitle(prefix + truncated + wslBadge);
    });`;
        if (titleUpdateRegex.test(utilsCode)) {
            utilsCode = utilsCode.replace(titleUpdateRegex, titleUpdateReplacement);
            console.log('[Patch] dist/utils.js patched with sticky custom window title.');
        } else {
            console.error('[Patch ERROR] dist/utils.js page-title-updated pattern not found!');
        }
    }

    // 4.3 Native X11 WM_CLASS assignment on BrowserWindow creation
    if (!utilsCode.includes('xprop -id ${xid} -f WM_CLASS 8s')) {
        const overlayTarget = '(0, loadingOverlay_1.attachLoadingOverlay)(win, foregroundColor, backgroundColor);';
        const overlayReplacement = overlayTarget + `
    if (process.env.ANTIGRAVITY_APP_NAME || process.env.ANTIGRAVITY_DESKTOP_NAME) {
        try {
            const handle = win.getNativeWindowHandle();
            if (handle && handle.length >= 4) {
                const xid = handle.readUInt32LE(0);
                if (xid) {
                    const wmClass = (process.env.ANTIGRAVITY_APP_NAME || process.env.ANTIGRAVITY_DESKTOP_NAME).replace(/\\.desktop$/i, '');
                    require('child_process').exec(\`xprop -id \${xid} -f WM_CLASS 8s -set WM_CLASS "\${wmClass}"\`);
                }
            }
        } catch (_) {}
    }`;
        if (utilsCode.includes(overlayTarget)) {
            utilsCode = utilsCode.replace(overlayTarget, overlayReplacement);
            console.log('[Patch] dist/utils.js patched with native WM_CLASS setting.');
        } else {
            console.error('[Patch ERROR] dist/utils.js attachLoadingOverlay pattern not found!');
        }
    }

    // 4.4 onRestartRequested handler for F5 reload
    if (!utilsCode.includes('onRestartRequested:')) {
        const target = `        onQuitRequested: () => {
            exports.showQuitConfirmation = true;
            electron_1.app.quit();
        },`;
        const replacement = target + `
        onRestartRequested: async () => {
            console.log('[Keybindings] Full backend & window sync requested via shortcut');
            let isGenerating = false;
            if (win && !win.isDestroyed() && win.webContents) {
                try {
                    isGenerating = await win.webContents.executeJavaScript(\`(() => {
                        return Boolean(
                            document.querySelector('button[aria-label*="Stop" i]') ||
                            document.querySelector('button[aria-label*="Cancel" i]') ||
                            document.querySelector('[data-testid="stop-button"]')
                        );
                    })()\`);
                } catch (_) {}
            }
            if ((global.__active_agent_count__ && global.__active_agent_count__ > 0) || isGenerating) {
                console.log('[Keybindings] Manual sync blocked: active agent or generation running.');
                if (win && !win.isDestroyed() && win.webContents) {
                    try {
                        void win.webContents.executeJavaScript("(() => { if (document.getElementById('__antigravity_sync_toast__')) return; const t = document.createElement('div'); t.id = '__antigravity_sync_toast__'; t.innerText = 'Cannot sync: Task is currently running'; t.style.cssText = 'position:fixed;top:20px;right:20px;background:#e53e3e;color:#fff;padding:8px 16px;border-radius:8px;z-index:999999;font-family:sans-serif;font-size:13px;pointer-events:none;box-shadow:0 4px 12px rgba(0,0,0,0.3);'; document.body.appendChild(t); setTimeout(() => t.remove(), 3000); })()");
                    } catch (_) {}
                }
                return;
            }
            if (win && !win.isDestroyed() && win.webContents) {
                try {
                    void win.webContents.executeJavaScript("(() => { if (document.getElementById('__antigravity_sync_toast__')) return; const t = document.createElement('div'); t.id = '__antigravity_sync_toast__'; t.innerText = 'Syncing...'; t.style.cssText = 'position:fixed;top:20px;right:20px;background:rgba(0,0,0,0.85);color:#fff;padding:8px 16px;border-radius:8px;z-index:999999;font-family:sans-serif;font-size:13px;pointer-events:none;box-shadow:0 4px 12px rgba(0,0,0,0.3);'; document.body.appendChild(t); })()");
                } catch (_) {}
            }
            const languageServer = require('./languageServer');
            if (languageServer && languageServer.restartLanguageServer) {
                try {
                    await languageServer.restartLanguageServer();
                } catch (_) {}
            }
            if (win && !win.isDestroyed() && win.webContents) {
                setTimeout(() => {
                    try {
                        if (win && !win.isDestroyed() && win.webContents) {
                            win.webContents.reload();
                        }
                    } catch (_) {}
                }, 300);
            }
        },`;
        utilsCode = utilsCode.replace(target, replacement);
        console.log('[Patch] dist/utils.js patched with onRestartRequested.');
    }

    fs.writeFileSync(utilsPath, utilsCode, 'utf8');
}

// ------------------------------------------------------------------------------
// 5. dist/tray.js
// ------------------------------------------------------------------------------
const trayPath = path.join(dir, 'dist', 'tray.js');
if (fs.existsSync(trayPath)) {
    let trayCode = fs.readFileSync(trayPath, 'utf8');
    if (!trayCode.includes('process.env.ANTIGRAVITY_TRAY_ICON_PATH')) {
        const targetTrayIcon = "const icon = electron_1.nativeImage.createFromPath(path.join(__dirname, '..', iconFile));";
        const replacementTrayIcon = `const defaultIconPath = path.join(__dirname, '..', iconFile);
    const trayIconPath = process.env.ANTIGRAVITY_TRAY_ICON_PATH || defaultIconPath;
    const icon = electron_1.nativeImage.createFromPath(trayIconPath);`;

        const targetTooltip = "tray.setToolTip(electron_1.app.getName());";
        const replacementTooltip = `const trayTooltip = process.env.ANTIGRAVITY_WINDOW_TITLE ? \`\${electron_1.app.getName()} (\${process.env.ANTIGRAVITY_WINDOW_TITLE})\` : electron_1.app.getName();
    tray.setToolTip(trayTooltip);`;

        if (trayCode.includes(targetTrayIcon)) {
            trayCode = trayCode.replace(targetTrayIcon, replacementTrayIcon);
        }
        if (trayCode.includes(targetTooltip)) {
            trayCode = trayCode.replace(targetTooltip, replacementTooltip);
        }
        fs.writeFileSync(trayPath, trayCode, 'utf8');
        console.log('[Patch] dist/tray.js patched with custom tray icon and tooltip.');
    } else {
        console.log('[Patch] dist/tray.js already has custom tray icon support.');
    }
}

// ------------------------------------------------------------------------------
// 6. dist/main.js
// ------------------------------------------------------------------------------
const mainPath = path.join(dir, 'dist', 'main.js');
if (fs.existsSync(mainPath)) {
    let mainCode = fs.readFileSync(mainPath, 'utf8');
    if (!mainCode.includes('process.env.ANTIGRAVITY_DESKTOP_NAME')) {
        mainCode = mainCode.replace(
            'const gotTheLock = electron_1.app.requestSingleInstanceLock();',
            `if (process.env.ANTIGRAVITY_DESKTOP_NAME && electron_1.app.setDesktopName) {
    try { electron_1.app.setDesktopName(process.env.ANTIGRAVITY_DESKTOP_NAME); } catch (_) {}
}
const gotTheLock = electron_1.app.requestSingleInstanceLock();`
        );
        fs.writeFileSync(mainPath, mainCode, 'utf8');
        console.log('[Patch] dist/main.js patched with setDesktopName.');
    } else {
        console.log('[Patch] dist/main.js already has setDesktopName.');
    }
}

console.log('[Patch] All patches completed successfully.');
