const assert = require('assert');
const { startMultiAccountRouter, setLastCascadeId } = require('../bin/lib/patch/router/server.js');
const { handleApiRequest } = require('../bin/lib/patch/router/api.js');
const { getBindings, getActiveAccountEmail } = require('../bin/lib/patch/router/bindings.js');

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

console.log('✓ All router quota routing tests passed successfully');
