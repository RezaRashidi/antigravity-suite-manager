"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerCustomModelHandlers = registerCustomModelHandlers;
/** Addon-owned channels only; vendor desktop APIs are left intact. */
const electron_1 = require("electron");
const path = __importStar(require("node:path"));
const cryptoStore = __importStar(require("./cryptoStore"));
const modelManagement_1 = require("./modelManagement");
const proxyAgent_1 = require("./proxy/proxyAgent");
async function openExternalOrAuthWindow(url) {
    if (!url.includes('accounts.google.com')) {
        await electron_1.shell.openExternal(url);
        return;
    }
    try {
        const proxy = await (0, proxyAgent_1.detectLocalProxy)();
        const authWin = new electron_1.BrowserWindow({
            width: 520,
            height: 680,
            title: 'Google Sign In',
            autoHideMenuBar: true,
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
            },
        });
        if (proxy) {
            await authWin.webContents.session.setProxy({ proxyRules: proxy });
        }
        authWin.webContents.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36');
        authWin.webContents.on('will-redirect', (_event, redirectUrl) => {
            if (redirectUrl.includes('/oauth2callback')) {
                setTimeout(() => {
                    if (!authWin.isDestroyed())
                        authWin.close();
                }, 1200);
            }
        });
        await authWin.loadURL(url);
    }
    catch {
        await electron_1.shell.openExternal(url);
    }
}
async function syncLanguageServerAndWindows(getLanguageServerPort) {
    let ls;
    try {
        ls = require('../languageServer');
    } catch (_) {
        try { ls = require('./languageServer'); } catch (_) {}
    }
    let port = (typeof getLanguageServerPort === 'function' ? getLanguageServerPort() : null) || (typeof ls?.getLsPort === 'function' ? ls.getLsPort() : null);
    let csrf = null;
    try {
        const fs = require('fs');
        for (const pid of fs.readdirSync('/proc')) {
            if (!/^\d+$/.test(pid)) continue;
            try {
                const cmd = fs.readFileSync('/proc/' + pid + '/cmdline', 'utf8');
                if (cmd.includes('language_server') && cmd.includes('--csrf_token')) {
                    const mCsrf = cmd.match(/--csrf_token[\0=\s]+([0-9a-fA-F-]+)/);
                    if (mCsrf) {
                        csrf = mCsrf[1];
                        if (!port) {
                            const mPort = cmd.match(/--https_server_port[\0=\s]+(\d+)/);
                            if (mPort && Number(mPort[1]) > 0) port = Number(mPort[1]);
                        }
                        break;
                    }
                }
            } catch (_) {}
        }
    } catch (_) {}

    let userStatus = null;
    if (port && csrf) {
        const https = require('https');
        const rpcCall = (method, payload) => new Promise((resolve) => {
            const data = JSON.stringify(payload);
            const req = https.request({
                hostname: '127.0.0.1',
                port,
                path: `/exa.language_server_pb.LanguageServerService/${method}`,
                method: 'POST',
                rejectUnauthorized: false,
                headers: {
                    'Content-Type': 'application/json',
                    'x-codeium-csrf-token': csrf,
                    'Content-Length': Buffer.byteLength(data),
                },
                timeout: 4000,
            }, (res) => {
                let buf = '';
                res.on('data', (c) => { buf += c; });
                res.on('end', () => {
                    try { resolve(JSON.parse(buf)); } catch (_) { resolve(null); }
                });
            });
            req.on('error', () => resolve(null));
            req.on('timeout', () => { req.destroy(); resolve(null); });
            req.write(data);
            req.end();
        });

        try {
            await rpcCall('GetAvailableModels', { forceRefresh: true });
            const statusRes = await rpcCall('GetUserStatus', {});
            if (statusRes?.userStatus) {
                userStatus = statusRes.userStatus;
            }
        } catch (_) {}
    }

    const serializedPayload = JSON.stringify(userStatus);
    const injectionScript = `
    (() => {
        try {
            if (typeof customModelsCache !== 'undefined') {
                customModelsCache.ts = 0;
            }
            const payload = ${serializedPayload};
            if (payload) {
                const root = document.getElementById('root') || document.body.firstElementChild;
                if (root) {
                    const fiberKey = Object.keys(root).find(k => k.startsWith('__reactFiber$') || k.startsWith('__reactContainer$') || k.startsWith('__reactInternalInstance$'));
                    if (fiberKey) {
                        const queue = [root[fiberKey]];
                        while (queue.length > 0) {
                            const node = queue.shift();
                            if (!node) continue;
                            const store = node.memoizedProps?.store || node.stateNode?.store;
                            if (store && typeof store.dispatch === 'function') {
                                store.dispatch({ type: 'userStatus/setUserStatus', payload: payload });
                                break;
                            }
                            if (node.child) queue.push(node.child);
                            if (node.sibling) queue.push(node.sibling);
                        }
                    }
                }
            }
        } catch (_) {}
        window.dispatchEvent(new CustomEvent('agy-models-changed'));
    })();
    `;

    const windows = electron_1.BrowserWindow.getAllWindows();
    for (const win of windows) {
        if (!win.isDestroyed() && win.webContents) {
            try {
                win.webContents.send('storage:models-changed');
                await win.webContents.executeJavaScript(injectionScript);
            } catch (_) {}
        }
    }
    return { success: true, dynamic: true, modelsUpdated: !!userStatus };
}

function registerCustomModelHandlers(getLanguageServerPort) {
    const manager = (0, modelManagement_1.createModelManager)(path.join(electron_1.app.getPath('home'), '.gemini', 'antigravity'), cryptoStore, openExternalOrAuthWindow);
    const handle = (channel, action) => {
        electron_1.ipcMain.handle(channel, async (_event, ...args) => {
            try {
                return await action(...args);
            }
            catch (error) {
                if (channel === 'storage:get-custom-models' || channel === 'storage:export-custom-models')
                    throw error;
                const status = error.status;
                return { success: false, error: error.message, ...(status ? { status } : {}) };
            }
        });
    };
    handle('storage:get-custom-models', () => manager.store.list());
    handle('storage:save-custom-model', async (model) => {
        const res = await manager.saveModel(model);
        await syncLanguageServerAndWindows(getLanguageServerPort);
        return res;
    });
    handle('storage:delete-custom-model', async (name) => {
        manager.store.delete(name);
        await syncLanguageServerAndWindows(getLanguageServerPort);
        return { success: true };
    });
    handle('storage:test-model-connection', (model) => manager.testModel(model));
    handle('storage:get-provider-presets', manager.presets);
    handle('storage:discover-models', manager.discoverModels);
    handle('storage:discover-local', manager.discoverLocal);
    handle('storage:export-custom-models', () => manager.store.export());
    handle('storage:import-custom-models', (payload) => ({ success: true, count: manager.store.import(payload) }));
    handle('storage:get-gateway', manager.getGateway);
    handle('storage:save-gateway', manager.saveGateway);
    handle('storage:test-gateway', manager.testGateway);
    handle('storage:import-gateway-models', manager.importGatewayModels);
    handle('storage:open-gateway-dashboard', manager.openDashboard);
    handle('storage:google-login', manager.googleLogin);
    handle('storage:google-login-cancel', manager.googleLoginCancel);
    handle('storage:google-test-account', manager.googleTestAccount);
    handle('storage:google-pool-status', manager.googlePoolStatus);
    handle('storage:get-proxy-status', async () => ({ proxy: await (0, proxyAgent_1.detectLocalProxy)() }));
    handle('storage:sync-models', () => syncLanguageServerAndWindows(getLanguageServerPort));
}
//# sourceMappingURL=customIpc.js.map