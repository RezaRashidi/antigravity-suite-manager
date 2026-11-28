'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const {
    ARTIFACT_WIDTH_OPTIONS,
    EXPERIMENT_CATALOG,
    MANAGED_FLAG_IDS,
    sanitizeExperimentsPayload,
} = require('../experiments_catalog.js');

function resolveConfigPath() {
    const rh = process.env.REAL_HOME || os.homedir();
    return path.join(rh, '.config', 'antigravity', 'experiments.json');
}

let _bootSnapshot = null;
let _cachedRawMtime = -1;
let _cachedState = null;

function readExperimentsState() {
    const file = resolveConfigPath();
    try {
        if (fs.existsSync(file)) {
            const st = fs.statSync(file);
            if (_cachedState && st.mtimeMs === _cachedRawMtime) {
                return _cachedState;
            }
            const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
            _cachedState = sanitizeExperimentsPayload(parsed);
            _cachedRawMtime = st.mtimeMs;
        } else {
            _cachedState = sanitizeExperimentsPayload(null);
            _cachedRawMtime = 0;
        }
    } catch (_) {
        _cachedState = sanitizeExperimentsPayload(null);
    }
    if (_bootSnapshot === null) {
        _bootSnapshot = { ..._cachedState.flags };
    }
    return _cachedState;
}

function writeExperimentsPatch(patch) {
    const file = resolveConfigPath();
    const cur = readExperimentsState();
    const nextFlags = { ...cur.flags };
    const nextConfig = { ...cur.config };
    let uiSeen = cur.uiSeen;

    if (patch && typeof patch === 'object') {
        if (patch.reset === true) {
            const reset = sanitizeExperimentsPayload(null);
            Object.assign(nextFlags, reset.flags);
            Object.assign(nextConfig, reset.config);
        }
        const incomingFlags = (patch.flags && typeof patch.flags === 'object') ? patch.flags : {};
        for (const id of MANAGED_FLAG_IDS) {
            if (typeof incomingFlags[id] === 'boolean') {
                nextFlags[id] = incomingFlags[id];
            }
        }
        const incomingCfg = (patch.config && typeof patch.config === 'object') ? patch.config : {};
        if (typeof incomingCfg.artifactWidth === 'string' && ARTIFACT_WIDTH_OPTIONS.some((o) => o.id === incomingCfg.artifactWidth)) {
            nextConfig.artifactWidth = incomingCfg.artifactWidth;
        }
        if (typeof patch.uiSeen === 'boolean') {
            uiSeen = patch.uiSeen;
        }
    }

    const clean = sanitizeExperimentsPayload({ flags: nextFlags, config: nextConfig, uiSeen });
    try {
        fs.mkdirSync(path.dirname(file), { recursive: true });
        const tmp = `${file}.${process.pid}.tmp`;
        fs.writeFileSync(tmp, JSON.stringify(clean, null, 2), 'utf8');
        fs.renameSync(tmp, file);
        const st = fs.statSync(file);
        _cachedRawMtime = st.mtimeMs;
    } catch (_) {}
    _cachedState = clean;
    return getPublicExperimentsPayload();
}

function getPendingRestartFlags(state = readExperimentsState()) {
    const boot = _bootSnapshot || state.flags;
    const pending = [];
    for (const item of EXPERIMENT_CATALOG) {
        if (!item.requiresRestart) continue;
        if (Boolean(state.flags[item.id]) !== Boolean(boot[item.id])) {
            pending.push(item.id);
        }
    }
    return pending;
}

function getPublicExperimentsPayload() {
    const state = readExperimentsState();
    const pendingRestart = getPendingRestartFlags(state);
    return {
        catalog: EXPERIMENT_CATALOG,
        widthOptions: ARTIFACT_WIDTH_OPTIONS,
        flags: state.flags,
        config: state.config,
        uiSeen: state.uiSeen,
        bootFlags: _bootSnapshot || state.flags,
        pendingRestart,
        requiresRestart: pendingRestart.length > 0,
    };
}

function upsertProtoFlagArray(arr, state) {
    if (!Array.isArray(arr)) return false;
    let changed = false;
    const byName = new Map();
    for (const entry of arr) {
        if (entry && typeof entry === 'object' && typeof entry.name === 'string') {
            byName.set(entry.name, entry);
        }
    }
    for (const item of EXPERIMENT_CATALOG) {
        if (item.layer !== 'both' && item.layer !== 'server') continue;
        const enabled = Boolean(state.flags[item.id]);
        const existing = byName.get(item.id);
        if (existing) {
            if ('boolValue' in existing || !('intValue' in existing || 'stringValue' in existing || 'floatValue' in existing)) {
                if (existing.boolValue !== enabled) {
                    existing.boolValue = enabled;
                    changed = true;
                }
            }
            if ('enabled' in existing && existing.enabled !== enabled) {
                existing.enabled = enabled;
                changed = true;
            }
        } else {
            arr.push({ name: item.id, boolValue: enabled });
            changed = true;
        }
    }
    return changed;
}

function mergeExperimentPayload(parsed, state, reqUrl = '') {
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return false;
    let changed = false;
    const isFetchConfig = typeof reqUrl === 'string' && (reqUrl.includes(':fetchConfig') || reqUrl.includes('/FetchConfig'));
    const isListExp = !reqUrl || (typeof reqUrl === 'string' && reqUrl.includes('listExperiments'));

    const applyFlagMap = (obj) => {
        if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return false;
        let touched = false;
        for (const item of EXPERIMENT_CATALOG) {
            if (item.layer !== 'both' && item.layer !== 'server') continue;
            const enabled = Boolean(state.flags[item.id]);
            if (obj[item.id] !== enabled) {
                obj[item.id] = enabled;
                touched = true;
            }
        }
        return touched;
    };

    // Standard listExperiments shape: { experimentIds: [...], flags: [{ name, boolValue }, ...] }
    // Proto3 omits `flags` when empty (`{}`), so materialize it cleanly on listExperiments.
    if (isListExp && !Array.isArray(parsed.flags) && !parsed.experimentConfig && !(parsed.flags && typeof parsed.flags === 'object')) {
        parsed.flags = [];
    }
    if (Array.isArray(parsed.flags)) {
        if (upsertProtoFlagArray(parsed.flags, state)) changed = true;
    } else if (parsed.flags && typeof parsed.flags === 'object') {
        if (applyFlagMap(parsed.flags)) changed = true;
    }

    // Standard fetchConfig shape: { experimentConfig: { experimentFlags: [{ name, boolValue }, ...] } }
    if (isFetchConfig && (!parsed.experimentConfig || typeof parsed.experimentConfig !== 'object')) {
        parsed.experimentConfig = { experimentFlags: [] };
    }
    if (parsed.experimentConfig && typeof parsed.experimentConfig === 'object') {
        if (!Array.isArray(parsed.experimentConfig.experimentFlags)) {
            parsed.experimentConfig.experimentFlags = [];
        }
        if (upsertProtoFlagArray(parsed.experimentConfig.experimentFlags, state)) changed = true;
    }

    if (Array.isArray(parsed.experiments)) {
        if (upsertProtoFlagArray(parsed.experiments, state)) changed = true;
    } else if (parsed.experiments && typeof parsed.experiments === 'object') {
        if (applyFlagMap(parsed.experiments)) changed = true;
    }

    if (parsed.flagValues && typeof parsed.flagValues === 'object' && !Array.isArray(parsed.flagValues)) {
        if (applyFlagMap(parsed.flagValues)) changed = true;
    }

    if ('contextUsageIndicatorEnabled' in parsed && MANAGED_FLAG_IDS.has('enable-context-usage-indicator')) {
        parsed.contextUsageIndicatorEnabled = Boolean(state.flags['enable-context-usage-indicator']);
        changed = true;
    }
    if ('conversationForking' in parsed && MANAGED_FLAG_IDS.has('conversationForking')) {
        const val = Boolean(state.flags.conversationForking);
        if (typeof parsed.conversationForking === 'object' && parsed.conversationForking !== null) {
            parsed.conversationForking.enabled = val;
        } else {
            parsed.conversationForking = { enabled: val };
        }
        changed = true;
    }
    return changed;
}

function mergeRpcExperimentsResponse(rawText, reqUrl = '') {
    if (!rawText || typeof rawText !== 'string') return rawText;
    try {
        const parsed = JSON.parse(rawText);
        const state = readExperimentsState();
        if (mergeExperimentPayload(parsed, state, reqUrl)) {
            return JSON.stringify(parsed);
        }
    } catch (_) {}
    return rawText;
}

module.exports = {
    resolveConfigPath,
    readExperimentsState,
    writeExperimentsPatch,
    getPendingRestartFlags,
    getPublicExperimentsPayload,
    mergeExperimentPayload,
    mergeRpcExperimentsResponse,
};
