const zlib = require('zlib');
const assert = require('assert');
const fs = require('fs');
const http = require('http');
const os = require('os');
const path = require('path');

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'agy_health_failover_'));
process.env.ANTIGRAVITY_ACCOUNTS_DIR = tmpDir;
process.env.REAL_HOME = tmpDir;
process.env.ANTIGRAVITY_TEST = '1';

const futureIso = new Date(Date.now() + 3600 * 1000).toISOString();
fs.writeFileSync(path.join(tmpDir, 'bad-verify@gmail.com.json'), JSON.stringify({
    email: 'bad-verify@gmail.com',
    is_primary: true,
    license_status: 'ok',
    token: { access_token: 'tok-bad-verify', refresh_token: 'rt-bad-1', expiry: futureIso },
}, null, 2));
fs.writeFileSync(path.join(tmpDir, 'bad-license@gmail.com.json'), JSON.stringify({
    email: 'bad-license@gmail.com',
    is_primary: false,
    license_status: 'no_license',
    token: { access_token: 'tok-bad-lic', refresh_token: 'rt-lic-1', expiry: futureIso },
}, null, 2));
fs.writeFileSync(path.join(tmpDir, 'good-one@gmail.com.json'), JSON.stringify({
    email: 'good-one@gmail.com',
    is_primary: false,
    license_status: 'ok',
    tier_type: 'Paid Pro',
    token: { access_token: 'tok-good-one', refresh_token: 'rt-good-1', expiry: futureIso },
}, null, 2));
fs.writeFileSync(path.join(tmpDir, 'good-two@gmail.com.json'), JSON.stringify({
    email: 'good-two@gmail.com',
    is_primary: false,
    license_status: 'ok',
    tier_type: 'Free Pro',
    token: { access_token: 'tok-good-two', refresh_token: 'rt-good-2', expiry: futureIso },
}, null, 2));

const oldBindId = 'b19b5666-cbaf-4361-8186-05d6edbe956f';
const activeBindId = '54524f02-7520-418c-bad6-89ce8fe1e150';
fs.writeFileSync(path.join(tmpDir, 'bindings.json'), JSON.stringify({
    [oldBindId]: { cascade_id: oldBindId, email: 'bad-verify@gmail.com', updated_at: '2026-10-24T06:53:46.414Z' },
    [activeBindId]: { cascade_id: activeBindId, email: 'good-one@gmail.com', updated_at: '2026-11-12T13:33:02.599Z' },
    '__default__': { cascade_id: '__default__', email: 'bad-verify@gmail.com', updated_at: '2026-11-12T13:33:10.789Z' },
    '__active_account': 'bad-verify@gmail.com',
}, null, 2));

const {
    loadAllAccounts,
    markAccountUnhealthy,
    clearAccountUnhealthy,
    isAccountHealthy,
    pickHealthyFallbackAccount,
} = require('../bin/lib/patch/router/accounts.js');
const { getActiveAccountEmail } = require('../bin/lib/patch/router/bindings.js');
const { allocateAccountForSubagent, releaseSubagentLease } = require('../bin/lib/patch/router/subagent_allocator.js');
const { handleApiRequest } = require('../bin/lib/patch/router/api.js');
const { extractCascadeId, startMultiAccountRouter } = require('../bin/lib/patch/router/server.js');

async function postJson(port, urlPath, bodyObj) {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify(bodyObj);
        const req = http.request({
            hostname: '127.0.0.1',
            port,
            path: urlPath,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(data),
            },
        }, (res) => {
            let out = '';
            res.on('data', c => out += c);
            res.on('end', () => resolve({ status: res.statusCode, body: out }));
        });
        req.on('error', reject);
        req.write(data);
        req.end();
    });
}

async function runTests() {
    const bindings = JSON.parse(fs.readFileSync(path.join(tmpDir, 'bindings.json'), 'utf8'));

    // 1. Artifact Directory Path must beat an older bound UUID in user prompt text
    const promptWithOldUuid = JSON.stringify({
        requestId: 'f3313330-dab6-48c1-8c40-ad8c223bb929',
        request: {
            systemInstruction: {
                parts: [{ text: `Artifact Directory Path: /home/reza/.gemini/antigravity/brain/${activeBindId}` }],
            },
            contents: [{ role: 'user', parts: [{ text: `Please check chat ${oldBindId} why it failed` }] }],
        },
    });
    const ex1 = extractCascadeId(promptWithOldUuid, bindings, null);
    assert.strictEqual(ex1.cascadeId, activeBindId);
    assert.strictEqual(ex1.source, 'artifact_dir');

    // 2. Multiple bound UUIDs without Artifact Dir pick newest updated_at / lastCascadeId, not insertion order
    const multiUuidBody = JSON.stringify({
        request: { contents: [{ parts: [{ text: `Compare ${oldBindId} and ${activeBindId}` }] }] },
    });
    const ex2 = extractCascadeId(multiUuidBody, bindings, null);
    assert.strictEqual(ex2.cascadeId, activeBindId);

    // 3. Background monitor payload with only random requestId must NOT invent cascadeId
    const monitorBody = JSON.stringify({
        requestId: '0c3c95bd-4728-4913-895f-cf5b97c7c04f',
        request: { contents: [{ role: 'user', parts: [{ text: 'Evaluate tool safety' }] }] },
    });
    const ex3 = extractCascadeId(monitorBody, bindings, activeBindId);
    assert.strictEqual(ex3.cascadeId, null);
    assert.strictEqual(ex3.source, 'none');

    // 4. End-to-end HTTP 403 Verify Account auto-failover + quarantine
    const seenAuthHeaders = [];
    const mockUpstream = http.createServer((req, res) => {
        const auth = req.headers.authorization || '';
        seenAuthHeaders.push({ url: req.url, auth });
        if (auth === 'Bearer tok-bad-verify') {
            res.writeHead(403, { 'Content-Type': 'application/json' });
            return res.end(JSON.stringify({
                error: { code: 403, message: 'Verify your account to continue.', status: 'PERMISSION_DENIED' },
            }));
        }
        if (auth === 'Bearer tok-bad-lic') {
            res.writeHead(403, { 'Content-Type': 'application/json' });
            return res.end(JSON.stringify({
                error: { code: 403, message: 'You do not have a valid license of this product.', status: 'PERMISSION_DENIED' },
            }));
        }
        res.writeHead(200, { 'Content-Type': 'text/event-stream' });
        res.end('data: {"candidates":[{"content":{"parts":[{"text":"ok"}]},"finishReason":"STOP"}]}\n\ndata: [DONE]\n\n');
    });

    await new Promise(r => mockUpstream.listen(0, '127.0.0.1', r));
    const upPort = mockUpstream.address().port;

    const routerSrv = startMultiAccountRouter(0, {
        allowNewInstance: true,
        host: '127.0.0.1',
        upstreamProtocol: 'http:',
        upstreamHost: '127.0.0.1',
        upstreamPort: upPort,
    });
    await new Promise(r => routerSrv.once('listening', r));
    const routerPort = routerSrv.address().port;

    try {
        // Request hitting a chat bound to bad-verify@gmail.com:
        // Upstream returns 403 once, router quarantines bad-verify@gmail.com and seamlessly fails over to good-one@gmail.com -> 200!
        const res1 = await postJson(routerPort, '/v1internal:streamGenerateContent?alt=sse', {
            cascadeId: oldBindId,
            request: { contents: [{ parts: [{ text: 'hello' }] }] },
        });
        assert.strictEqual(res1.status, 200, 'Client must receive 200 after transparent 403 failover');
        assert.ok(res1.body.includes('"text":"ok"'));
        assert.strictEqual(seenAuthHeaders[0].auth, 'Bearer tok-bad-verify');
        assert.strictEqual(seenAuthHeaders[1].auth, 'Bearer tok-good-one');

        // Confirm bad-verify@gmail.com is now quarantined on disk and in memory
        const accsAfter = loadAllAccounts();
        assert.strictEqual(isAccountHealthy(accsAfter['bad-verify@gmail.com'], accsAfter), false);
        assert.strictEqual(accsAfter['bad-verify@gmail.com'].license_status, 'verify_required');

        // Active default and subagent allocator must NEVER select bad-verify or bad-license
        const activeFallback = getActiveAccountEmail(accsAfter);
        assert.ok(activeFallback === 'good-one@gmail.com' || activeFallback === 'good-two@gmail.com');

        const subAlloc = allocateAccountForSubagent('sub-test-1', activeBindId, accsAfter, bindings);
        assert.strictEqual(subAlloc, 'good-two@gmail.com', 'Subagent must pick healthy non-parent account');
        releaseSubagentLease('sub-test-1');

        // Subsequent request to bad-verify@gmail.com skips it proactively without even hitting upstream with tok-bad-verify
        const beforeCount = seenAuthHeaders.length;
        const res2 = await postJson(routerPort, '/v1internal:streamGenerateContent?alt=sse', {
            cascadeId: oldBindId,
            request: { contents: [{ parts: [{ text: 'second turn' }] }] },
        });
        assert.strictEqual(res2.status, 200);
        assert.strictEqual(seenAuthHeaders.length, beforeCount + 1, 'Proactive skip should hit upstream only once with healthy token');
        assert.strictEqual(seenAuthHeaders[beforeCount].auth, 'Bearer tok-good-one');

        // set-active via API for an unhealthy account must NOT clobber active fallback and returns skipped=true
        let setActResBody = '';
        const mockRes = { setHeader: () => {}, writeHead: () => {}, end: (s) => { setActResBody = s || ''; } };
        handleApiRequest(
            { url: '/api/multi-account/set-active', method: 'POST' },
            mockRes,
            JSON.stringify({ email: 'bad-verify@gmail.com' })
        );
        assert.notStrictEqual(getActiveAccountEmail(loadAllAccounts()), 'bad-verify@gmail.com');
        assert.strictEqual(JSON.parse(setActResBody).skipped, true);

        // /bind to unhealthy account must also skip and return unhealthy=true
        let bindBadBody = '';
        handleApiRequest(
            { url: '/api/multi-account/bind', method: 'POST' },
            { setHeader: () => {}, writeHead: () => {}, end: (s) => { bindBadBody = s || ''; } },
            JSON.stringify({ cascadeId: activeBindId, email: 'bad-verify@gmail.com' })
        );
        assert.strictEqual(JSON.parse(bindBadBody).unhealthy, true);

        // /api/multi-account/state must preserve explicit healthy active_default (array vs map regression)
        require('../bin/lib/patch/router/telemetry.js')._quotaCache.timestamp = Date.now();
        handleApiRequest(
            { url: '/api/multi-account/set-active', method: 'POST' },
            { setHeader: () => {}, writeHead: () => {}, end: () => {} },
            JSON.stringify({ email: 'good-two@gmail.com' })
        );
        let stateBody = '';
        handleApiRequest(
            { url: '/api/multi-account/state', method: 'GET' },
            { setHeader: () => {}, writeHead: () => {}, end: (s) => { stateBody = s || ''; } },
            ''
        );
        assert.strictEqual(JSON.parse(stateBody).active_default, 'good-two@gmail.com');

        // Clearing health restores eligibility
        clearAccountUnhealthy('bad-verify@gmail.com');
        assert.strictEqual(isAccountHealthy(loadAllAccounts()['bad-verify@gmail.com']), true);

        // Cooldown expiry auto-clears persisted quarantine on both memory and disk
        markAccountUnhealthy('bad-verify@gmail.com', 'verify_required', 'Verify', 25);
        await new Promise(r => setTimeout(r, 45));
        const accsExpired = loadAllAccounts();
        assert.strictEqual(isAccountHealthy(accsExpired['bad-verify@gmail.com'], accsExpired), true);
        const onDiskAfterExpiry = JSON.parse(fs.readFileSync(path.join(tmpDir, 'bad-verify@gmail.com.json'), 'utf8'));
        assert.strictEqual(onDiskAfterExpiry.license_status, 'ok');

        // Fallback helper prefers verified Paid Pro accounts
        markAccountUnhealthy('bad-verify@gmail.com', 'verify_required', 'Verify');
        assert.strictEqual(pickHealthyFallbackAccount(loadAllAccounts(), ['good-one@gmail.com']), 'good-two@gmail.com');

        // Generic HTTP 403 (e.g. gzipped proxy/transient 403) must fail over WITHOUT poisoning disk JSON permanently
        const { classifyHttpError } = require('../bin/lib/patch/router/accounts.js');
        const clsGeneric403 = classifyHttpError(403, '<html>Cloudflare 403</html>');
        assert.strictEqual(clsGeneric403.reason, 'forbidden_transient');
        assert.strictEqual(clsGeneric403.persist, false);

        // HTTP 401 failover + gzipped 403 failover end-to-end
        const gzipMock = http.createServer((req, res) => {
            if (req.headers.authorization === 'Bearer tok-good-two') {
                const gz = zlib.gzipSync(Buffer.from(JSON.stringify({ error: { code: 403, message: 'Verify your account to continue.' } })));
                res.writeHead(403, { 'Content-Type': 'application/json', 'Content-Encoding': 'gzip' });
                return res.end(gz);
            }
            if (req.headers.authorization === 'Bearer tok-good-one') {
                res.writeHead(200, { 'Content-Type': 'text/event-stream' });
                return res.end('data: {"candidates":[{"content":{"parts":[{"text":"gzip-failover-ok"}]},"finishReason":"STOP"}]}\n\ndata: [DONE]\n\n');
            }
            res.writeHead(401, { 'Content-Type': 'application/json' });
            return res.end(JSON.stringify({ error: { code: 401, status: 'UNAUTHENTICATED' } }));
        });
        await new Promise(r => gzipMock.listen(0, '127.0.0.1', r));
        const gzPort = gzipMock.address().port;
        const gzRouter = startMultiAccountRouter(0, {
            allowNewInstance: true,
            host: '127.0.0.1',
            upstreamProtocol: 'http:',
            upstreamHost: '127.0.0.1',
            upstreamPort: gzPort,
        });
        await new Promise(r => gzRouter.once('listening', r));
        try {
            const gzRes = await postJson(gzRouter.address().port, '/v1internal:streamGenerateContent?alt=sse', {
                cascadeId: 'gz-test-chat',
                request: { contents: [{ parts: [{ text: 'hi' }] }] },
            });
            assert.strictEqual(gzRes.status, 200);
            assert.ok(gzRes.body.includes('gzip-failover-ok'));
            assert.strictEqual(loadAllAccounts()['good-two@gmail.com'].license_status, 'verify_required');
        } finally {
            gzRouter.close();
            gzipMock.close();
        }

        console.log('✓ All router health, quarantine, cascade extraction, and 403 auto-failover tests passed');
    } finally {
        routerSrv.close();
        mockUpstream.close();
        try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    }
}

runTests().then(() => {
    process.exit(0);
}).catch(err => {
    console.error(err);
    process.exit(1);
});
