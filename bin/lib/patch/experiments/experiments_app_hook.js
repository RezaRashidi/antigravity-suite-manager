'use strict';

/**
 * Electron main-process hook for Experiment Flags in Antigravity App.
 * Attached inside dist/utils.js invokeWindowLoadUrl alongside rtl_app_hook.js.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { app, shell } = require('electron');

let _expRouter = null;
try { _expRouter = require('../router/experiments.js'); } catch (_) {}

const {
    ARTIFACT_WIDTH_OPTIONS,
    EXPERIMENT_CATALOG,
    sanitizeExperimentsPayload,
} = require('../experiments_catalog.js');

function getConfigPath() {
    if (_expRouter) return _expRouter.resolveConfigPath();
    const rh = process.env.REAL_HOME || os.homedir();
    return path.join(rh, '.config', 'antigravity', 'experiments.json');
}

function loadConfig() {
    if (_expRouter) return _expRouter.readExperimentsState();
    const file = getConfigPath();
    try {
        if (fs.existsSync(file)) {
            return sanitizeExperimentsPayload(JSON.parse(fs.readFileSync(file, 'utf8')));
        }
    } catch (_) {}
    return sanitizeExperimentsPayload(null);
}

let _bootFlags = null;
function getBootFlags() {
    if (!_bootFlags) _bootFlags = { ...loadConfig().flags };
    return _bootFlags;
}

let saveChain = Promise.resolve();
function saveConfig(rawJson) {
    let incoming;
    try { incoming = JSON.parse(rawJson); } catch (_) { return; }
    if (_expRouter) {
        try { _expRouter.writeExperimentsPatch(incoming); } catch (_) {}
        return;
    }
    const clean = sanitizeExperimentsPayload(incoming);
    const file = getConfigPath();
    saveChain = saveChain.then(async () => {
        await fs.promises.mkdir(path.dirname(file), { recursive: true });
        const tmp = `${file}.${process.pid}.tmp`;
        await fs.promises.writeFile(tmp, JSON.stringify(clean, null, 2), 'utf8');
        await fs.promises.rename(tmp, file);
    }).catch(() => {});
}

let cachedUiCode = null;
function getUiCode() {
    if (cachedUiCode === null) {
        const featPath = path.join(__dirname, 'suite_features_ui.js');
        const featCode = fs.existsSync(featPath) ? fs.readFileSync(featPath, 'utf8') + '\n;\n' : '';
        cachedUiCode = featCode + fs.readFileSync(path.join(__dirname, 'experiments_ui_app.js'), 'utf8');
    }
    return cachedUiCode;
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

module.exports = function attachAppExperimentsHook(win) {
    if (!win || !win.webContents || win._antigravitySuiteExperimentsAttached) return;
    win._antigravitySuiteExperimentsAttached = true;
    const bootFlags = getBootFlags();

    win.webContents.on('console-message', (_event, ...args) => {
        const message = (args.length === 1 && typeof args[0] === 'object' && args[0] !== null) ? args[0].message : args[1];
        if (typeof message !== 'string') return;
        if (message.startsWith('SAVE_EXPERIMENTS_CONFIG|')) {
            saveConfig(message.substring('SAVE_EXPERIMENTS_CONFIG|'.length));
        } else if (message.startsWith('SUITE_FILE_ACTION|')) {
            handleFileAction(message.substring('SUITE_FILE_ACTION|'.length));
        } else if (message === 'SUITE_RELAUNCH_APP') {
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
    });

    const injectIntoTarget = async (target, isSubframe) => {
        try {
            if (!target || (typeof target.isDestroyed === 'function' && target.isDestroyed())) return;
            const currentURL = typeof target.getURL === 'function' ? target.getURL() : (target.url || '');
            if (!currentURL || !/^https?:\/\/(?:127\.0\.0\.1|localhost):\d+/i.test(currentURL)) return;
            const cfg = loadConfig();
            const boot = `${getUiCode()}\n;\nif (window.__antigravityMountAppExperiments) { window.__antigravityMountAppExperiments(${JSON.stringify(EXPERIMENT_CATALOG)}, ${JSON.stringify(cfg)}, ${JSON.stringify(bootFlags)}, ${Boolean(isSubframe)}); }`;
            if (typeof target.executeJavaScript === 'function') {
                void target.executeJavaScript(boot).catch(() => {});
            }
        } catch (_) {}
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
        try { attachAppExperimentsHook(childWin); } catch (_) {}
    });
};

module.exports.ARTIFACT_WIDTH_OPTIONS = ARTIFACT_WIDTH_OPTIONS;
