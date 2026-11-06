// Antigravity Multi-Account IDE Main-Process Injection Hook
import * as electronModule from 'electron';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const require = createRequire(import.meta.url);

const electron = electronModule.default || electronModule;
let app = electronModule.app || electron.app;
let ipcMain = electronModule.ipcMain || electron.ipcMain;
let BrowserWindow = electronModule.BrowserWindow || electron.BrowserWindow;
let webContents = electronModule.webContents || electron.webContents;
let webFrameMain = electronModule.webFrameMain || electron.webFrameMain;
let sessionModule = electronModule.session || electron.session;

if (!app || !webContents) {
    try {
        const el = require('electron');
        app = app || el.app || el.default?.app;
        ipcMain = ipcMain || el.ipcMain || el.default?.ipcMain;
        BrowserWindow = BrowserWindow || el.BrowserWindow || el.default?.BrowserWindow;
        webContents = webContents || el.webContents || el.default?.webContents;
        webFrameMain = webFrameMain || el.webFrameMain || el.default?.webFrameMain;
        sessionModule = sessionModule || el.session || el.default?.session;
    } catch (_) {}
}

function relaxCsp(ses) {
    if (!ses?.webRequest?.onHeadersReceived || ses._agyCspRelaxed) return;
    ses._agyCspRelaxed = true;
    try {
        ses.webRequest.onHeadersReceived((details, callback) => {
            const responseHeaders = { ...details.responseHeaders };
            for (const key of Object.keys(responseHeaders)) {
                if (key.toLowerCase() === 'content-security-policy') {
                    const cspList = responseHeaders[key];
                    const arr = Array.isArray(cspList) ? cspList : [cspList];
                    responseHeaders[key] = arr.map(csp => {
                        if (/connect-src/i.test(csp)) {
                            return csp.replace(/connect-src\s+/i, "connect-src http://127.0.0.1:* http://localhost:* ws://127.0.0.1:* ");
                        }
                        return csp;
                    });
                }
            }
            callback({ responseHeaders });
        });
    } catch (_) {}
}
if (sessionModule?.defaultSession) relaxCsp(sessionModule.defaultSession);
if (app?.on) {
    app.on('session-created', (ses) => relaxCsp(ses));
}

function getRouter() {
    try {
        return require('./multi_account_router.cjs');
    } catch (_) {
        try {
            return require('./multi_account_router.js');
        } catch (e) {
            console.error('[MultiAccount IDE] Failed to load router:', e?.message || e);
            return null;
        }
    }
}

try {
    const router = getRouter();
    if (router?.startMultiAccountRouter) router.startMultiAccountRouter(41999);
} catch (e) {
    console.error('[MultiAccount IDE] Error starting router:', e?.message || e);
}

function registerIpc() {
    try {
        if (ipcMain._multiAccountRegistered) return;
        ipcMain._multiAccountRegistered = true;
        const router = getRouter();
        if (!router) return;
        ipcMain.handle('multi-account:get-state', async () => {
            const accounts = router.loadAllAccountsWithQuotasSync ? router.loadAllAccountsWithQuotasSync() : Object.values(router.loadAllAccounts());
            return { accounts, bindings: router.getBindings(), active_default: router.getActiveAccountEmail?.() };
        });
        ipcMain.handle('multi-account:bind-cascade', async (_e, c, em, m) => {
            router.setBinding(c, em, m || '');
            if ((c === '__default__' || c === 'default' || c.startsWith('draft_') || c.startsWith('chat_')) && router.setActiveAccount) router.setActiveAccount(em);
            return true;
        });
        ipcMain.handle('multi-account:set-active-account', async (_e, em) => {
            if (router.setActiveAccount) router.setActiveAccount(em);
            return true;
        });
        ipcMain.handle('multi-account:set-primary', async (_e, em) => {
            if (router.setPrimaryAccount) return router.setPrimaryAccount(em);
            return false;
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

function getInjectionScripts() {
    const router = getRouter();
    let initialData = { accounts: [], bindings: {}, active_default: null };
    try {
        if (router) {
            const accounts = router.loadAllAccountsWithQuotasSync ? router.loadAllAccountsWithQuotasSync() : Object.values(router.loadAllAccounts());
            initialData = { accounts, bindings: router.getBindings(), active_default: router.getActiveAccountEmail?.() };
        }
    } catch (_) {}

    const cssPath = path.join(__dirname, 'ui', 'styles.css');
    let cssCode = '';
    if (fs.existsSync(cssPath)) {
        try { cssCode = fs.readFileSync(cssPath, 'utf8'); } catch (_) {}
    }
    const initStateScript = `window.__AGY_INITIAL_STATE__ = ${JSON.stringify(initialData)};`;
    const bridge = `if (!window.antigravityMultiAccount) {
        window.antigravityMultiAccount = {
            getState: () => fetch('http://127.0.0.1:41999/api/multi-account/state').then(r => r.json()),
            bindCascade: (c, e, m) => fetch('http://127.0.0.1:41999/api/multi-account/bind', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cascadeId:c,email:e,model:m})}).then(r => r.json()),
            setActiveAccount: (e) => fetch('http://127.0.0.1:41999/api/multi-account/bind', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cascadeId:'__default__',email:e,active:true})}).then(r => r.json()),
            setPrimary: (e) => fetch('http://127.0.0.1:41999/api/multi-account/set-primary', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:e})}).then(r => r.json()),
            removeAccount: (e) => fetch('http://127.0.0.1:41999/api/multi-account/remove', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:e})}).then(r => r.json()),
            startLogin: () => fetch('http://127.0.0.1:41999/api/multi-account/login', {method:'POST'}).then(r => r.json())
        };
    };`;
    const scripts = [];
    if (cssCode) {
        scripts.push(`(function(){
            if (!document.getElementById('antigravity-suite-styles')) {
                const s = document.createElement('style');
                s.id = 'antigravity-suite-styles';
                s.textContent = ${JSON.stringify(cssCode)};
                (document.head || document.documentElement).appendChild(s);
            }
        })();`);
    }
    scripts.push(initStateScript);
    scripts.push(bridge);

    const rtlClientPath = path.join(__dirname, 'antigravity-rtl-client.js');
    if (fs.existsSync(rtlClientPath)) {
        try {
            const fontPath = path.join(__dirname, 'Vazirmatn-Variable.woff2');
            const fontBase64 = fs.existsSync(fontPath) ? fs.readFileSync(fontPath).toString('base64') : '';
            const rtlCode = fs.readFileSync(rtlClientPath, 'utf8')
                .replaceAll('__FONT_BASE64__', fontBase64)
                .replaceAll('__RTL_CONFIG__', '{"isRTL":true,"forceRTL":false,"fixAtSign":true,"lh":"1.6","fs":"16"}');
            scripts.push(rtlCode);
        } catch (_) {}
    }

    for (const s of ['ui/flyout.js', 'ui/mount.js', 'multi_account_ui.js']) {
        const sp = path.join(__dirname, s);
        if (fs.existsSync(sp)) {
            try { scripts.push(fs.readFileSync(sp, 'utf8')); } catch (_) {}
        }
    }
    return scripts.join('\n;\n');
}

function tryInjectTarget(target) {
    if (!target) return;
    try {
        const url = (typeof target.getURL === 'function' ? target.getURL() : target.url) || '';
        const isTarget = url.includes('127.0.0.1') || url.includes('localhost') || url.includes('workbench') || url.includes('vscode-app') || url.includes('vscode-webview') || url === '';
        if (!isTarget) return;

        const checkScript = `(function() {
            if (window.__antigravityUiActive && document.getElementById('antigravity-account-pill')) return 'active';
            const tb = document.querySelector('[data-testid="input-box-bottom-toolbar"], [data-testid="agent-input-box"], [data-testid="conversation-view"], [data-testid="model-selector-trigger"]');
            if (tb) {
                window.__antigravityUiActive = true;
                return 'inject';
            }
            return 'none';
        })()`;

        if (typeof target.executeJavaScript === 'function') {
            target.executeJavaScript(checkScript).then(status => {
                if (status === 'inject') {
                    const payload = getInjectionScripts();
                    target.executeJavaScript(payload).catch(() => {});
                }
            }).catch(() => {});
        }
    } catch (_) {}
}

function collectAllFramesFromWc(wc) {
    if (!wc || wc.isDestroyed?.()) return [];
    const frames = [];
    try {
        const root = wc.mainFrame;
        if (root) {
            if (root.framesInSubtree) {
                return root.framesInSubtree;
            }
            const queue = [root];
            while (queue.length > 0) {
                const current = queue.shift();
                frames.push(current);
                if (current.frames && Array.isArray(current.frames)) {
                    queue.push(...current.frames);
                }
            }
        }
    } catch (_) {}
    return frames;
}

function processWebContents(wc) {
    if (!wc || wc.isDestroyed?.()) return;
    tryInjectTarget(wc);
    const frames = collectAllFramesFromWc(wc);
    for (const f of frames) {
        tryInjectTarget(f);
    }
}

function scanAllTargets() {
    try {
        let list = [];
        if (webContents?.getAllWebContents) {
            list = webContents.getAllWebContents();
        } else if (BrowserWindow?.getAllWindows) {
            list = BrowserWindow.getAllWindows().map(w => w.webContents).filter(Boolean);
        }
        for (const wc of list) {
            processWebContents(wc);
        }
    } catch (_) {}
}

if (app) {
    app.on('browser-window-created', (_event, win) => {
        const wc = win.webContents;
        if (!wc) return;
        wc.on('dom-ready', () => processWebContents(wc));
        wc.on('did-finish-load', () => processWebContents(wc));
        wc.on('did-frame-finish-load', () => processWebContents(wc));
    });

    app.on('web-contents-created', (_event, wc) => {
        if (!wc) return;
        wc.on('dom-ready', () => processWebContents(wc));
        wc.on('did-finish-load', () => processWebContents(wc));
        wc.on('did-frame-finish-load', () => processWebContents(wc));
    });

    app.whenReady().then(() => {
        scanAllTargets();
        setInterval(scanAllTargets, 1200);
    });
}
