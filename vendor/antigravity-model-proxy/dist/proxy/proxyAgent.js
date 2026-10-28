"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.checkPort = checkPort;
exports.detectLocalProxy = detectLocalProxy;
exports.createTunnelAgent = createTunnelAgent;
exports.getProxyAgent = getProxyAgent;
exports.getRelayUrl = getRelayUrl;
exports.resetProxyCache = resetProxyCache;
const http = __importStar(require("node:http"));
const https = __importStar(require("node:https"));
const tls = __importStar(require("node:tls"));
const net = __importStar(require("node:net"));
let cachedProxyUrl = undefined;
let cachedAgent = undefined;
function checkPort(port, host = '127.0.0.1', timeout = 250) {
    return new Promise((resolve) => {
        const socket = new net.Socket();
        let settled = false;
        const finish = (open) => {
            if (settled)
                return;
            settled = true;
            socket.destroy();
            resolve(open);
        };
        socket.setTimeout(timeout);
        socket.on('connect', () => finish(true));
        socket.on('timeout', () => finish(false));
        socket.on('error', () => finish(false));
        socket.connect(port, host);
    });
}
async function detectLocalProxy() {
    if (cachedProxyUrl !== undefined) {
        return cachedProxyUrl || undefined;
    }
    const envProxy = process.env.HTTPS_PROXY || process.env.HTTP_PROXY || process.env.ALL_PROXY;
    if (envProxy) {
        cachedProxyUrl = envProxy;
        return envProxy;
    }
    // Common local proxy ports (Clash, v2ray, NekoBox)
    const commonPorts = [7890, 10809, 2081, 10808];
    for (const port of commonPorts) {
        if (await checkPort(port)) {
            const url = `http://127.0.0.1:${port}`;
            cachedProxyUrl = url;
            return url;
        }
    }
    cachedProxyUrl = null;
    return undefined;
}
function createTunnelAgent(proxyUrl) {
    const parsed = new URL(proxyUrl);
    const agent = new https.Agent();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    agent.createConnection = (options, callback) => {
        const req = http.request({
            host: parsed.hostname,
            port: Number(parsed.port) || 80,
            method: 'CONNECT',
            path: `${options.host}:${options.port || 443}`,
            headers: {
                Host: `${options.host}:${options.port || 443}`,
                ...(parsed.username
                    ? {
                        'Proxy-Authorization': `Basic ${Buffer.from(`${decodeURIComponent(parsed.username)}:${decodeURIComponent(parsed.password)}`).toString('base64')}`,
                    }
                    : {}),
            },
        });
        req.on('connect', (res, socket) => {
            if (res.statusCode === 200) {
                const tlsSocket = tls.connect({
                    socket,
                    servername: options.servername || (typeof options.host === 'string' ? options.host : undefined),
                }, () => callback(null, tlsSocket));
                tlsSocket.on('error', (err) => callback(err));
            }
            else {
                socket.destroy();
                callback(new Error(`Proxy CONNECT rejected with HTTP ${res.statusCode}`));
            }
        });
        req.on('error', (err) => callback(err));
        req.end();
    };
    return agent;
}
function getProxyAgent(customProxyUrl) {
    if (customProxyUrl) {
        return createTunnelAgent(customProxyUrl);
    }
    if (cachedAgent !== undefined) {
        return cachedAgent || undefined;
    }
    const envProxy = process.env.HTTPS_PROXY || process.env.HTTP_PROXY || process.env.ALL_PROXY || (cachedProxyUrl || undefined);
    if (envProxy) {
        cachedAgent = createTunnelAgent(envProxy);
        return cachedAgent;
    }
    return undefined;
}
function getRelayUrl() {
    return process.env.GOOGLE_RELAY_URL?.replace(/\/$/, '') || undefined;
}
function resetProxyCache() {
    cachedProxyUrl = undefined;
    cachedAgent = undefined;
}
//# sourceMappingURL=proxyAgent.js.map