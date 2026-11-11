// Multi-Account Router: Loopback HTTP Proxy Server
const http = require('http');
const https = require('https');
const zlib = require('zlib');
const { getBindings, setBinding, getActiveAccountEmail, logTraffic } = require('./bindings.js');
const { loadAllAccounts } = require('./accounts.js');
const { refreshGoogleToken } = require('./oauth.js');
const { handleApiRequest, tryInterceptCommand } = require('./api.js');
const { getProxyAgent, resetProxyAgent } = require('./proxy_agent.js');
const { getAuthenticUserAgent } = require('./ua.js');
const { getSubagentPolicy, isSubagent, trackInFlight, allocateAccountForSubagent } = require('./subagent_allocator.js');
const { isEligibilityRpc, normalizeEligibilityResponse } = require('./eligibility_middleware.js');

const DEFAULT_PORT = 41999;
const UPSTREAM_HOST = 'daily-cloudcode-pa.googleapis.com';
let _server = null, _lastCascadeId = null, _lastCascadeTs = 0;

async function resolveTokenForAccount(email) {
    if (!email) return null;
    const accounts = loadAllAccounts();
    let target = null;
    if (email === 'Primary (Native)') {
        target = Object.values(accounts).find(a => a.is_primary);
    } else {
        target = accounts[email.toLowerCase()];
    }
    if (!target || !target.token) return null;
    const expiryMs = target.token.expiry ? new Date(target.token.expiry).getTime() : 0;
    if (!expiryMs || expiryMs - Date.now() < 300000) return await refreshGoogleToken(target);
    return target.token.access_token || null;
}

async function resolveTokenForCascade(cascadeId) {
    let email = cascadeId ? (getBindings()[cascadeId]?.email || null) : null;
    if (!email) email = getActiveAccountEmail(loadAllAccounts());
    return await resolveTokenForAccount(email);
}

function setLastCascadeId(cascadeId, email) {
    if (cascadeId) {
        _lastCascadeId = cascadeId;
        _lastCascadeTs = Date.now();
    }
}

function startMultiAccountRouter(port = DEFAULT_PORT) {
    if (_server) return _server;
    _server = http.createServer((req, res) => {
        if (req.url === '/healthz') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            return res.end(JSON.stringify({ status: 'ok', proxy: 'antigravity-multi-account-node' }));
        }
        const chunks = [];
        req.on('data', chunk => chunks.push(chunk));
        req.on('end', async () => {
            const body = Buffer.concat(chunks);
            const bodyStr = body.toString('utf8');
            if (handleApiRequest(req, res, bodyStr)) return;

            let cascadeId = null;
            try {
                const parsed = JSON.parse(bodyStr);
                cascadeId = parsed.cascadeId || parsed.conversationId || parsed.trajectoryId || parsed.cascade_id || parsed.conversation_id || parsed.trajectory_id;
            } catch (_) {
                const match = bodyStr.match(/"(?:cascadeId|conversationId|trajectoryId|cascade_id|conversation_id|trajectory_id)":\s*"([a-zA-Z0-9_\-]+)"/);
                if (match) cascadeId = match[1];
            }
            const bindings = getBindings();
            if (!cascadeId) { for (const bid of Object.keys(bindings)) if (!bid.startsWith('__') && bid !== 'default' && bid.length >= 8 && bodyStr.includes(bid)) { cascadeId = bid; break; } }
            if (!cascadeId) { const m = bodyStr.match(/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i); if (m) cascadeId = m[1]; }
            if (!cascadeId && _lastCascadeId && (Date.now() - _lastCascadeTs < 3600000)) cascadeId = _lastCascadeId;
            if (cascadeId) { _lastCascadeId = cascadeId; _lastCascadeTs = Date.now(); }

            if (tryInterceptCommand(req, res, bodyStr, cascadeId)) return;

            const isGen = req.url && (req.url.includes('streamGenerateContent') || req.url.includes('generateContent'));
            const isAccountRpc = req.url && (
                isGen ||
                req.url.includes('retrieveUserQuota') ||
                req.url.includes('fetchAvailableModels')
            );
            // loadCodeAssist stays native: hijacking it breaks login onboarding (401).
            let token = null, boundEmail = 'Primary (Native)', isSub = false;
            if (isAccountRpc) {
                const accounts = loadAllAccounts();
                const activeDefault = getActiveAccountEmail(accounts);
                const subPolicy = getSubagentPolicy();
                const subInfo = subPolicy.enabled && cascadeId ? isSubagent(cascadeId) : { isSubagent: false };
                isSub = !!subInfo.isSubagent;

                if (isSub) {
                    const allocated = allocateAccountForSubagent(cascadeId, subInfo.parentId, accounts, bindings);
                    boundEmail = allocated || activeDefault || 'Primary (Native)';
                } else {
                    boundEmail = (cascadeId && bindings[cascadeId]?.email) || activeDefault || 'Primary (Native)';
                }
                token = await resolveTokenForAccount(boundEmail);
                const tokenFp = token ? `token: ...${token.slice(-6)}` : 'token: [Native LS Session]';
                logTraffic(`${isGen ? (isSub ? 'SubagentGen' : 'ChatGen') : 'AccountRpc'}: [${cascadeId || 'general'}] -> Account: [${boundEmail}] | ${tokenFp} | Path: ${req.url}`);
            } else {
                logTraffic(`ControlPlane: [${cascadeId || 'system'}] -> Native LS Session | Path: ${req.url}`);
            }

            const headers = { ...req.headers, host: UPSTREAM_HOST };
            if (!headers['user-agent'] || headers['user-agent'].includes('Antigravity/2.')) {
                headers['user-agent'] = getAuthenticUserAgent();
            }
            if (isAccountRpc && token) headers.authorization = `Bearer ${token}`;
            if (body.length > 0) headers['content-length'] = Buffer.byteLength(body);
            delete headers['transfer-encoding'];
            delete headers['connection'];

            const isEligRpc = isEligibilityRpc(req.url);
            if (isEligRpc) {
                // Prevent upstream compression on intercepted handshakes to avoid gzip corruption
                delete headers['accept-encoding'];
            }

            const agent = getProxyAgent();
            const upOpts = {
                hostname: UPSTREAM_HOST, port: 443, path: req.url, method: req.method, headers, timeout: 0,
            };
            if (agent) upOpts.agent = agent;

            let inFlightTracked = isGen && boundEmail && boundEmail !== 'Primary (Native)';
            if (inFlightTracked) trackInFlight(boundEmail, 1);
            let settled = false;
            let streamTimer = null;
            let ttfbTimer = null;

            const clearTimers = () => {
                if (ttfbTimer) { clearTimeout(ttfbTimer); ttfbTimer = null; }
                if (streamTimer) { clearTimeout(streamTimer); streamTimer = null; }
            };

            const finishInFlight = () => {
                clearTimers();
                if (inFlightTracked) {
                    inFlightTracked = false;
                    trackInFlight(boundEmail, -1);
                }
            };

            // TTFB timeout: 120s for generation (reasoning models like Argon), 25s for non-generation RPCs
            const ttfbTimeoutMs = isGen ? 120000 : 25000;
            ttfbTimer = setTimeout(() => {
                if (settled) return;
                logTraffic(`Chat: [${cascadeId || 'general'}] !! Upstream TTFB Timeout (${ttfbTimeoutMs / 1000}s) on ${req.url}`);
                resetProxyAgent();
                upReq.destroy(new Error(`Upstream TTFB timeout (${ttfbTimeoutMs / 1000}s)`));
            }, ttfbTimeoutMs);

            const upReq = https.request(upOpts, (upRes) => {
                // Headers received: clear TTFB timer
                if (ttfbTimer) { clearTimeout(ttfbTimer); ttfbTimer = null; }

                logTraffic(`${isAccountRpc ? (isGen ? (isSub ? 'SubagentGen' : 'ChatGen') : 'AccountRpc') : 'ControlPlane'}: [${cascadeId || 'general'}] <- Upstream Response: ${upRes.statusCode}`);
                
                if (isEligRpc) {
                    const chunks = [];
                    upRes.on('data', c => chunks.push(c));
                    upRes.on('end', () => {
                        settled = true;
                        finishInFlight();
                        let rawBuf = Buffer.concat(chunks);
                        const enc = (upRes.headers['content-encoding'] || '').toLowerCase();
                        if (enc === 'gzip') {
                            try {
                                rawBuf = zlib.gunzipSync(rawBuf);
                            } catch (e) {
                                logTraffic(`[ELIGIBILITY] Gunzip failed for ${req.url}: ${e.message}`);
                            }
                        } else if (enc === 'deflate') {
                            try {
                                rawBuf = zlib.inflateSync(rawBuf);
                            } catch (_) {}
                        }
                        const rawBody = rawBuf.toString('utf8');
                        const norm = normalizeEligibilityResponse(req.url, upRes.statusCode, rawBody);
                        if (norm.modified) {
                            logTraffic(`[ELIGIBILITY] Normalized location/auth handshake for ${req.url} (${upRes.statusCode} -> ${norm.statusCode})`);
                            if (boundEmail && boundEmail !== 'Primary (Native)') {
                                const { markAccountBypassed } = require('./accounts.js');
                                markAccountBypassed(boundEmail, true);
                            }
                        }
                        const resHeaders = { ...upRes.headers };
                        const outBuf = Buffer.from(norm.bodyStr, 'utf8');
                        resHeaders['content-length'] = outBuf.length;
                        delete resHeaders['content-encoding'];
                        delete resHeaders['transfer-encoding'];
                        delete resHeaders['connection'];
                        delete resHeaders['keep-alive'];
                        res.writeHead(norm.statusCode, resHeaders);
                        res.end(outBuf);
                    });
                    upRes.on('close', () => { settled = true; finishInFlight(); });
                    return;
                }

                // Streaming chunk idle monitor for generation
                if (isGen) {
                    const resetStreamIdle = () => {
                        if (streamTimer) clearTimeout(streamTimer);
                        streamTimer = setTimeout(() => {
                            logTraffic(`Chat: [${cascadeId || 'general'}] !! Stream Idle Timeout (60s) on ${req.url}`);
                            resetProxyAgent();
                            upReq.destroy(new Error('Stream idle timeout (60s)'));
                        }, 60000);
                    };
                    resetStreamIdle();
                    upRes.on('data', resetStreamIdle);
                }

                const resHeaders = { ...upRes.headers };
                if (resHeaders['content-length']) {
                    delete resHeaders['transfer-encoding'];
                }
                delete resHeaders['connection'];
                delete resHeaders['keep-alive'];
                res.writeHead(upRes.statusCode, resHeaders);
                upRes.pipe(res);
                upRes.on('end', () => { settled = true; finishInFlight(); });
                upRes.on('close', () => { settled = true; finishInFlight(); });
            });

            req.on('aborted', () => { settled = true; finishInFlight(); upReq.destroy(); });
            req.on('error', () => { settled = true; finishInFlight(); upReq.destroy(); });
            res.on('error', () => { settled = true; finishInFlight(); upReq.destroy(); });
            res.on('close', () => { settled = true; finishInFlight(); });
            res.on('finish', () => { settled = true; finishInFlight(); });

            upReq.on('error', (err) => {
                settled = true;
                finishInFlight();
                logTraffic(`Chat: [${cascadeId || 'general'}] !! Upstream Error: ${err.message}`);
                const msg = err.message || '';
                if (msg.includes('hang up') || msg.includes('ECONNRESET') || msg.includes('ETIMEDOUT') || msg.includes('timeout')) {
                    resetProxyAgent();
                }
                if (!res.headersSent) {
                    const status = msg.includes('timeout') ? 504 : 502;
                    res.writeHead(status, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: err.message }));
                }
            });

            if (body.length > 0) upReq.write(body);
            upReq.end();
        });
    });

    _server.on('error', (err) => { if (err.code !== 'EADDRINUSE') console.error('[MultiAccountRouter] Error:', err.message); });
    const host = process.env.ANTIGRAVITY_ROUTER_HOST || '0.0.0.0';
    _server.listen(port, host, () => logTraffic(`MultiAccountRouter started on ${host}:${port}`));
    return _server;
}

module.exports = {
    resolveTokenForAccount,
    resolveTokenForCascade,
    setLastCascadeId,
    startMultiAccountRouter,
    getAuthenticUserAgent,
    resetProxyAgent
};
