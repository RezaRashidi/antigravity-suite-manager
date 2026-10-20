const fs = require('fs');
const path = require('path');

function patchMultiAccount(dir) {
    console.log('[Patch] Applying Multi-Account subsystem patches in:', dir);
    const distDir = path.join(dir, 'dist');
    if (!fs.existsSync(distDir)) return;

    // 1. Copy multi_account_router.js and multi_account_ui.js into dist
    const routerSrc = path.join(__dirname, 'multi_account_router.js');
    const uiSrc = path.join(__dirname, 'multi_account_ui.js');
    if (fs.existsSync(routerSrc)) {
        fs.copyFileSync(routerSrc, path.join(distDir, 'multi_account_router.js'));
    }
    if (fs.existsSync(uiSrc)) {
        fs.copyFileSync(uiSrc, path.join(distDir, 'multi_account_ui.js'));
    }

    // 2. Patch languageServer.js
    const lsPath = path.join(distDir, 'languageServer.js');
    if (fs.existsSync(lsPath)) {
        let lsCode = fs.readFileSync(lsPath, 'utf8');
        if (!lsCode.includes("require('./multi_account_router')")) {
            lsCode = "try { require('./multi_account_router').startMultiAccountRouter(); } catch (_) {}\n" + lsCode;
        }
        lsCode = lsCode.replace(
            "'--cloud_code_endpoint',\n            'https://daily-cloudcode-pa.googleapis.com'",
            "'--cloud_code_endpoint',\n            (process.env.ANTIGRAVITY_CLOUD_CODE_ENDPOINT || 'http://127.0.0.1:41999')"
        );
        fs.writeFileSync(lsPath, lsCode, 'utf8');
        console.log('[Patch] dist/languageServer.js updated for multi-account proxy endpoint.');
    }

    // 3. Patch ipcHandlers.js
    const ipcPath = path.join(distDir, 'ipcHandlers.js');
    if (fs.existsSync(ipcPath)) {
        let ipcCode = fs.readFileSync(ipcPath, 'utf8');
        if (!ipcCode.includes("electron_1.ipcMain.handle('multi-account:get-state'")) {
            const ipcSnippets = `
    electron_1.ipcMain.handle('multi-account:get-state', async () => {
        try {
            const { spawnSync } = require('child_process');
            const res = spawnSync('python3', ['-m', 'antigravity_suite.multi_account.cli', 'json'], { encoding: 'utf8', timeout: 4000 });
            if (res.stdout) return JSON.parse(res.stdout);
        } catch (_) {}
        try {
            const router = require('./multi_account_router');
            return { accounts: Object.values(router.loadAllAccounts()), bindings: router.getBindings(), proxy_running: true };
        } catch (_) { return { accounts: [], bindings: {} }; }
    });
    electron_1.ipcMain.handle('multi-account:bind-cascade', async (_event, cascadeId, email, model) => {
        try {
            const router = require('./multi_account_router');
            router.setBinding(cascadeId, email, model || '');
            return true;
        } catch (_) { return false; }
    });
    electron_1.ipcMain.handle('multi-account:start-login', async () => {
        try {
            const { spawn } = require('child_process');
            spawn('python3', ['-m', 'antigravity_suite.multi_account.cli', 'login'], { detached: true, stdio: 'ignore' }).unref();
            return true;
        } catch (_) { return false; }
    });
`;
            ipcCode = ipcCode.replace(
                'function registerIpcHandlers(storageManager) {',
                'function registerIpcHandlers(storageManager) {' + ipcSnippets
            );
            fs.writeFileSync(ipcPath, ipcCode, 'utf8');
            console.log('[Patch] dist/ipcHandlers.js updated with multi-account channels.');
        }
    }

    // 4. Patch preload.js
    const preloadPath = path.join(distDir, 'preload.js');
    if (fs.existsSync(preloadPath)) {
        let preloadCode = fs.readFileSync(preloadPath, 'utf8');
        if (!preloadCode.includes("'antigravityMultiAccount'")) {
            const preloadSnippet = `
const multiAccountAPI = {
    getState: () => electron_1.ipcRenderer.invoke('multi-account:get-state'),
    bindCascade: (cascadeId, email, model) => electron_1.ipcRenderer.invoke('multi-account:bind-cascade', cascadeId, email, model),
    startLogin: () => electron_1.ipcRenderer.invoke('multi-account:start-login'),
};
electron_1.contextBridge.exposeInMainWorld('antigravityMultiAccount', multiAccountAPI);
`;
            preloadCode += '\n' + preloadSnippet;
            fs.writeFileSync(preloadPath, preloadCode, 'utf8');
            console.log('[Patch] dist/preload.js exposed window.antigravityMultiAccount.');
        }
    }

    // 5. Patch utils.js for UI injection on dom-ready
    const utilsPath = path.join(distDir, 'utils.js');
    if (fs.existsSync(utilsPath)) {
        let utilsCode = fs.readFileSync(utilsPath, 'utf8');
        if (!utilsCode.includes('multi_account_ui.js')) {
            const injectSnippet = `
        try {
            const uiCodePath = require('path').join(__dirname, 'multi_account_ui.js');
            if (require('fs').existsSync(uiCodePath)) {
                const uiCode = require('fs').readFileSync(uiCodePath, 'utf8');
                void win.webContents.executeJavaScript(uiCode);
            }
        } catch (e) {
            console.error('[MultiAccount] UI injection error:', e.message);
        }
`;
            utilsCode = utilsCode.replace(
                "win.webContents.on('dom-ready', () => {",
                "win.webContents.on('dom-ready', () => {" + injectSnippet
            );
            fs.writeFileSync(utilsPath, utilsCode, 'utf8');
            console.log('[Patch] dist/utils.js updated with multi-account UI injection.');
        }
    }
}

module.exports = { patchMultiAccount };
