/**
 * Antigravity RTL Main-Process Injection Hook for Antigravity IDE
 * Prepend-imported at the top of resources/app/out/main.js
 * Non-blocking async font discovery, async serialized config writes, zero log-file bloat.
 */
import { app } from 'electron';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { execFile } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CONFIG_FILE = path.join(os.homedir(), '.antigravity-rtl.json');
const SAFE_STR_RE = /^[\p{L}\p{N} ._-]{0,64}$/u;

function sanitizeConfigPatch(obj) {
    const clean = {};
    if (!obj || typeof obj !== 'object') return clean;
    for (const k of ['faFont', 'enFont', 'codeFont', 'lh', 'fs']) {
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

let cachedFontBase64 = null;
function getFontBase64() {
    if (cachedFontBase64 === null) {
        const fontPath = path.join(__dirname, 'Vazirmatn-Variable.woff2');
        cachedFontBase64 = fs.existsSync(fontPath) ? fs.readFileSync(fontPath).toString('base64') : '';
    }
    return cachedFontBase64;
}

let cachedClientTemplate = null;
function getClientTemplate() {
    if (cachedClientTemplate === null) {
        const clientPath = path.join(__dirname, 'antigravity-rtl-client.js');
        cachedClientTemplate = fs.existsSync(clientPath) ? fs.readFileSync(clientPath, 'utf8') : '';
    }
    return cachedClientTemplate;
}

let cachedSystemFonts = null;
let fontsPromise = null;
function getSystemFontsAsync() {
    if (cachedSystemFonts !== null) return Promise.resolve(cachedSystemFonts);
    if (fontsPromise) return fontsPromise;
    fontsPromise = new Promise((resolve) => {
        execFile('fc-list', ['--format=%{family}\t%{lang}\t%{spacing}\n'], { timeout: 3000, maxBuffer: 8 * 1024 * 1024 }, (err, stdout) => {
            if (err || !stdout) {
                cachedSystemFonts = { all: [], fa: [], en: [], code: [] };
                resolve(cachedSystemFonts);
                return;
            }
            const allMap = new Map();
            const faSet = new Set();
            const enSet = new Set();
            const codeSet = new Set();

            for (const line of stdout.split('\n')) {
                if (!line) continue;
                const parts = line.split('\t');
                const families = parts[0] || '';
                const lang = parts[1] || '';
                const spacing = Number(parts[2] || '0');
                const isFa = /(?:^|\|)(?:fa|ar)(?:\||$)/.test(lang);
                const isEn = /(?:^|\|)en(?:\||$)/.test(lang);
                const isMono = spacing === 100 || spacing === 110;

                for (const raw of families.split(',')) {
                    const name = raw.replace(/\\-/g, '-').trim();
                    if (!name || !SAFE_STR_RE.test(name)) continue;
                    const key = name.toLowerCase();
                    if (!allMap.has(key)) allMap.set(key, name);
                    const canonical = allMap.get(key);
                    if (isFa) faSet.add(canonical);
                    if (isEn) enSet.add(canonical);
                    if (isMono) codeSet.add(canonical);
                }
            }

            const sortAlpha = (iter) => Array.from(iter).sort((a, b) => a.localeCompare(b));
            cachedSystemFonts = {
                all: sortAlpha(allMap.values()),
                fa: sortAlpha(faSet),
                en: sortAlpha(enSet),
                code: sortAlpha(codeSet)
            };
            resolve(cachedSystemFonts);
        });
    });
    return fontsPromise;
}

void getSystemFontsAsync();

export function loadRtlConfig() {
    const defaults = {
        faFont: '',
        enFont: '',
        codeFont: '',
        lh: '1.6',
        fs: '16',
        isRTL: true,
        forceRTL: false,
        panelSeen: false
    };
    if (fs.existsSync(CONFIG_FILE)) {
        try {
            const parsed = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
            return { ...defaults, ...sanitizeConfigPatch(parsed) };
        } catch (_) {}
    }
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

app.on('browser-window-created', (_event, win) => {
    win.webContents.on('console-message', (_e, ...args) => {
        const msg = (args.length === 1 && typeof args[0] === 'object' && args[0] !== null)
            ? args[0].message
            : args[1];
        if (typeof msg === 'string' && msg.startsWith('SAVE_RTL_CONFIG|')) {
            saveRtlConfig(msg.substring(16));
        }
    });

    const injectIntoTarget = async (target) => {
        try {
            if (!target || target.isDestroyed?.()) return;
            const url = (typeof target.getURL === 'function' ? target.getURL() : target.url) || '';
            if (!url.includes('workbench') && !url.includes('jetski') && !url.endsWith('.html') && url !== '') {
                return;
            }
            const tpl = getClientTemplate();
            if (!tpl) return;

            const fontBase64 = getFontBase64();
            const rtlConfig = loadRtlConfig();
            const systemFonts = await getSystemFontsAsync();
            const clientCode = tpl
                .replaceAll('__FONT_BASE64__', fontBase64)
                .replaceAll('__RTL_CONFIG__', () => JSON.stringify(rtlConfig))
                .replaceAll('__SYSTEM_FONTS__', () => JSON.stringify(systemFonts));

            if (typeof target.executeJavaScript === 'function') {
                await target.executeJavaScript(clientCode);
            }
        } catch (_) {}
    };

    const injectWindowAndFrames = async (subframesOnly) => {
        if (!subframesOnly) {
            await injectIntoTarget(win.webContents);
        }
        try {
            const root = win.webContents.mainFrame;
            const frames = root && root.framesInSubtree ? root.framesInSubtree : [];
            for (const f of frames) {
                if (f !== root) await injectIntoTarget(f);
            }
        } catch (_) {}
    };

    win.webContents.on('dom-ready', () => injectWindowAndFrames(false));
    win.webContents.on('did-frame-finish-load', () => injectWindowAndFrames(true));
});
