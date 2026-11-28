/**
 * Antigravity IDE Main-Process Experiment Flags Hook.
 * Prepended as `import './antigravity-experiments-main.js';` in resources/app/out/main.js.
 */
import { app, shell } from 'electron';
import fs from 'fs';
import { createRequire } from 'module';
import os from 'os';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const require = createRequire(import.meta.url);
const { EXPERIMENT_CATALOG, sanitizeExperimentsPayload } = require('./experiments_catalog.js');

const CONFIG_FILE = path.join(process.env.REAL_HOME || os.homedir(), '.config', 'antigravity', 'experiments.json');

function loadConfig() {
    try {
        if (fs.existsSync(CONFIG_FILE)) {
            return sanitizeExperimentsPayload(JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8')));
        }
    } catch (_) {}
    return sanitizeExperimentsPayload(null);
}

const bootFlags = { ...loadConfig().flags };
let saveChain = Promise.resolve();
function saveConfig(rawJson) {
    let incoming;
    try { incoming = JSON.parse(rawJson); } catch (_) { return; }
    const clean = sanitizeExperimentsPayload(incoming);
    saveChain = saveChain.then(async () => {
        await fs.promises.mkdir(path.dirname(CONFIG_FILE), { recursive: true });
        const tmp = `${CONFIG_FILE}.${process.pid}.tmp`;
        await fs.promises.writeFile(tmp, JSON.stringify(clean, null, 2), 'utf8');
        await fs.promises.rename(tmp, CONFIG_FILE);
    }).catch(() => {});
}

let cachedClient = null;
function getClientCode() {
    if (cachedClient === null) {
        const featPath = path.join(__dirname, 'suite_features_ui.js');
        const featCode = fs.existsSync(featPath) ? fs.readFileSync(featPath, 'utf8') + '\n;\n' : '';
        const p = path.join(__dirname, 'experiments_ui_ide.js');
        cachedClient = fs.existsSync(p) ? (featCode + fs.readFileSync(p, 'utf8')) : '';
    }
    return cachedClient;
}

function handleFileAction(rawJson) {
    try {
        const data = JSON.parse(rawJson);
        let fp = String(data?.filePath || '').trim();
        if (!fp || fp.includes('\0')) return;
        fp = fp.replace(/^file:\/\//i, '').replace(/#L\d+(?:-L?\d+)?$/i, '').replace(/:\d+(?::\d+)?$/, '');
        try { fp = decodeURIComponent(fp); } catch (_) {}
        if (!fp) return;
        if (data.action === 'reveal') shell.showItemInFolder(fp);
        else if (data.action === 'open') void shell.openPath(fp);
    } catch (_) {}
}

app.on('browser-window-created', (_event, win) => {
    win.webContents.on('console-message', (_e, ...args) => {
        const msg = (args.length === 1 && typeof args[0] === 'object' && args[0] !== null) ? args[0].message : args[1];
        if (typeof msg !== 'string') return;
        if (msg.startsWith('SAVE_EXPERIMENTS_CONFIG|')) {
            saveConfig(msg.substring('SAVE_EXPERIMENTS_CONFIG|'.length));
        } else if (msg.startsWith('SUITE_FILE_ACTION|')) {
            handleFileAction(msg.substring('SUITE_FILE_ACTION|'.length));
        } else if (msg === 'SUITE_RELAUNCH_IDE') {
            try {
                require('./experiments/relaunch_helper.js').scheduleCleanRelaunch(app);
            } catch (_) {
                try {
                    require('./relaunch_helper.js').scheduleCleanRelaunch(app);
                } catch (_) {
                    setTimeout(() => {
                        try { app.releaseSingleInstanceLock?.(); } catch (_) {}
                        try { app.relaunch(); } catch (_) {}
                        try { app.quit(); } catch (_) {}
                    }, 80);
                }
            }
        }
    });

    const injectIntoTarget = async (target, isSubframe) => {
        try {
            if (!target || target.isDestroyed?.()) return;
            const url = (typeof target.getURL === 'function' ? target.getURL() : target.url) || '';
            const baseUrl = url.split(/[?#]/)[0];
            const isWebview = url.startsWith('vscode-webview://');
            if (!url.includes('workbench') && !url.includes('jetski') && !isWebview && !baseUrl.endsWith('.html') && url !== '') return;
            const uiCode = getClientCode();
            if (!uiCode) return;
            const cfg = loadConfig();
            const payload = `${uiCode}\n;\nif (window.__antigravityMountIdeExperiments) { window.__antigravityMountIdeExperiments(${JSON.stringify(EXPERIMENT_CATALOG)}, ${JSON.stringify(cfg)}, ${JSON.stringify(bootFlags)}, ${Boolean(isSubframe || isWebview)}); }`;
            if (typeof target.executeJavaScript === 'function') {
                await target.executeJavaScript(payload);
            }
        } catch (_) {}
    };

    const injectAll = async (subframesOnly) => {
        if (!subframesOnly) await injectIntoTarget(win.webContents, false);
        try {
            const root = win.webContents.mainFrame;
            const frames = root && root.framesInSubtree ? root.framesInSubtree : [];
            for (const f of frames) {
                if (f !== root) await injectIntoTarget(f, true);
            }
        } catch (_) {}
    };

    win.webContents.on('dom-ready', () => injectAll(false));
    win.webContents.on('did-frame-finish-load', () => injectAll(true));
});
