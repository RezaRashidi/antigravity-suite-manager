'use strict';

/**
 * In-process ephemeral Dev UI Server launched lazily from dist/languageServer.js.
 * Bound strictly to 127.0.0.1:0 so multiple Antigravity App profiles never collide.
 * Reads the embedded ZIP archive inside language_server read-only and patches main.js in RAM.
 */

const fs = require('fs');
const http = require('http');
const os = require('os');
const path = require('path');
const { findUiBundle, readBundleFile } = require('./ls_zip_bundle.js');
const { patchMainJs } = require('./main_js_patcher.js');

let _pricingMod = null;
try { _pricingMod = require('../router/pricing.js'); } catch (_) {}

const MIME = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.mjs': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.webp': 'image/webp',
    '.ico': 'image/x-icon',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.ttf': 'font/ttf',
    '.wasm': 'application/wasm',
};

let _server = null;
let _url = null;
let _bundleCache = null;
let _mainCache = null;

let _catalogMod = null;
try { _catalogMod = require('../experiments_catalog.js'); } catch (_) {}

function readActiveExperiments() {
    const defaults = _catalogMod ? _catalogMod.getDefaultFlags() : {
        'enable-input-draft-persistence': true,
        'configure-artifact-width': true,
        'enable-enhanced-file-viewer': true,
        'enable-open-with': true,
        'enable-conversation-groups': true,
        'enable-open-in-ide-button': true,
        'enable-conversation-forking': true,
        'enable-fork-in-new-worktree': true,
        'enable-fork-at-historical-step': true,
        conversationForking: true,
        'enable-context-usage-indicator': true,
        'enable-cost-accumulator': true,
        'enable-resource-manager': true,
    };
    try {
        const rh = process.env.REAL_HOME || os.homedir();
        const file = path.join(rh, '.config', 'antigravity', 'experiments.json');
        if (fs.existsSync(file)) {
            const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
            const clean = _catalogMod ? _catalogMod.sanitizeExperimentsPayload(raw) : null;
            const flags = clean ? clean.flags : { ...defaults, ...(raw && typeof raw.flags === 'object' ? raw.flags : {}) };
            const config = clean ? clean.config : { artifactWidth: 'default', sidebarChatLimit: 0, contextTarget: 0 };
            return {
                flags,
                config,
                indicator: flags['enable-context-usage-indicator'] !== false,
                costs: flags['enable-cost-accumulator'] !== false,
            };
        }
    } catch (_) {}
    return {
        flags: defaults,
        config: { artifactWidth: 'default', sidebarChatLimit: 0, contextTarget: 0 },
        indicator: defaults['enable-context-usage-indicator'] !== false,
        costs: defaults['enable-cost-accumulator'] !== false,
    };
}

function getBundle(lsBinaryPath) {
    const stat = fs.statSync(lsBinaryPath);
    if (_bundleCache && _bundleCache.file === lsBinaryPath && _bundleCache.size === stat.size && _bundleCache.mtimeMs === stat.mtimeMs) {
        return _bundleCache;
    }
    _bundleCache = findUiBundle(lsBinaryPath);
    _mainCache = null;
    return _bundleCache;
}

function buildBootFlagPreamble(prefs) {
    const flags = prefs.flags || {};
    const cfg = prefs.config || {};
    return `;(function(){try{var s=${JSON.stringify(flags)},c=${JSON.stringify(cfg)},k='jetski.developer.customFlagOverrides',f={};try{f=JSON.parse(localStorage.getItem(k)||'{}')}catch(_){}if(!f||typeof f!=='object'||Array.isArray(f))f={};for(var id in s){if(typeof s[id]==='boolean')f[id]=s[id];}localStorage.setItem(k,JSON.stringify(f));if(typeof s['enable-context-usage-indicator']==='boolean'){localStorage.setItem('contextUsageIndicatorEnabled',s['enable-context-usage-indicator']?'true':'false');}globalThis.__SUITE_SIDEBAR_LIMIT=Number(c.sidebarChatLimit||0);globalThis.__SUITE_CONTEXT_TARGET=Number(c.contextTarget||0);}catch(_){}})();\n`;
}

function getPatchedMain(bundle) {
    const prefs = readActiveExperiments();
    const original = readBundleFile(bundle, 'main.js');

    if (_pricingMod) void _pricingMod.triggerBackgroundRefresh(false);
    const priceData = _pricingMod ? _pricingMod.readCachedPrices() : { fetchedAt: 0 };
    const priceTable = (prefs.costs && _pricingMod) ? _pricingMod.buildCompactTable(priceData) : (prefs.costs ? {} : null);
    const flagsKey = JSON.stringify(prefs.flags) + '|' + JSON.stringify(prefs.config);
    const cacheKey = `${bundle.size}:${bundle.mtimeMs}:${flagsKey}:${priceData.fetchedAt || 0}`;

    if (_mainCache && _mainCache.key === cacheKey) return _mainCache.data;

    try {
        const res = patchMainJs(original.toString('utf8'), {
            enableIndicator: prefs.indicator,
            priceTable,
            enableSidebarLimit: true,
            enableContextTarget: true,
        });
        const buf = Buffer.from(buildBootFlagPreamble(prefs) + res.source, 'utf8');
        _mainCache = { key: cacheKey, data: buf };
        return buf;
    } catch (err) {
        console.warn('[Suite DevUI] Fail-open serving original main.js:', err && err.message ? err.message : String(err));
        return original;
    }
}

function ensureDevUiServer(lsBinaryPath) {
    if (_url) return Promise.resolve(_url);
    return new Promise((resolve) => {
        try {
            if (!lsBinaryPath || !fs.existsSync(lsBinaryPath)) { resolve(null); return; }
            const srv = http.createServer((req, res) => {
                try {
                    const pathname = decodeURIComponent((req.url || '/').split('?')[0]);
                    if (!pathname.startsWith('/') || pathname.includes('\0') || pathname.includes('..')) {
                        res.writeHead(404); res.end(); return;
                    }
                    const name = pathname === '/' ? 'index.html' : pathname.slice(1);
                    const bundle = getBundle(lsBinaryPath);
                    const body = name === 'main.js' ? getPatchedMain(bundle) : readBundleFile(bundle, name);
                    if (!body) { res.writeHead(404); res.end('Not found'); return; }
                    res.writeHead(200, {
                        'Content-Type': MIME[path.extname(name).toLowerCase()] || 'application/octet-stream',
                        'Content-Length': body.length,
                        'Cache-Control': 'no-cache',
                    });
                    res.end(req.method === 'HEAD' ? undefined : body);
                } catch (err) {
                    res.writeHead(500);
                    res.end(err && err.message ? err.message : 'DevUI error');
                }
            });
            srv.on('error', () => resolve(null));
            srv.listen(0, '127.0.0.1', () => {
                const addr = srv.address();
                if (addr && typeof addr === 'object' && addr.port) {
                    _server = srv;
                    _url = `http://127.0.0.1:${addr.port}`;
                    resolve(_url);
                } else {
                    resolve(null);
                }
            });
        } catch (_) {
            resolve(null);
        }
    });
}

function stopDevUiServer() {
    try { if (_server) _server.close(); } catch (_) {}
    _server = null;
    _url = null;
}

module.exports = { ensureDevUiServer, stopDevUiServer };
