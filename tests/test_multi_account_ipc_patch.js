// Test: Multi-Account IPC Patcher & Login Dispatcher
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const os = require('os');

const { patchIpcAndPreload, unpatchIpcAndPreload } = require('../bin/lib/patch/patch_multi_account_ipc.js');
const { handleApiRequest } = require('../bin/lib/patch/router/api.js');

function runTests() {
    console.log('Running Multi-Account IPC & Login Tests...');

    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'agy_ipc_patch_test_'));

    try {
        // Test 1: Patching modern App v2.32+ signature: function registerIpcHandlers(storageManager, deps = {})
        const modernIpcContent = `
const electron_1 = require("electron");
function registerIpcHandlers(storageManager, deps = {}) {
    electron_1.ipcMain.handle('existing:ping', () => 'pong');
}
exports.registerIpcHandlers = registerIpcHandlers;
`;
        const modernPreloadContent = `
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld('existingBridge', {});
`;
        fs.writeFileSync(path.join(tmpDir, 'ipcHandlers.js'), modernIpcContent, 'utf8');
        fs.writeFileSync(path.join(tmpDir, 'preload.js'), modernPreloadContent, 'utf8');

        patchIpcAndPreload(tmpDir);

        let patchedIpc = fs.readFileSync(path.join(tmpDir, 'ipcHandlers.js'), 'utf8');
        assert.ok(patchedIpc.includes("electron_1.ipcMain.handle('multi-account:start-login'"), "Should inject multi-account:start-login");
        assert.ok(patchedIpc.includes("electron_1.ipcMain.handle('multi-account:get-state'"), "Should inject multi-account:get-state");
        assert.ok(patchedIpc.includes("DISPLAY: process.env.DISPLAY || ':0'"), "Should guarantee DISPLAY env in spawn");
        assert.ok(patchedIpc.includes("/* AGY_MULTI_ACCOUNT_IPC_START */"), "Should wrap with start marker");
        assert.ok(patchedIpc.includes("/* AGY_MULTI_ACCOUNT_IPC_END */"), "Should wrap with end marker");

        let patchedPreload = fs.readFileSync(path.join(tmpDir, 'preload.js'), 'utf8');
        assert.ok(patchedPreload.includes("antigravityMultiAccount"), "Should inject antigravityMultiAccount into preload");

        // Idempotency check: patching again should not duplicate
        patchIpcAndPreload(tmpDir);
        let doublePatchedIpc = fs.readFileSync(path.join(tmpDir, 'ipcHandlers.js'), 'utf8');
        const countStartLogin = (doublePatchedIpc.match(/multi-account:start-login/g) || []).length;
        assert.strictEqual(countStartLogin, 1, "Patcher should be idempotent");

        // Test Unpatch
        unpatchIpcAndPreload(tmpDir);
        let unpatchedIpc = fs.readFileSync(path.join(tmpDir, 'ipcHandlers.js'), 'utf8');
        assert.ok(!unpatchedIpc.includes("multi-account:start-login"), "Unpatch should remove start-login");
        assert.ok(!unpatchedIpc.includes("/* AGY_MULTI_ACCOUNT_IPC_START */"), "Unpatch should remove markers");
        assert.ok(unpatchedIpc.includes("electron_1.ipcMain.handle('existing:ping'"), "Unpatch should preserve original code");

        let unpatchedPreload = fs.readFileSync(path.join(tmpDir, 'preload.js'), 'utf8');
        assert.ok(!unpatchedPreload.includes("antigravityMultiAccount"), "Unpatch should remove context bridge");
        console.log('✓ Modern App v2.32+ IPC patch & unpatch passed');

        // Test 2: Patching legacy signature: function registerIpcHandlers(storageManager)
        const legacyIpcContent = `
function registerIpcHandlers(storageManager) {
    electron_1.ipcMain.handle('legacy:call', () => true);
}
`;
        fs.writeFileSync(path.join(tmpDir, 'ipcHandlers.js'), legacyIpcContent, 'utf8');
        patchIpcAndPreload(tmpDir);
        patchedIpc = fs.readFileSync(path.join(tmpDir, 'ipcHandlers.js'), 'utf8');
        assert.ok(patchedIpc.includes("electron_1.ipcMain.handle('multi-account:start-login'"), "Should inject into legacy signature");
        console.log('✓ Legacy signature IPC patch passed');

        // Test 3: HTTP API /api/multi-account/login endpoint
        let statusCode = 0;
        let responseBody = '';
        const mockReq = {
            url: '/api/multi-account/login',
            method: 'POST',
            setHeader: () => {}
        };
        const mockRes = {
            setHeader: () => {},
            writeHead: (code) => { statusCode = code; },
            end: (data) => { responseBody = data; }
        };

        const handled = handleApiRequest(mockReq, mockRes, '');
        assert.strictEqual(handled, true, "handleApiRequest should handle /api/multi-account/login");
        assert.strictEqual(statusCode, 200, "Should return HTTP 200");
        const parsed = JSON.parse(responseBody);
        assert.strictEqual(parsed.ok, true, "Response payload should have { ok: true }");
        console.log('✓ HTTP API /api/multi-account/login test passed');

        console.log('All Multi-Account IPC & Login tests passed successfully!');
        process.exit(0);
    } finally {
        try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    }
}

runTests();
