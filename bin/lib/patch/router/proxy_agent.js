// Multi-Account Router: Pure Node.js HTTP/HTTPS Proxy Agent Helper
const http = require('http');
const https = require('https');
const tls = require('tls');
const url = require('url');
const fs = require('fs');
const path = require('path');
const os = require('os');

let _cachedAgent = null;
let _lastProxyUrl = null;

function getProxyUrl() {
    const envProxy = process.env.https_proxy || process.env.HTTPS_PROXY ||
                     process.env.all_proxy || process.env.ALL_PROXY ||
                     process.env.http_proxy || process.env.HTTP_PROXY ||
                     process.env.ide_http_proxy;
    if (envProxy && envProxy.trim()) {
        let s = envProxy.trim();
        if (!/^https?:\/\//i.test(s) && !/^socks5:\/\//i.test(s)) s = 'http://' + s;
        return s;
    }

    const home = os.homedir();
    const candSettings = [
        path.join(home, '.config', 'Antigravity IDE', 'User', 'settings.json'),
        path.join(home, '.config', 'Antigravity', 'User', 'settings.json'),
        path.join(home, '.config', 'antigravity-ide', 'User', 'settings.json'),
        path.join(home, '.config', 'Code', 'User', 'settings.json'),
    ];
    for (const p of candSettings) {
        if (fs.existsSync(p)) {
            try {
                const content = fs.readFileSync(p, 'utf8');
                const m = content.match(/"http\.proxy"\s*:\s*"([^"]+)"/);
                if (m && m[1] && m[1].trim()) {
                    let s = m[1].trim();
                    if (!/^https?:\/\//i.test(s) && !/^socks5:\/\//i.test(s)) s = 'http://' + s;
                    return s;
                }
            } catch (_) {}
        }
    }
    return null;
}

function getProxyAgent() {
    const proxyStr = getProxyUrl();
    if (!proxyStr) return undefined;
    if (_cachedAgent && _lastProxyUrl === proxyStr) return _cachedAgent;

    try {
        const proxy = new url.URL(proxyStr);
        if (proxy.protocol.startsWith('socks')) {
            // SOCKS proxy not directly handled by HTTP CONNECT, return undefined
            return undefined;
        }

        _cachedAgent = new https.Agent({
            keepAlive: true,
            createConnection: (options, callback) => {
                const targetHost = options.host || options.hostname;
                const targetPort = options.port || 443;
                const connectReq = http.request({
                    host: proxy.hostname,
                    port: proxy.port || (proxy.protocol === 'https:' ? 443 : 80),
                    method: 'CONNECT',
                    path: `${targetHost}:${targetPort}`,
                    headers: {
                        Host: `${targetHost}:${targetPort}`,
                        ...(proxy.username ? {
                            'Proxy-Authorization': 'Basic ' + Buffer.from(`${proxy.username}:${proxy.password}`).toString('base64')
                        } : {})
                    }
                });

                connectReq.on('connect', (res, socket, head) => {
                    if (res.statusCode !== 200) {
                        socket.destroy();
                        return callback(new Error(`Proxy CONNECT to ${targetHost}:${targetPort} failed with status: ${res.statusCode}`));
                    }
                    const tlsSocket = tls.connect({
                        socket,
                        servername: targetHost,
                        rejectUnauthorized: options.rejectUnauthorized !== false,
                    }, () => callback(null, tlsSocket));
                    tlsSocket.on('error', err => callback(err));
                });

                connectReq.on('error', err => callback(err));
                connectReq.setTimeout(10000, () => {
                    connectReq.destroy(new Error(`Proxy CONNECT timeout to ${targetHost}:${targetPort}`));
                });
                connectReq.end();
            }
        });
        _lastProxyUrl = proxyStr;
        return _cachedAgent;
    } catch (_) {
        return undefined;
    }
}

module.exports = { getProxyUrl, getProxyAgent };
