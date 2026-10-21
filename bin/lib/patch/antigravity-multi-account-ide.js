// Antigravity Multi-Account IDE Main-Process Injection Hook
import { app, ipcMain, BrowserWindow } from 'electron';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const require = createRequire(import.meta.url);

try {
    const router = require('./multi_account_router.js');
    if (router?.startMultiAccountRouter) router.startMultiAccountRouter(41999);
} catch (_) {}

function registerIpc() {
    try {
        if (ipcMain._multiAccountRegistered) return;
        ipcMain._multiAccountRegistered = true;
        const router = require('./multi_account_router.js');
        ipcMain.handle('multi-account:get-state', async () => {
            const accounts = router.loadAllAccountsWithQuotasSync ? router.loadAllAccountsWithQuotasSync() : Object.values(router.loadAllAccounts());
            return { accounts, bindings: router.getBindings(), active_default: router.getActiveAccountEmail?.() };
        });
        ipcMain.handle('multi-account:bind-cascade', async (_e, c, em, m) => {
            router.setBinding(c, em, m || '');
            if (router.setActiveAccount) router.setActiveAccount(em);
            return true;
        });
        ipcMain.handle('multi-account:set-active-account', async (_e, em) => {
            if (router.setActiveAccount) router.setActiveAccount(em);
            return true;
        });
        ipcMain.handle('multi-account:remove-account', async (_e, em) => {
            if (router.removeAccount) router.removeAccount(em);
            return true;
        });
        ipcMain.handle('multi-account:start-login', async () => {
            const { spawn } = require('child_process'), rh = process.env.REAL_HOME || require('os').homedir();
            const py = process.platform === 'win32' ? 'python' : (process.env.PYTHON || 'python3');
            const sDirs = [process.env.ANTIGRAVITY_SUITE_DIR, path.join(rh, 'PhpstormProjects', 'antigravity-suite-manager'), path.join(rh, '.antigravity-suite-manager')].filter(Boolean);
            const env = { ...process.env, REAL_HOME: rh, ANTIGRAVITY_ACCOUNTS_DIR: process.env.ANTIGRAVITY_ACCOUNTS_DIR || path.join(rh, '.config', 'antigravity', 'accounts'), PYTHONPATH: sDirs.map(d => path.join(d, 'src')).join(':') + (process.env.PYTHONPATH ? ':' + process.env.PYTHONPATH : '') };
            spawn(py, ['-m', 'antigravity_suite.multi_account.cli', 'login'], { detached: true, stdio: 'ignore', env }).unref();
            return true;
        });
    } catch (_) {}
}
registerIpc();

function injectToWebContents(wc) {
    try {
        const url = wc.getURL() || '';
        if (!url.includes('workbench') && !url.includes('jetski') && !url.endsWith('.html') && url !== '') return;
        const cssPath = path.join(__dirname, 'ui', 'styles.css');
        if (fs.existsSync(cssPath)) void wc.insertCSS(fs.readFileSync(cssPath, 'utf8'));
        const bridge = `if (!window.antigravityMultiAccount) {
            window.antigravityMultiAccount = {
                getState: () => fetch('http://127.0.0.1:41999/api/multi-account/state').then(r => r.json()),
                bindCascade: (c, e, m) => fetch('http://127.0.0.1:41999/api/multi-account/bind', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cascadeId:c,email:e,model:m,active:true})}).then(r => r.json()),
                setActiveAccount: (e) => fetch('http://127.0.0.1:41999/api/multi-account/bind', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cascadeId:'__default__',email:e,active:true})}).then(r => r.json()),
                removeAccount: (e) => fetch('http://127.0.0.1:41999/api/multi-account/remove', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:e})}).then(r => r.json()),
                startLogin: () => fetch('http://127.0.0.1:41999/api/multi-account/login', {method:'POST'}).then(r => r.json())
            };
        };`;
        const scripts = [bridge];
        for (const s of ['ui/flyout.js', 'ui/mount.js', 'multi_account_ui.js']) {
            const sp = path.join(__dirname, s);
            if (fs.existsSync(sp)) scripts.push(fs.readFileSync(sp, 'utf8'));
        }
        void wc.executeJavaScript(scripts.join('\n;\n')).catch(e => console.error('[MultiAccount IDE] eval error:', e.message));
    } catch (_) {}
}

app.on('browser-window-created', (_event, win) => {
    win.webContents.on('dom-ready', () => injectToWebContents(win.webContents));
    win.webContents.on('did-finish-load', () => injectToWebContents(win.webContents));
});
app.on('web-contents-created', (_event, contents) => {
    contents.on('dom-ready', () => injectToWebContents(contents));
    contents.on('did-finish-load', () => injectToWebContents(contents));
});
app.whenReady().then(() => {
    try { for (const win of BrowserWindow.getAllWindows()) injectToWebContents(win.webContents); } catch (_) {}
});
