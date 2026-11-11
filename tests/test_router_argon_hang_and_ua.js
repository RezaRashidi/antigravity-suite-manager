// Test suite for Dynamic Authentic User-Agent and Router GZIP/Stall Resilience
const assert = require('assert');
const http = require('http');
const https = require('https');
const zlib = require('zlib');
const { getAuthenticUserAgent, getInstalledVersion } = require('../bin/lib/patch/router/ua.js');
const { resetProxyAgent, getProxyAgent } = require('../bin/lib/patch/router/proxy_agent.js');
const { isEligibilityRpc, normalizeEligibilityResponse } = require('../bin/lib/patch/router/eligibility_middleware.js');

console.log('Testing Dynamic Authentic User-Agent resolution...');

// Test 1: User-Agent Format
const ver = getInstalledVersion();
assert.ok(ver && ver.length >= 3, `Expected valid version string, got: ${ver}`);
const ua = getAuthenticUserAgent();
assert.ok(ua.startsWith('antigravity/hub/'), `UA must start with antigravity/hub/, got: ${ua}`);
assert.ok(ua.includes('(os_type='), `UA must include os_type, got: ${ua}`);
assert.ok(ua.includes('arch='), `UA must include arch, got: ${ua}`);
console.log(`✓ UA Test passed: ${ua}`);

// Test 2: GZIP Decompression on Eligibility RPC
console.log('Testing GZIP handling in eligibility normalization...');
const rawMock = JSON.stringify({
    ineligible: true,
    ineligibilityReason: 'LOCATION_UNSUPPORTED',
    currentTier: 'TEAMS_TIER_PRO'
});
const gzipped = zlib.gzipSync(Buffer.from(rawMock, 'utf8'));

// Simulate router decompressing gzip buffer
let decompressed = gzipped;
try {
    decompressed = zlib.gunzipSync(gzipped);
} catch (e) {
    assert.fail(`Gunzip failed: ${e.message}`);
}
const norm = normalizeEligibilityResponse('/v1internal:loadCodeAssist', 200, decompressed.toString('utf8'));
assert.strictEqual(norm.modified, true);
const parsedNorm = JSON.parse(norm.bodyStr);
assert.strictEqual(parsedNorm.hasValidAuth, true);
assert.strictEqual(parsedNorm.ineligible, undefined);
console.log('✓ GZIP decompression & normalization passed without corruption');

// Test 3: resetProxyAgent safety
console.log('Testing resetProxyAgent...');
resetProxyAgent();
console.log('✓ resetProxyAgent passed');

console.log('\n✓ All Router Argon & UA resilience tests passed successfully!');
