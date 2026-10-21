// Multi-Account Router: Loopback HTTP Proxy Server
const http = require('http');
const https = require('https');
const { getBindings, getActiveAccountEmail, logTraffic } = require('./bindings.js');
const { loadAllAccounts } = require('./accounts.js');
const { refreshGoogleToken } = require('./oauth.js');
const { handleApiRequest, tryInterceptCommand } = require('./api.js');
const { getProxyAgent } = require('./proxy_agent.js');

const DEFAULT_PORT = 41999;
const UPSTREAM_HOST = 'daily-cloudcode-pa.googleapis.com';
let _server = null, _lastCascadeId = null, _lastCascadeTs = 0;

async function resolveTokenForAccount(email) {
    if (!email) return null;
    const accounts = loadAllAccounts();
    const target = accounts[email];
    if (!target || target.is_primary || !target.token) return null;
    const expiryMs = target.token.expiry ? new Date(target.token.expiry).getTime() : 0;
    if (!expiryMs || expiryMs - Date.now() < 300000) return await refreshGoogleToken(target);
    return target.token.access_token || null;
}

async function resolveTokenForCascade(cascadeId) {
    let email = cascadeId ? (getBindings()[cascadeId]?.email || null) : null;
    if (!email) email = getActiveAccountEmail(loadAllAccounts());
    return await resolveTokenForAccount(email);
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
            if (!cascadeId && _lastCascadeId && (Date.now() - _lastCascadeTs < 30000)) cascadeId = _lastCascadeId;
            if (cascadeId) { _lastCascadeId = cascadeId; _lastCascadeTs = Date.now(); }

            if (tryInterceptCommand(req, res, bodyStr, cascadeId)) return;

            const boundEmail = (cascadeId && bindings[cascadeId]?.email) || getActiveAccountEmail(loadAllAccounts()) || 'Primary (Native)';
            const token = await resolveTokenForCascade(cascadeId), tokenFp = token ? `token: ...${token.slice(-6)}` : 'token: [Native LS Session]';
            logTraffic(`Chat: [${cascadeId || 'general'}] -> Account: [${boundEmail}] | ${tokenFp} | Path: ${req.url}`);

            const headers = { ...req.headers, host: UPSTREAM_HOST };
            if (token) headers.authorization = `Bearer ${token}`;
            if (body.length > 0) headers['content-length'] = Buffer.byteLength(body);
            delete headers['transfer-encoding']; delete headers['connection'];

            const agent = getProxyAgent();
            const upOpts = {
                hostname: UPSTREAM_HOST, port: 443, path: req.url, method: req.method, headers, timeout: 0,
            };
            if (agent) upOpts.agent = agent;

            const upReq = https.request(upOpts, (upRes) => {
                logTraffic(`Chat: [${cascadeId || 'general'}] <- Upstream Response: ${upRes.statusCode}`);
                res.writeHead(upRes.statusCode, upRes.headers);
                upRes.pipe(res);
            });

            req.on('aborted', () => upReq.destroy());
            upReq.on('error', (err) => {
                logTraffic(`Chat: [${cascadeId || 'general'}] !! Upstream Error: ${err.message}`);
                if (!res.headersSent) { res.writeHead(502, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: err.message })); }
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

module.exports = { resolveTokenForAccount, resolveTokenForCascade, startMultiAccountRouter };
