const assert = require('assert');
const fs = require('fs');
const path = require('path');
const os = require('os');

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'agy_router_test_'));
process.env.ANTIGRAVITY_ACCOUNTS_DIR = tmpDir;
process.env.REAL_HOME = tmpDir;
process.env.ANTIGRAVITY_TEST = '1';

const { startMultiAccountRouter, setLastCascadeId } = require('../bin/lib/patch/router/server.js');
const { handleApiRequest } = require('../bin/lib/patch/router/api.js');
const { getBindings, getActiveAccountEmail } = require('../bin/lib/patch/router/bindings.js');

try {
    // Test 1: setLastCascadeId
    setLastCascadeId('test-cascade-123', 'test@example.com');

    // Test 2: handleApiRequest for set-active
    const mockReq = { url: '/api/multi-account/set-active', method: 'POST', setHeader: () => {} };
    let resHeader = 0, resBody = '';
    const mockRes = {
        setHeader: () => {},
        writeHead: (code) => { resHeader = code; },
        end: (str) => { resBody = str; }
    };
    const handled = handleApiRequest(mockReq, mockRes, JSON.stringify({ cascadeId: 'test-cascade-abc', email: 'active@example.com' }));
    assert.strictEqual(handled, true);
    assert.strictEqual(resHeader, 200);

    const bindings = getBindings();
    assert.strictEqual(bindings.__active_account, 'active@example.com');
    assert.strictEqual(getActiveAccountEmail(), 'active@example.com');

    // Test 3: handleApiRequest for set-primary
    fs.writeFileSync(path.join(tmpDir, 'active@example.com.json'), JSON.stringify({ email: 'active@example.com', token: { access_token: 'abc' } }), 'utf8');
    const mockReqPrim = { url: '/api/multi-account/set-primary', method: 'POST', setHeader: () => {} };
    let resHeaderPrim = 0;
    const mockResPrim = {
        setHeader: () => {},
        writeHead: (code) => { resHeaderPrim = code; },
        end: () => {}
    };
    const handledPrim = handleApiRequest(mockReqPrim, mockResPrim, JSON.stringify({ email: 'active@example.com' }));
    assert.strictEqual(handledPrim, true);
    assert.strictEqual(resHeaderPrim, 200);

    const savedAcc = JSON.parse(fs.readFileSync(path.join(tmpDir, 'active@example.com.json'), 'utf8'));
    assert.strictEqual(savedAcc.is_primary, true);

    console.log('✓ All router quota routing tests passed successfully');
    process.exit(0);
} finally {
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
}
