// Multi-Account Router: Loopback HTTP Proxy Server
const http = require('http');
const https = require('https');
const zlib = require('zlib');
const { getBindings, setBinding, getActiveAccountEmail, logTraffic } = require('./bindings.js');
const {
    loadAllAccounts,
    classifyHttpError,
    markAccountUnhealthy,
    clearAccountUnhealthy,
    isAccountHealthy,
    pickHealthyFallbackAccount,
} = require('./accounts.js');
const { refreshGoogleToken } = require('./oauth.js');
const { handleApiRequest, tryInterceptCommand } = require('./api.js');
const { getProxyAgent, resetProxyAgent } = require('./proxy_agent.js');
const { getAuthenticUserAgent } = require('./ua.js');
const { getSubagentPolicy, isSubagent, trackInFlight, allocateAccountForSubagent } = require('./subagent_allocator.js');
const { isEligibilityRpc, normalizeEligibilityResponse } = require('./eligibility_middleware.js');

const DEFAULT_PORT = 41999;
const UPSTREAM_HOST = 'daily-cloudcode-pa.googleapis.com';
const MAX_FAILOVER_ATTEMPTS = 6;
let _server = null, _lastCascadeId = null, _lastCascadeTs = 0;

function decodeUpstreamBuffer(rawBuf, contentEncoding = '') {
    const enc = String(contentEncoding || '').toLowerCase();
    if (enc === 'gzip') {
        try { return zlib.gunzipSync(rawBuf); } catch (_) { return rawBuf; }
    }
    if (enc === 'deflate') {
        try { return zlib.inflateSync(rawBuf); } catch (_) { return rawBuf; }
    }
    return rawBuf;
}

function extractSystemInstructionText(parsed, bodyStr) {
    try {
        const si = parsed?.request?.systemInstruction || parsed?.systemInstruction;
        if (typeof si === 'string') return si;
        if (Array.isArray(si?.parts)) {
            return si.parts.map(p => (typeof p?.text === 'string' ? p.text : '')).join('\n');
        }
        if (si && typeof si === 'object') return JSON.stringify(si);
    } catch (_) {}
    return bodyStr ? bodyStr.slice(0, 32768) : '';
}

function extractCascadeId(bodyStr, bindings = {}, lastCascadeId = null) {
    if (!bodyStr || typeof bodyStr !== 'string') return { cascadeId: null, source: 'none' };
    let parsed = null;
    try {
        parsed = JSON.parse(bodyStr);
        const direct = parsed.cascadeId || parsed.conversationId || parsed.cascade_id || parsed.conversation_id;
        if (direct && typeof direct === 'string') return { cascadeId: direct, source: 'explicit' };
    } catch (_) {
        const match = bodyStr.match(/"(?:cascadeId|conversationId|cascade_id|conversation_id)":\s*"([a-zA-Z0-9_\-]+)"/);
        if (match) return { cascadeId: match[1], source: 'explicit' };
    }

    const sysText = extractSystemInstructionText(parsed, bodyStr);
    const artMatch = sysText.match(/Artifact Directory Path:\s*[^\n"]*?[\\/]brain[\\/]([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i);
    if (artMatch && artMatch[1]) {
        return { cascadeId: artMatch[1], source: 'artifact_dir' };
    }

    const traj = parsed?.trajectoryId || parsed?.trajectory_id || (() => {
        const tm = bodyStr.match(/"(?:trajectoryId|trajectory_id)":\s*"([a-zA-Z0-9_\-]+)"/);
        return tm ? tm[1] : null;
    })();
    if (traj && bindings && bindings[traj]) {
        return { cascadeId: traj, source: 'binding' };
    }

    if (bindings && typeof bindings === 'object') {
        const matched = [];
        for (const bid of Object.keys(bindings)) {
            if (!bid.startsWith('__') && bid !== 'default' && bid.length >= 8 && bodyStr.includes(bid)) {
                matched.push(bid);
            }
        }
        if (matched.length === 1) {
            return { cascadeId: matched[0], source: 'binding' };
        }
        if (matched.length > 1) {
            matched.sort((a, b) => {
                const aLast = (lastCascadeId && a === lastCascadeId) ? 1 : 0;
                const bLast = (lastCascadeId && b === lastCascadeId) ? 1 : 0;
                if (aLast !== bLast) return bLast - aLast;
                const aSys = (sysText && sysText.includes(a)) ? 1 : 0;
                const bSys = (sysText && sysText.includes(b)) ? 1 : 0;
                if (aSys !== bSys) return bSys - aSys;
                const aTs = Date.parse(bindings[a]?.updated_at || '') || 0;
                const bTs = Date.parse(bindings[b]?.updated_at || '') || 0;
                if (aTs !== bTs) return bTs - aTs;
                return b.length - a.length;
            });
            return { cascadeId: matched[0], source: 'binding' };
        }
    }

    return { cascadeId: null, source: 'none' };
}

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

function startMultiAccountRouter(port = DEFAULT_PORT, options = {}) {
    if (_server && !options.allowNewInstance) return _server;
    const upstreamHost = options.upstreamHost || UPSTREAM_HOST;
    const upstreamPort = options.upstreamPort || 443;
    const upstreamClient = options.upstreamProtocol === 'http:' ? http : https;
    const useProxyAgent = options.upstreamProtocol !== 'http:';

    const srv = http.createServer((req, res) => {
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

            const bindings = getBindings();
            const freshLastId = (_lastCascadeId && (Date.now() - _lastCascadeTs < 3600000)) ? _lastCascadeId : null;
            const extracted = extractCascadeId(bodyStr, bindings, freshLastId);
            let cascadeId = extracted.cascadeId;
            if (cascadeId && extracted.source !== 'none') {
                _lastCascadeId = cascadeId;
                _lastCascadeTs = Date.now();
            }

            if (tryInterceptCommand(req, res, bodyStr, cascadeId)) return;

            const isGen = req.url && (req.url.includes('streamGenerateContent') || req.url.includes('generateContent'));
            const isAccountRpc = req.url && (
                isGen ||
                req.url.includes('retrieveUserQuota') ||
                req.url.includes('fetchAvailableModels')
            );
            const isEligRpc = isEligibilityRpc(req.url);

            if (!cascadeId && !isGen && freshLastId) {
                cascadeId = freshLastId;
            }

            // loadCodeAssist stays native: hijacking it breaks login onboarding (401).
            let token = null, boundEmail = 'Primary (Native)', isSub = false;
            let accountsSnapshot = {};
            const triedEmails = new Set();

            if (isAccountRpc) {
                accountsSnapshot = loadAllAccounts();
                const activeDefault = getActiveAccountEmail(accountsSnapshot);
                const subPolicy = getSubagentPolicy();
                const subInfo = subPolicy.enabled && cascadeId ? isSubagent(cascadeId) : { isSubagent: false };
                isSub = !!subInfo.isSubagent;

                if (isSub) {
                    const allocated = allocateAccountForSubagent(cascadeId, subInfo.parentId, accountsSnapshot, bindings);
                    boundEmail = allocated || activeDefault || 'Primary (Native)';
                } else {
                    boundEmail = (cascadeId && bindings[cascadeId]?.email) || activeDefault || 'Primary (Native)';
                }

                // Proactive health check: avoid routing onto a known unverified/403 account
                const targetAcc = boundEmail === 'Primary (Native)'
                    ? Object.values(accountsSnapshot).find(a => a && a.is_primary)
                    : accountsSnapshot[boundEmail.toLowerCase()];

                if (targetAcc && !isAccountHealthy(targetAcc, accountsSnapshot)) {
                    const reason = targetAcc.license_status || 'unhealthy';
                    const exclude = [boundEmail, targetAcc.email];
                    const healthyFallback = pickHealthyFallbackAccount(accountsSnapshot, exclude, activeDefault);
                    if (healthyFallback) {
                        logTraffic(`[HEALTH_SKIP] Account [${boundEmail}] is ${reason}; routing [${cascadeId || 'general'}] to [${healthyFallback}]`);
                        triedEmails.add(boundEmail.toLowerCase());
                        if (targetAcc.email) triedEmails.add(targetAcc.email.toLowerCase());
                        boundEmail = healthyFallback;
                    }
                }

                token = await resolveTokenForAccount(boundEmail);
                if (!token && boundEmail !== 'Primary (Native)') {
                    markAccountUnhealthy(boundEmail, 'auth_failed', 'Token resolution failed', 10 * 60 * 1000, accountsSnapshot[boundEmail.toLowerCase()]);
                    triedEmails.add(boundEmail.toLowerCase());
                    const nextAcc = pickHealthyFallbackAccount(accountsSnapshot, Array.from(triedEmails));
                    if (nextAcc) {
                        logTraffic(`[HEALTH_SKIP] Missing token for [${boundEmail}]; failing over [${cascadeId || 'general'}] to [${nextAcc}]`);
                        boundEmail = nextAcc;
                        token = await resolveTokenForAccount(boundEmail);
                    }
                }
            } else {
                logTraffic(`ControlPlane: [${cascadeId || 'system'}] -> Native LS Session | Path: ${req.url}`);
            }

            let reqAborted = false;
            let activeUpReq = null;
            let activeCleanup = () => {};

            req.on('aborted', () => { reqAborted = true; activeCleanup(); if (activeUpReq) activeUpReq.destroy(); });
            req.on('error', () => { reqAborted = true; activeCleanup(); if (activeUpReq) activeUpReq.destroy(); });
            res.on('error', () => { reqAborted = true; activeCleanup(); if (activeUpReq) activeUpReq.destroy(); });
            res.on('close', () => {
                if (!res.writableEnded) {
                    reqAborted = true;
                    if (activeUpReq) activeUpReq.destroy();
                }
                activeCleanup();
            });
            res.on('finish', () => { activeCleanup(); });

            const maxAttempts = isAccountRpc && !isEligRpc ? MAX_FAILOVER_ATTEMPTS : 1;

            const sendAttempt = (currentEmail, currentToken, attemptNum) => {
                if (reqAborted || res.headersSent) return;

                if (isAccountRpc) {
                    const tokenFp = currentToken ? `token: ...${currentToken.slice(-6)}` : 'token: [Native LS Session]';
                    logTraffic(`${isGen ? (isSub ? 'SubagentGen' : 'ChatGen') : 'AccountRpc'}: [${cascadeId || 'general'}] -> Account: [${currentEmail}] | ${tokenFp} | Path: ${req.url}`);
                }

                const headers = { ...req.headers, host: upstreamHost };
                if (!headers['user-agent'] || headers['user-agent'].includes('Antigravity/2.')) {
                    headers['user-agent'] = getAuthenticUserAgent();
                }
                if (isAccountRpc && currentToken) headers.authorization = `Bearer ${currentToken}`;
                if (body.length > 0) headers['content-length'] = Buffer.byteLength(body);
                delete headers['transfer-encoding'];
                delete headers['connection'];
                if (isEligRpc) {
                    delete headers['accept-encoding'];
                }

                const agent = useProxyAgent ? getProxyAgent() : undefined;
                const upOpts = {
                    hostname: upstreamHost,
                    port: upstreamPort,
                    path: req.url,
                    method: req.method,
                    headers,
                    timeout: 0,
                };
                if (agent) upOpts.agent = agent;

                let inFlightTracked = isGen && currentEmail && currentEmail !== 'Primary (Native)';
                if (inFlightTracked) trackInFlight(currentEmail, 1);
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
                        trackInFlight(currentEmail, -1);
                    }
                };
                activeCleanup = finishInFlight;

                const ttfbTimeoutMs = isGen ? 120000 : 25000;
                ttfbTimer = setTimeout(() => {
                    if (settled) return;
                    logTraffic(`Chat: [${cascadeId || 'general'}] !! Upstream TTFB Timeout (${ttfbTimeoutMs / 1000}s) on ${req.url}`);
                    resetProxyAgent();
                    upReq.destroy(new Error(`Upstream TTFB timeout (${ttfbTimeoutMs / 1000}s)`));
                }, ttfbTimeoutMs);

                const upReq = upstreamClient.request(upOpts, (upRes) => {
                    if (ttfbTimer) { clearTimeout(ttfbTimer); ttfbTimer = null; }

                    logTraffic(`${isAccountRpc ? (isGen ? (isSub ? 'SubagentGen' : 'ChatGen') : 'AccountRpc') : 'ControlPlane'}: [${cascadeId || 'general'}] <- Upstream Response: ${upRes.statusCode}`);

                    if (isEligRpc) {
                        const resChunks = [];
                        upRes.on('data', c => resChunks.push(c));
                        upRes.on('error', (err) => {
                            settled = true;
                            finishInFlight();
                            logTraffic(`EligibilityRpc: [${cascadeId || 'general'}] !! Response Stream Error: ${err.message}`);
                            if (!res.headersSent) {
                                res.writeHead(502, { 'Content-Type': 'application/json' });
                                res.end(JSON.stringify({ error: err.message }));
                            } else {
                                res.destroy(err);
                            }
                        });
                        upRes.on('end', () => {
                            settled = true;
                            finishInFlight();
                            const rawBuf = decodeUpstreamBuffer(Buffer.concat(resChunks), upRes.headers['content-encoding']);
                            const rawBody = rawBuf.toString('utf8');
                            if (upRes.statusCode === 200 && req.url?.includes('retrieveUserQuotaSummary') && currentEmail !== 'Primary (Native)') {
                                try {
                                    const parsedQuota = JSON.parse(rawBody);
                                    if (Array.isArray(parsedQuota.groups) && parsedQuota.groups.length > 0) {
                                        clearAccountUnhealthy(currentEmail);
                                    }
                                } catch (_) {}
                            } else if (upRes.statusCode === 403 && /verify your account|SUBSCRIPTION_REQUIRED|valid license/i.test(rawBody) && currentEmail !== 'Primary (Native)') {
                                const cls = classifyHttpError(403, rawBody);
                                markAccountUnhealthy(currentEmail, cls.reason, cls.message, undefined, accountsSnapshot[currentEmail.toLowerCase()], { persist: cls.persist });
                            }
                            const norm = normalizeEligibilityResponse(req.url, upRes.statusCode, rawBody);
                            if (norm.modified) {
                                logTraffic(`[ELIGIBILITY] Normalized location/auth handshake for ${req.url} (${upRes.statusCode} -> ${norm.statusCode})`);
                                if (currentEmail && currentEmail !== 'Primary (Native)') {
                                    const { markAccountBypassed } = require('./accounts.js');
                                    markAccountBypassed(currentEmail, true);
                                }
                            }
                            const resHeaders = { ...upRes.headers };
                            const outBuf = Buffer.from(norm.bodyStr, 'utf8');
                            resHeaders['content-length'] = outBuf.length;
                            delete resHeaders['content-encoding'];
                            delete resHeaders['transfer-encoding'];
                            delete resHeaders['connection'];
                            delete resHeaders['keep-alive'];
                            if (!res.headersSent) {
                                res.writeHead(norm.statusCode, resHeaders);
                                res.end(outBuf);
                            }
                        });
                        upRes.on('close', () => { settled = true; finishInFlight(); });
                        return;
                    }

                    // Intercept account-level 403/401 before piping headers to client and seamlessly fail over
                    if (isAccountRpc && (upRes.statusCode === 403 || upRes.statusCode === 401)) {
                        const errChunks = [];
                        let errBytes = 0;
                        let errTruncated = false;
                        upRes.on('data', (c) => {
                            if (errBytes < 524288) {
                                errChunks.push(c);
                                errBytes += c.length;
                            } else {
                                errTruncated = true;
                            }
                        });
                        upRes.on('error', (err) => {
                            settled = true;
                            finishInFlight();
                            logTraffic(`AccountRpc: [${cascadeId || 'general'}] !! Error Response Stream Failure: ${err.message}`);
                            if (!res.headersSent && !reqAborted) {
                                res.writeHead(502, { 'Content-Type': 'application/json' });
                                res.end(JSON.stringify({ error: err.message }));
                            }
                        });
                        upRes.on('end', async () => {
                            settled = true;
                            finishInFlight();
                            const rawErrBuf = Buffer.concat(errChunks);
                            const decodedErrBuf = decodeUpstreamBuffer(rawErrBuf, upRes.headers['content-encoding']);
                            const errText = decodedErrBuf.toString('utf8');
                            const cls = classifyHttpError(upRes.statusCode, errText);

                            triedEmails.add(String(currentEmail).toLowerCase());
                            const freshAccounts = loadAllAccounts();
                            if (currentEmail === 'Primary (Native)') {
                                const prim = Object.values(freshAccounts).find(a => a && a.is_primary);
                                if (prim?.email) {
                                    triedEmails.add(prim.email.toLowerCase());
                                    markAccountUnhealthy(prim.email, cls.reason, cls.message, undefined, prim, { persist: cls.persist });
                                }
                            } else {
                                markAccountUnhealthy(currentEmail, cls.reason, cls.message, undefined, freshAccounts[currentEmail.toLowerCase()], { persist: cls.persist });
                            }

                            if (!reqAborted && !res.headersSent && attemptNum < maxAttempts) {
                                let nextEmail = pickHealthyFallbackAccount(freshAccounts, Array.from(triedEmails));
                                while (nextEmail && !reqAborted) {
                                    triedEmails.add(nextEmail.toLowerCase());
                                    const nextToken = await resolveTokenForAccount(nextEmail);
                                    if (reqAborted) return;
                                    if (nextToken) {
                                        logTraffic(`[FAILOVER] [${cascadeId || 'general'}] Account [${currentEmail}] returned HTTP ${upRes.statusCode} (${cls.reason}); retrying with [${nextEmail}]`);
                                        sendAttempt(nextEmail, nextToken, attemptNum + 1);
                                        return;
                                    }
                                    markAccountUnhealthy(nextEmail, 'auth_failed', 'Token resolution failed', 10 * 60 * 1000, freshAccounts[nextEmail.toLowerCase()]);
                                    nextEmail = pickHealthyFallbackAccount(freshAccounts, Array.from(triedEmails));
                                }
                            }

                            if (!reqAborted && !res.headersSent) {
                                const resHeaders = { ...upRes.headers };
                                let outErrBuf = rawErrBuf;
                                if (errTruncated && resHeaders['content-encoding']) {
                                    delete resHeaders['content-encoding'];
                                    resHeaders['content-type'] = 'application/json; charset=utf-8';
                                    outErrBuf = Buffer.from(JSON.stringify({ error: { code: upRes.statusCode, message: cls.message } }), 'utf8');
                                }
                                resHeaders['content-length'] = Buffer.byteLength(outErrBuf);
                                delete resHeaders['transfer-encoding'];
                                delete resHeaders['connection'];
                                delete resHeaders['keep-alive'];
                                res.writeHead(upRes.statusCode, resHeaders);
                                res.end(outErrBuf);
                            }
                        });
                        upRes.on('close', () => { settled = true; finishInFlight(); });
                        return;
                    }

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
                    if (!res.headersSent) {
                        res.writeHead(upRes.statusCode, resHeaders);
                    }
                    upRes.on('error', (err) => {
                        settled = true;
                        finishInFlight();
                        logTraffic(`Chat: [${cascadeId || 'general'}] !! Upstream Stream Error: ${err.message}`);
                        resetProxyAgent();
                        if (!res.headersSent) {
                            res.writeHead(502, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({ error: err.message }));
                        } else if (!res.destroyed) {
                            res.destroy(err);
                        }
                    });
                    upRes.pipe(res);
                    upRes.on('end', () => { settled = true; finishInFlight(); });
                    upRes.on('close', () => { settled = true; finishInFlight(); });
                });
                activeUpReq = upReq;

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
            };

            sendAttempt(boundEmail, token, 1);
        });
    });

    srv.on('error', (err) => { if (err.code !== 'EADDRINUSE') console.error('[MultiAccountRouter] Error:', err.message); });
    const host = options.host || process.env.ANTIGRAVITY_ROUTER_HOST || '0.0.0.0';
    srv.listen(port, host, () => logTraffic(`MultiAccountRouter started on ${host}:${port}`));
    if (!options.allowNewInstance) _server = srv;
    return srv;
}

module.exports = {
    resolveTokenForAccount,
    resolveTokenForCascade,
    setLastCascadeId,
    extractCascadeId,
    startMultiAccountRouter,
    getAuthenticUserAgent,
    resetProxyAgent
};
