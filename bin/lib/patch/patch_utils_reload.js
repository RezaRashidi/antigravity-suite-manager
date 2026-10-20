const fs = require('fs');

function patchUtilsReload(utilsCode) {
    let code = utilsCode;
    if (code.includes('onRestartRequested:')) {
        code = code.replace(/\s*onRestartRequested:\s*async\s*\(\)\s*=>\s*\{[\s\S]*?\n\s*\},(?=\s*\n\s*\}\);)/, '');
    }

    const target = '        onQuitRequested: () => {\n            exports.showQuitConfirmation = true;\n            electron_1.app.quit();\n        },';
    if (!code.includes(target)) {
        return code;
    }

    const replacement = target + `
        onRestartRequested: async () => {
            console.log('[Keybindings] Full backend & window sync requested via shortcut');
            let isGenerating = false;
            if (win && !win.isDestroyed() && win.webContents) {
                try {
                    isGenerating = await win.webContents.executeJavaScript('Boolean(document.querySelector(\\'button[aria-label*="Stop" i]\\') || document.querySelector(\\'button[aria-label*="Cancel" i]\\') || document.querySelector(\\'[data-testid="stop-button"]\\'))');
                } catch (_) {}
            }
            if ((global.__active_agent_count__ && global.__active_agent_count__ > 0) || isGenerating) {
                console.log('[Keybindings] Sync blocked: active agent running.');
                if (win && !win.isDestroyed() && win.webContents) {
                    try {
                        void win.webContents.executeJavaScript("(() => { if (document.getElementById('__antigravity_sync_toast__')) return; const t = document.createElement('div'); t.id = '__antigravity_sync_toast__'; t.innerText = 'Cannot sync: Task is currently running'; t.style.cssText = 'position:fixed;top:20px;right:20px;background:#e53e3e;color:#fff;padding:8px 16px;border-radius:8px;z-index:999999;font-family:sans-serif;font-size:13px;pointer-events:none;box-shadow:0 4px 12px rgba(0,0,0,0.3);'; document.body.appendChild(t); setTimeout(() => t.remove(), 3000); })()");
                    } catch (_) {}
                }
                return;
            }
            if (win && !win.isDestroyed() && win.webContents) {
                try {
                    void win.webContents.executeJavaScript("(() => { if (document.getElementById('__antigravity_sync_toast__')) return; const t = document.createElement('div'); t.id = '__antigravity_sync_toast__'; t.innerText = 'Syncing chats with IDE...'; t.style.cssText = 'position:fixed;top:20px;right:20px;background:rgba(0,0,0,0.85);color:#fff;padding:8px 16px;border-radius:8px;z-index:999999;font-family:sans-serif;font-size:13px;pointer-events:none;box-shadow:0 4px 12px rgba(0,0,0,0.3);'; document.body.appendChild(t); })()");
                } catch (_) {}
            }
            let newPort = null;
            try {
                const ls = require('./languageServer');
                if (ls && typeof ls.restartLanguageServer === 'function') {
                    await ls.restartLanguageServer();
                    newPort = typeof ls.getLsPort === 'function' ? ls.getLsPort() : null;
                }
            } catch (err) {
                console.error('[Keybindings] LanguageServer restart failed:', err);
            }
            if (win && !win.isDestroyed() && win.webContents) {
                try {
                    const curUrl = win.webContents.getURL();
                    if (newPort && curUrl && curUrl.includes('127.0.0.1')) {
                        const parsed = new URL(curUrl);
                        parsed.port = String(newPort);
                        await win.loadURL(parsed.toString());
                    } else {
                        win.webContents.reload();
                    }
                } catch (_) {}
            }
        },`;

    return code.replace(target, replacement);
}

module.exports = { patchUtilsReload };
