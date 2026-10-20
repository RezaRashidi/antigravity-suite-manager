// Multi-Account Patcher: IPC Handlers and Preload Context Bridge
const fs = require('fs');
const path = require('path');

function patchIpcAndPreload(distDir) {
    const ipcPath = path.join(distDir, 'ipcHandlers.js');
    if (fs.existsSync(ipcPath)) {
        let code = fs.readFileSync(ipcPath, 'utf8');
        if (!code.includes("electron_1.ipcMain.handle('multi-account:get-state'")) {
            const snippets = `
    electron_1.ipcMain.handle('multi-account:get-state', async () => {
        try {
            const router = require('./multi_account_router');
            let accounts = router.loadAllAccountsWithQuotasSync ? router.loadAllAccountsWithQuotasSync() : Object.values(router.loadAllAccounts());
            if (!accounts?.some(a => a.quotas?.length) && router.loadAllAccountsWithQuotas) {
                try { accounts = await Promise.race([router.loadAllAccountsWithQuotas(), new Promise(r => setTimeout(() => r(accounts), 800))]); } catch (_) {}
            }
            if (!accounts || !accounts.length) accounts = Object.values(router.loadAllAccounts());
            const bindings = router.getBindings();
            return { accounts, bindings, active_default: router.getActiveAccountEmail ? router.getActiveAccountEmail() : bindings.__active_account, proxy_running: true };
        } catch (_) {
            try { const router = require('./multi_account_router'); return { accounts: Object.values(router.loadAllAccounts()), bindings: router.getBindings() }; } catch (e) { return { accounts: [], bindings: {} }; }
        }
    });
    electron_1.ipcMain.handle('multi-account:bind-cascade', async (_event, cascadeId, email, model) => {
        try {
            const router = require('./multi_account_router');
            router.setBinding(cascadeId, email, model || '');
            if (router.setActiveAccount) router.setActiveAccount(email);
            return true;
        } catch (_) { return false; }
    });
    electron_1.ipcMain.handle('multi-account:set-active-account', async (_event, email) => {
        try {
            const router = require('./multi_account_router');
            if (router.setActiveAccount) router.setActiveAccount(email);
            return true;
        } catch (_) { return false; }
    });
    electron_1.ipcMain.handle('multi-account:start-login', async () => {
        try {
            const { spawn } = require('child_process');
            const py = process.platform === 'win32' ? 'python' : (process.env.PYTHON || 'python3');
            spawn(py, ['-m', 'antigravity_suite.multi_account.cli', 'login'], { detached: true, stdio: 'ignore' }).unref();
            return true;
        } catch (_) { return false; }
    });
    electron_1.ipcMain.handle('multi-account:log', async (_event, msg) => {
        try {
            const p = electron_1.app?.getPath ? electron_1.app.getPath('userData') : require('path').join(require('os').homedir(), '.config', 'antigravity');
            require('fs').mkdirSync(p, { recursive: true });
            require('fs').appendFileSync(require('path').join(p, 'ui_debug.log'), '[' + new Date().toISOString() + '] ' + msg + '\\n');
        } catch (_) {}
        return true;
    });
`;
            code = code.replace('function registerIpcHandlers(storageManager) {', 'function registerIpcHandlers(storageManager) {' + snippets);
            fs.writeFileSync(ipcPath, code, 'utf8');
        }
    }

    const preloadPath = path.join(distDir, 'preload.js');
    if (fs.existsSync(preloadPath)) {
        let code = fs.readFileSync(preloadPath, 'utf8');
        if (!code.includes("'antigravityMultiAccount'")) {
            const snippet = `
const multiAccountAPI = {
    getState: () => electron_1.ipcRenderer.invoke('multi-account:get-state'),
    bindCascade: (cascadeId, email, model) => electron_1.ipcRenderer.invoke('multi-account:bind-cascade', cascadeId, email, model),
    setActiveAccount: (email) => electron_1.ipcRenderer.invoke('multi-account:set-active-account', email),
    startLogin: () => electron_1.ipcRenderer.invoke('multi-account:start-login'),
    log: (msg) => electron_1.ipcRenderer.invoke('multi-account:log', msg),
};
electron_1.contextBridge.exposeInMainWorld('antigravityMultiAccount', multiAccountAPI);
`;
            fs.writeFileSync(preloadPath, code + '\n' + snippet, 'utf8');
        }
    }
}

function unpatchIpcAndPreload(distDir) {
    const ipcPath = path.join(distDir, 'ipcHandlers.js');
    if (fs.existsSync(ipcPath)) {
        let code = fs.readFileSync(ipcPath, 'utf8');
        code = code.replace(/electron_1\.ipcMain\.handle\('multi-account:get-state'[\s\S]*?electron_1\.ipcMain\.handle\('multi-account:log'[\s\S]*?\}\);/g, '');
        fs.writeFileSync(ipcPath, code, 'utf8');
    }
    const preloadPath = path.join(distDir, 'preload.js');
    if (fs.existsSync(preloadPath)) {
        let code = fs.readFileSync(preloadPath, 'utf8');
        code = code.replace(/const multiAccountAPI = \{[\s\S]*?electron_1\.contextBridge\.exposeInMainWorld\('antigravityMultiAccount', multiAccountAPI\);/g, '');
        fs.writeFileSync(preloadPath, code, 'utf8');
    }
}

module.exports = { patchIpcAndPreload, unpatchIpcAndPreload };
