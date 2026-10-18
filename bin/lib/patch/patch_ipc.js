const fs = require('fs');
const path = require('path');

function patchIpcHandlers(dir) {
    const ipcPath = path.join(dir, 'dist', 'ipcHandlers.js');
    if (!fs.existsSync(ipcPath)) return;
    let ipcCode = fs.readFileSync(ipcPath, 'utf8');
    if (ipcCode.includes('global.__active_agent_count__ =')) {
        console.log('[Patch] dist/ipcHandlers.js already tracks active agent count.');
        return;
    }
    ipcCode = ipcCode.replace(
        "electron_1.ipcMain.handle('agent:update-active-count', async (_event, count) => {",
        "global.__active_agent_count__ = 0;\n    electron_1.ipcMain.handle('agent:update-active-count', async (_event, count) => {\n        global.__active_agent_count__ = typeof count === 'number' ? count : 0;"
    );
    fs.writeFileSync(ipcPath, ipcCode, 'utf8');
    console.log('[Patch] dist/ipcHandlers.js patched.');
}

module.exports = { patchIpcHandlers };
