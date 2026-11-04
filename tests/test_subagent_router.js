// Test: Subagent Dynamic Account Allocator and Router Integration
const assert = require('assert');
const {
    isSubagent,
    allocateAccountForSubagent,
    trackInFlight,
    getInFlightCount,
    releaseSubagentLease,
    getSubagentPolicy,
    setSubagentPolicy
} = require('../bin/lib/patch/router/subagent_allocator.js');

function runTests() {
    console.log('Running Subagent Dynamic Account Allocator Tests...');

    // 1. Policy test
    const initialPolicy = getSubagentPolicy();
    assert.strictEqual(typeof initialPolicy.enabled, 'boolean');
    setSubagentPolicy({ enabled: true, proactive_mode: true });
    assert.strictEqual(getSubagentPolicy().enabled, true);
    assert.strictEqual(getSubagentPolicy().proactive_mode, true);
    console.log('✓ Policy test passed');

    // 2. Mock account allocation with parent exclusion
    const accounts = {
        'parent@test.com': { email: 'parent@test.com' },
        'sub1@test.com': { email: 'sub1@test.com' },
        'sub2@test.com': { email: 'sub2@test.com' },
        'sub3@test.com': { email: 'sub3@test.com' }
    };
    const bindings = {
        'parent-conv-id': { email: 'parent@test.com' }
    };

    // Subagent 1: should pick an idle account that is NOT parent@test.com
    const alloc1 = allocateAccountForSubagent('sub-uuid-1', 'parent-conv-id', accounts, bindings);
    assert.notStrictEqual(alloc1, 'parent@test.com');
    assert.ok(['sub1@test.com', 'sub2@test.com', 'sub3@test.com'].includes(alloc1));
    trackInFlight(alloc1, 1);
    assert.strictEqual(getInFlightCount(alloc1), 1);
    console.log('✓ Subagent 1 allocated idle non-parent account:', alloc1);

    // Subagent 2: should pick a DIFFERENT idle account
    const alloc2 = allocateAccountForSubagent('sub-uuid-2', 'parent-conv-id', accounts, bindings);
    assert.notStrictEqual(alloc2, 'parent@test.com');
    assert.notStrictEqual(alloc2, alloc1);
    trackInFlight(alloc2, 1);
    assert.strictEqual(getInFlightCount(alloc2), 1);
    console.log('✓ Subagent 2 allocated distinct idle account:', alloc2);

    // Subagent 3: should pick the remaining idle account
    const alloc3 = allocateAccountForSubagent('sub-uuid-3', 'parent-conv-id', accounts, bindings);
    assert.notStrictEqual(alloc3, 'parent@test.com');
    assert.notStrictEqual(alloc3, alloc1);
    assert.notStrictEqual(alloc3, alloc2);
    trackInFlight(alloc3, 1);
    assert.strictEqual(getInFlightCount(alloc3), 1);
    console.log('✓ Subagent 3 allocated distinct idle account:', alloc3);

    // Parent account must still be 0 in-flight
    assert.strictEqual(getInFlightCount('parent@test.com'), 0);
    console.log('✓ Parent account preserved with 0 in-flight streams');

    // Clean up in-flight
    trackInFlight(alloc1, -1);
    trackInFlight(alloc2, -1);
    trackInFlight(alloc3, -1);
    assert.strictEqual(getInFlightCount(alloc1), 0);
    assert.strictEqual(getInFlightCount(alloc2), 0);
    assert.strictEqual(getInFlightCount(alloc3), 0);
    releaseSubagentLease('sub-uuid-1');
    releaseSubagentLease('sub-uuid-2');
    releaseSubagentLease('sub-uuid-3');
    console.log('✓ In-flight and lease release passed');

    console.log('All Subagent Allocator tests passed successfully!');
    process.exit(0);
}

runTests();
