const fs = require('fs');
const path = require('path');

function patchUtilsWindow(utilsCode) {
    let code = utilsCode;
    if (!code.includes('process.env.ANTIGRAVITY_WINDOW_TITLE')) {
        code = code.replace(
            'title: electron_1.app.getName() + wslBadge,',
            'title: (process.env.ANTIGRAVITY_WINDOW_TITLE ? ("[" + process.env.ANTIGRAVITY_WINDOW_TITLE + "] ") : "") + electron_1.app.getName() + wslBadge,'
        ).replace(
            "icon: path_1.default.join(__dirname, '..', 'icon.png'),",
            'icon: process.env.ANTIGRAVITY_ICON_PATH || path_1.default.join(__dirname, "..", "icon.png"),'
        );
    }

    if (!code.includes('const prefix = process.env.ANTIGRAVITY_WINDOW_TITLE')) {
        const titleRegex = /win\.on\('page-title-updated',\s*\([^)]*\)\s*=>\s*\{[\s\S]*?win\.setTitle\([^)]*\);[\s\S]*?\}\);/;
        const titleRepl = `win.on('page-title-updated', (event, title) => {
        const maxLength = 25;
        const truncated = title.length > maxLength ? title.substring(0, maxLength) + '...' : title;
        const prefix = process.env.ANTIGRAVITY_WINDOW_TITLE ? ("[" + process.env.ANTIGRAVITY_WINDOW_TITLE + "] ") : "";
        event.preventDefault();
        win.setTitle(prefix + truncated + wslBadge);
    });`;
        if (titleRegex.test(code)) code = code.replace(titleRegex, titleRepl);
    }

    if (!code.includes("execFile('xprop'")) {
        const overlayTarget = '(0, loadingOverlay_1.attachLoadingOverlay)(win, foregroundColor, backgroundColor);';
        const overlayRepl = overlayTarget + `
    if (process.env.ANTIGRAVITY_APP_NAME || process.env.ANTIGRAVITY_DESKTOP_NAME) {
        try {
            const handle = win.getNativeWindowHandle();
            if (handle && handle.length >= 4) {
                const xid = handle.readUInt32LE(0);
                if (xid) {
                    const wmClass = (process.env.ANTIGRAVITY_APP_NAME || process.env.ANTIGRAVITY_DESKTOP_NAME).replace(/\\.desktop$/i, '');
                    require('child_process').execFile('xprop', ['-id', String(xid), '-f', 'WM_CLASS', '8s', '-set', 'WM_CLASS', wmClass]);
                }
            }
        } catch (_) {}
    }`;
        if (code.includes(overlayTarget)) code = code.replace(overlayTarget, overlayRepl);
    }
    return code;
}

module.exports = { patchUtilsWindow };
