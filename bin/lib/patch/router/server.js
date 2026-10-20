// Multi-Account Router: Loopback HTTP Proxy Server
const http = require('http');
const https = require('https');
const { getBindings, getActiveAccountEmail, logTraffic } = require('./bindings');
const { loadAllAccounts } = require('./accounts');
const { refreshGoogleToken } = require('./oauth');

const DEFAULT_PORT = 41999;
const UPSTREAM_HOST = 'daily-cloudcode-pa.googleapis.com';
let _server = null;

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
            let cascadeId = null;
            try {
                const parsed = JSON.parse(body.toString('utf8'));
                cascadeId = parsed.cascadeId || parsed.conversationId || parsed.trajectoryId;
            } catch (_) {
                const match = body.toString('utf8').match(/"(?:cascadeId|conversationId)":\s*"([a-zA-Z0-9_\-]+)"/);
                if (match) cascadeId = match[1];
            }

            const bindings = getBindings();
            const boundEmail = (cascadeId && bindings[cascadeId]?.email) || getActiveAccountEmail(loadAllAccounts()) || 'Primary (Native)';
            const token = await resolveTokenForCascade(cascadeId);
            const tokenFp = token ? `token: ...${token.slice(-6)}` : 'token: [Native LS Session]';
            logTraffic(`Chat: [${cascadeId || 'general'}] -> Account: [${boundEmail}] | ${tokenFp} | Path: ${req.url}`);

            const headers = { ...req.headers, host: UPSTREAM_HOST };
            if (token) headers.authorization = `Bearer ${token}`;
            if (body.length > 0) headers['content-length'] = Buffer.byteLength(body);
            delete headers['transfer-encoding'];
            delete headers['connection'];

            const upReq = https.request({
                hostname: UPSTREAM_HOST, port: 443, path: req.url, method: req.method, headers, timeout: 0,
            }, (upRes) => {
                logTraffic(`Chat: [${cascadeId || 'general'}] <- Upstream Response: ${upRes.statusCode}`);
                res.writeHead(upRes.statusCode, upRes.headers);
                upRes.pipe(res);
            });

            req.on('aborted', () => upReq.destroy());
            upReq.on('error', (err) => {
                logTraffic(`Chat: [${cascadeId || 'general'}] !! Upstream Error: ${err.message}`);
                if (!res.headersSent) {
                    res.writeHead(502, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: err.message }));
                }
            });
            if (body.length > 0) upReq.write(body);
            upReq.end();
        });
    });

    _server.on('error', (err) => {
        if (err.code === 'EADDRINUSE') console.log(`[MultiAccountRouter] Port ${port} in use.`);
        else console.error('[MultiAccountRouter] Server error:', err.message);
    });
    _server.listen(port, '127.0.0.1', () => {
        logTraffic(`MultiAccountRouter started on port ${port}`);
    });
    return _server;
}

module.exports = { resolveTokenForAccount, resolveTokenForCascade, startMultiAccountRouter };
