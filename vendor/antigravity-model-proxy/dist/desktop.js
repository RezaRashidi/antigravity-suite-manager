"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.install = install;
/** Custom-model integration installed alongside the current vendor desktop runtime. */
const electron_1 = require("electron");
const customIpc_1 = require("./customIpc");
const proxy_1 = require("./proxy");
let installed = false;
function install(getLanguageServerPort) {
    if (installed)
        return;
    installed = true;
    (0, customIpc_1.registerCustomModelHandlers)();
    // Registered before the vendor's ready callback, without replacing its startup,
    // updater, WSL integration, certificate policy, or window configuration.
    void electron_1.app.whenReady().then(() => {
        electron_1.session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
            const proxyPort = (0, proxy_1.getProxyPort)();
            const lsPort = getLanguageServerPort();
            if (!proxyPort || !lsPort)
                return callback({});
            const url = new URL(details.url);
            if (!['http:', 'https:'].includes(url.protocol) ||
                !['127.0.0.1', 'localhost'].includes(url.hostname) ||
                Number(url.port) !== lsPort) {
                return callback({});
            }
            if (/(?:\/|\.)LanguageServerService\/SetCloudCodeURL$/.test(url.pathname)) {
                callback({ cancel: true });
            }
            else if (/(?:\/|\.)LanguageServerService\/GetAvailableModels$/.test(url.pathname)) {
                callback({
                    redirectURL: `http://127.0.0.1:${proxyPort}/GetAvailableModels?ls=${encodeURIComponent(details.url)}`,
                });
            }
            else
                callback({});
        });
    });
    electron_1.app.on('browser-window-created', (_event, win) => {
        win.webContents.on('did-fail-load', (_event, code, description, _url, isMainFrame) => {
            if (!isMainFrame || code === -3 || win.isDestroyed())
                return;
            console.error('[Model Patch] Desktop page failed to load:', code, description);
            electron_1.dialog.showErrorBox('Antigravity could not load', `${description} (${code})\n\nCheck the Electron and language-server logs. ` +
                'If this began after an update, reinstall a clean vendor build and run the patch preflight again.');
        });
        win.webContents.on('preload-error', (_event, _preload, error) => {
            console.error('[Model Patch] Preload failed:', error);
        });
    });
    electron_1.app.on('will-quit', () => {
        void (0, proxy_1.stopProxy)();
    });
}
//# sourceMappingURL=desktop.js.map