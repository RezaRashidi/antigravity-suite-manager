const fs = require('fs');
const path = require('path');

function patchTray(dir) {
    const trayPath = path.join(dir, 'dist', 'tray.js');
    if (!fs.existsSync(trayPath)) return;
    let trayCode = fs.readFileSync(trayPath, 'utf8');
    if (trayCode.includes('process.env.ANTIGRAVITY_TRAY_ICON_PATH')) {
        console.log('[Patch] dist/tray.js already has custom tray icon support.');
        return;
    }
    const targetTrayIcon = "const icon = electron_1.nativeImage.createFromPath(path.join(__dirname, '..', iconFile));";
    const replacementTrayIcon = `const defaultIconPath = path.join(__dirname, '..', iconFile);
    const trayIconPath = process.env.ANTIGRAVITY_TRAY_ICON_PATH || process.env.ANTIGRAVITY_ICON_PATH || defaultIconPath;
    const icon = electron_1.nativeImage.createFromPath(trayIconPath);`;

    const targetTooltip = "tray.setToolTip(electron_1.app.getName());";
    const replacementTooltip = `const trayTooltip = process.env.ANTIGRAVITY_WINDOW_TITLE ? \`\${electron_1.app.getName()} (\${process.env.ANTIGRAVITY_WINDOW_TITLE})\` : electron_1.app.getName();
    tray.setToolTip(trayTooltip);`;

    if (trayCode.includes(targetTrayIcon)) trayCode = trayCode.replace(targetTrayIcon, replacementTrayIcon);
    if (trayCode.includes(targetTooltip)) trayCode = trayCode.replace(targetTooltip, replacementTooltip);

    fs.writeFileSync(trayPath, trayCode, 'utf8');
    console.log('[Patch] dist/tray.js patched with custom tray icon and tooltip.');
}

module.exports = { patchTray };
