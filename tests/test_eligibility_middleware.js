const assert = require('assert');
const { isEligibilityRpc, normalizeEligibilityResponse } = require('../bin/lib/patch/router/eligibility_middleware.js');

// Test 1: URL detection
assert.strictEqual(isEligibilityRpc('/v1internal:loadCodeAssist'), true);
assert.strictEqual(isEligibilityRpc('/v1internal:fetchUserInfo'), true);
assert.strictEqual(isEligibilityRpc('/v1internal:retrieveUserQuotaSummary'), true);
assert.strictEqual(isEligibilityRpc('/v1internal:streamGenerateContent'), false);
assert.strictEqual(isEligibilityRpc(null), false);

// Test 2: loadCodeAssist with ineligibility
const rawBlocked = JSON.stringify({
    ineligible: true,
    ineligibilityReason: 'LOCATION_RESTRICTED',
    hasValidAuth: false
});
const res1 = normalizeEligibilityResponse('/v1internal:loadCodeAssist', 403, rawBlocked);
assert.strictEqual(res1.modified, true);
assert.strictEqual(res1.statusCode, 200);
const parsed1 = JSON.parse(res1.bodyStr);
assert.strictEqual(parsed1.hasValidAuth, true);
assert.strictEqual(parsed1.has_valid_auth, true);
assert.strictEqual(parsed1.isGcpTos, true);
assert.strictEqual(parsed1.currentTier, 'TEAMS_TIER_PRO');
assert.strictEqual(parsed1.ineligible, undefined);
assert.strictEqual(parsed1.ineligibilityReason, undefined);

// Test 3: fetchUserInfo with isEligible: false
const rawUser = JSON.stringify({ email: 'user@example.com', isEligible: false });
const res2 = normalizeEligibilityResponse('/v1internal:fetchUserInfo', 200, rawUser);
assert.strictEqual(res2.modified, true);
assert.strictEqual(JSON.parse(res2.bodyStr).isEligible, true);

// Test 4: retrieveUserQuotaSummary with HTTP 403
const rawQuotaError = JSON.stringify({ error: { code: 403, message: 'Forbidden' } });
const res3 = normalizeEligibilityResponse('/v1internal:retrieveUserQuotaSummary', 403, rawQuotaError);
assert.strictEqual(res3.modified, true);
assert.strictEqual(res3.statusCode, 200);
const parsed3 = JSON.parse(res3.bodyStr);
assert.strictEqual(parsed3.userStatus.isEligible, true);

// Test 5: untouched when already ok
const normalPayload = JSON.stringify({ status: 'ok', currentTier: 'FREE' });
const res4 = normalizeEligibilityResponse('/v1internal:loadCodeAssist', 200, normalPayload);
assert.strictEqual(res4.modified, false);
assert.strictEqual(res4.bodyStr, normalPayload);

// Test 6: UI Flyout displays bypass notice in quota details when is_bypassed is true
const vm = require('vm');
const fs = require('fs');
const path = require('path');
const flyoutCode = fs.readFileSync(path.join(__dirname, '../bin/lib/patch/ui/flyout.js'), 'utf8');
const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(flyoutCode, sandbox);

const bypassedHtml = sandbox.window.__antigravityBuildFlyout({
    email: 'goldab.dev@gmail.com',
    tier: 'Paid Pro',
    is_bypassed: true,
    quotas: [{ family: 'gemini', window: '5h', percent: 99, label: 'Five Hour' }]
});
assert.ok(bypassedHtml.includes('Region Bypass'), 'Flyout should contain bypass indicator');
assert.ok(bypassedHtml.includes('agy-bypass-badge'), 'Flyout should contain agy-bypass-badge class');

const normalHtml = sandbox.window.__antigravityBuildFlyout({
    email: 'normal@gmail.com',
    tier: 'PRO',
    is_bypassed: false,
    quotas: [{ family: 'gemini', window: '5h', percent: 90, label: 'Five Hour' }]
});
assert.ok(!normalHtml.includes('Region Bypass'), 'Flyout should not contain bypass indicator for normal account');

console.log('✓ All eligibility middleware and flyout integration tests passed successfully');
