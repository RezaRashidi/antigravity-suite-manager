/**
 * Electron main-process RTL hook for Antigravity Standalone App (app.asar/dist/rtl/rtl_app_hook.js).
 * Loaded by invokeWindowLoadUrl in dist/utils.js before win.loadURL(url).
 * Non-blocking async system font discovery + async serialized config writes.
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFile } = require('child_process');

const SAFE_STR_RE = /^[\p{L}\p{N} ._-]{0,64}$/u;
const CONFIG_FILE = path.join(os.homedir(), '.antigravity-rtl.json');

function sanitizeConfigPatch(obj) {
    const clean = {};
    if (!obj || typeof obj !== 'object') return clean;
    for (const k of ['faFont', 'enFont', 'codeFont', 'lh', 'fs', 'fw']) {
        if (typeof obj[k] === 'string' && SAFE_STR_RE.test(obj[k])) {
            clean[k] = obj[k];
        }
    }
    for (const k of ['isRTL', 'forceRTL', 'panelSeen']) {
        if (typeof obj[k] === 'boolean') {
            clean[k] = obj[k];
        }
    }
    return clean;
}

function loadRtlConfig() {
    const defaults = {
        faFont: '',
        enFont: '',
        codeFont: '',
        lh: '1.6',
        fs: '16',
        fw: '',
        isRTL: true,
        forceRTL: false,
        panelSeen: false
    };
    try {
        if (fs.existsSync(CONFIG_FILE)) {
            const parsed = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
            return { ...defaults, ...sanitizeConfigPatch(parsed) };
        }
    } catch (_) {}
    return defaults;
}

let saveChain = Promise.resolve();
function saveRtlConfig(rawJson) {
    let incoming;
    try {
        incoming = sanitizeConfigPatch(JSON.parse(rawJson));
    } catch (_) {
        return;
    }
    saveChain = saveChain.then(async () => {
        let existing = {};
        try {
            if (fs.existsSync(CONFIG_FILE)) {
                existing = JSON.parse(await fs.promises.readFile(CONFIG_FILE, 'utf8'));
            }
        } catch (_) {}
        const merged = { ...existing, ...incoming };
        await fs.promises.writeFile(CONFIG_FILE, JSON.stringify(merged, null, 2), 'utf8');
    }).catch(() => {});
}

let cachedFontBase64 = null;
function getFontBase64() {
    if (cachedFontBase64 === null) {
        const fontPath = path.join(__dirname, 'Vazirmatn-Variable.woff2');
        cachedFontBase64 = fs.existsSync(fontPath) ? fs.readFileSync(fontPath).toString('base64') : '';
    }
    return cachedFontBase64;
}

let cachedClientBundle = null;
function getClientBundle() {
    if (cachedClientBundle === null) {
        const parts = ['rtl_engine.js', 'rtl_styles.js', 'rtl_ui_app.js'].map((name) =>
            fs.readFileSync(path.join(__dirname, name), 'utf8')
        );
        cachedClientBundle = parts.join('\n;\n');
    }
    return cachedClientBundle;
}

function fcWeightToCss(w) {
    if (w <= 20) return 100;
    if (w <= 45) return 200;
    if (w <= 65) return 300;
    if (w <= 90) return 400;
    if (w <= 140) return 500;
    if (w <= 190) return 600;
    if (w <= 202) return 700;
    if (w <= 207) return 800;
    return 900;
}

let cachedSystemFonts = null;
let fontsPromise = null;
function getSystemFontsAsync() {
    if (cachedSystemFonts !== null) return Promise.resolve(cachedSystemFonts);
    if (fontsPromise) return fontsPromise;
    fontsPromise = new Promise((resolve) => {
        execFile('fc-list', ['--format=%{family}\t%{lang}\t%{spacing}\t%{weight}\n'], { timeout: 3000, maxBuffer: 8 * 1024 * 1024 }, (err, stdout) => {
            if (err || !stdout) {
                cachedSystemFonts = { all: [], fa: [], en: [], code: [], weights: {} };
                resolve(cachedSystemFonts);
                return;
            }
            const allMap = new Map();
            const faSet = new Set();
            const enSet = new Set();
            const codeSet = new Set();
            const weightsMap = new Map();

            for (const line of stdout.split('\n')) {
                if (!line) continue;
                const parts = line.split('\t');
                const families = parts[0] || '';
                const lang = parts[1] || '';
                const spacing = Number(parts[2] || '0');
                const rawWeight = (parts[3] || '').trim();
                const isFa = /(?:^|\|)(?:fa|ar)(?:\||$)/.test(lang);
                const isEn = /(?:^|\|)en(?:\||$)/.test(lang);
                const isMono = spacing === 100 || spacing === 110;

                const primaryFamily = families.split(',')[0].replace(/\\-/g, '-').trim();
                if (!primaryFamily || !SAFE_STR_RE.test(primaryFamily)) continue;
                const key = primaryFamily.toLowerCase();
                if (!allMap.has(key)) allMap.set(key, primaryFamily);
                const canonical = allMap.get(key);
                if (isFa) faSet.add(canonical);
                if (isEn) enSet.add(canonical);
                if (isMono) codeSet.add(canonical);

                if (!weightsMap.has(key)) weightsMap.set(key, new Set());
                const wSet = weightsMap.get(key);
                const rangeMatch = rawWeight.match(/^\[(\d+)\s+(\d+)\]$/);
                if (rangeMatch) {
                    const minC = fcWeightToCss(Number(rangeMatch[1]));
                    const maxC = fcWeightToCss(Number(rangeMatch[2]));
                    for (let cw = 100; cw <= 900; cw += 100) {
                        if (cw >= minC && cw <= maxC) wSet.add(cw);
                    }
                } else if (/^\d+$/.test(rawWeight)) {
                    wSet.add(fcWeightToCss(Number(rawWeight)));
                }
            }

            const sortAlpha = (iter) => Array.from(iter).sort((a, b) => a.localeCompare(b));
            const weights = {};
            for (const [k, set] of weightsMap.entries()) {
                if (set.size > 0) weights[k] = Array.from(set).sort((a, b) => a - b);
            }
            cachedSystemFonts = {
                all: sortAlpha(allMap.values()),
                fa: sortAlpha(faSet),
                en: sortAlpha(enSet),
                code: sortAlpha(codeSet),
                weights
            };
            resolve(cachedSystemFonts);
        });
    });
    return fontsPromise;
}

// Kick off non-blocking background discovery once at module load (~40ms)
void getSystemFontsAsync();

module.exports = function attachAppRtlHook(win) {
    if (!win || !win.webContents || win._antigravitySuiteRtlAttached) return;
    win._antigravitySuiteRtlAttached = true;

    win.webContents.on('console-message', (_event, ...args) => {
        const message = (args.length === 1 && typeof args[0] === 'object' && args[0] !== null)
            ? args[0].message
            : args[1];
        if (typeof message === 'string' && message.startsWith('SAVE_RTL_CONFIG|')) {
            saveRtlConfig(message.substring(16));
        }
    });

    const injectIntoTarget = async (target, isSubframe) => {
        try {
            if (!target || (typeof target.isDestroyed === 'function' && target.isDestroyed())) return;
            const currentURL = typeof target.getURL === 'function' ? target.getURL() : (target.url || '');
            if (!currentURL || !/^https?:\/\/(?:127\.0\.0\.1|localhost):\d+/i.test(currentURL)) {
                return;
            }
            const fontBase64 = getFontBase64();
            const rtlConfig = loadRtlConfig();
            const systemFonts = await getSystemFontsAsync();
            const bootCode = `${getClientBundle()}\n;\nwindow.__AGY_RTL_FONTS__ = ${JSON.stringify(systemFonts)};\nif (window.__antigravityMountAppRtl) { window.__antigravityMountAppRtl(${JSON.stringify(fontBase64)}, ${JSON.stringify(rtlConfig)}, ${JSON.stringify(systemFonts)}, ${Boolean(isSubframe)}); }`;
            if (typeof target.executeJavaScript === 'function') {
                void target.executeJavaScript(bootCode).catch((err) => {
                    console.error('[Antigravity RTL] Inject error:', err && err.message ? err.message : String(err));
                });
            }
        } catch (err) {
            console.error('[Antigravity RTL] Hook prepare error:', err && err.message ? err.message : String(err));
        }
    };

    win.webContents.on('dom-ready', () => injectIntoTarget(win.webContents, false));
    win.webContents.on('did-frame-finish-load', () => {
        try {
            const root = win.webContents.mainFrame;
            const frames = root && root.framesInSubtree ? root.framesInSubtree : [];
            for (const f of frames) {
                if (f !== root) void injectIntoTarget(f, true);
            }
        } catch (_) {}
    });
    win.webContents.on('did-create-window', (childWin) => {
        try { attachAppRtlHook(childWin); } catch (_) {}
    });
};
