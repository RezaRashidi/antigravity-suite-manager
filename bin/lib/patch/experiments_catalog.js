'use strict';

/**
 * Curated Safe Experiment Flags Catalog shared by Router, App, and IDE.
 * Dangerous/unstable overrides (e.g. guidelinesOverride, macos-only CUA, battle-mode) are intentionally excluded.
 */

const ARTIFACT_WIDTH_OPTIONS = [
    { id: 'default', label: 'Default', css: '' },
    { id: 'wide', label: 'Wide (960px)', css: '960px' },
    { id: 'full', label: 'Full (1280px)', css: 'min(92vw, 1280px)' },
];

const EXPERIMENT_CATALOG = [
    // Group 1: UI & Editor (localStorage customFlagOverrides)
    {
        id: 'enable-input-draft-persistence',
        label: 'Input Draft Persistence',
        description: 'Preserve typed unsent prompt text across reloads/restarts',
        group: 'ui',
        layer: 'client',
        requiresRestart: false,
        defaultEnabled: true,
    },
    {
        id: 'configure-artifact-width',
        label: 'Configurable Artifact Width',
        description: 'Allow wide artifact panes (helpful for Persian Markdown & Mermaid)',
        group: 'ui',
        layer: 'client',
        requiresRestart: false,
        defaultEnabled: true,
        hasWidthOption: true,
    },
    {
        id: 'enable-enhanced-file-viewer',
        label: 'Enhanced File Viewer',
        description: 'Enable enhanced preview for attached and workspace files',
        group: 'ui',
        layer: 'client',
        requiresRestart: false,
        defaultEnabled: true,
    },
    {
        id: 'enable-open-with',
        label: 'Open With Menu',
        description: 'Show "Open With" external app launcher actions for files',
        group: 'ui',
        layer: 'client',
        requiresRestart: false,
        defaultEnabled: true,
    },
    {
        id: 'enable-conversation-groups',
        label: 'Conversation Groups',
        description: 'Group conversations cleanly inside sidebar navigation',
        group: 'ui',
        layer: 'client',
        requiresRestart: false,
        defaultEnabled: true,
    },
    {
        id: 'enable-open-in-ide-button',
        label: 'Open in IDE Button',
        description: 'Show native Open in IDE button in App titlebar',
        group: 'ui',
        layer: 'client',
        requiresRestart: true,
        defaultEnabled: true,
    },
    {
        id: 'enable-compact-layout',
        label: 'Compact Layout',
        description: 'Tighten chat line height (1.42) & tool block padding',
        group: 'ui',
        layer: 'client',
        requiresRestart: false,
        defaultEnabled: false,
    },
    {
        id: 'enable-fulltext-search',
        label: 'Full-Text Chat Search',
        description: 'Search message text, code & commands inside conversation picker',
        group: 'ui',
        layer: 'client',
        requiresRestart: false,
        defaultEnabled: true,
    },
    {
        id: 'enable-file-context-menu',
        label: 'File Context Menu (#L:C)',
        description: 'Right-click file:// links to attach, open, reveal or copy #L:C',
        group: 'ui',
        layer: 'client',
        requiresRestart: false,
        defaultEnabled: true,
    },

    // Group 2: Conversation Forking
    {
        id: 'enable-conversation-forking',
        label: 'Conversation Forking',
        description: 'Enable forking chats into a branched timeline',
        group: 'fork',
        layer: 'both',
        requiresRestart: false,
        defaultEnabled: true,
    },
    {
        id: 'enable-fork-in-new-worktree',
        label: 'Fork in New Worktree',
        description: 'Allow forking into a separate git worktree workspace',
        group: 'fork',
        layer: 'both',
        requiresRestart: false,
        defaultEnabled: true,
    },
    {
        id: 'enable-fork-at-historical-step',
        label: 'Fork at Historical Step',
        description: 'Allow branching from earlier assistant/user turns',
        group: 'fork',
        layer: 'both',
        requiresRestart: false,
        defaultEnabled: true,
    },
    {
        id: 'conversationForking',
        label: 'Forking Server Sync',
        description: 'Sync conversationForking flag through LS listExperiments',
        group: 'fork',
        layer: 'both',
        requiresRestart: true,
        defaultEnabled: true,
    },

    // Group 3: Agent & Telemetry (Router listExperiments / fetchConfig + Runtime Hooks)
    {
        id: 'enable-context-usage-indicator',
        label: 'Context Window Indicator',
        description: 'Show context fill percentage ring & breakdown popover',
        group: 'agent',
        layer: 'both',
        requiresRestart: true,
        defaultEnabled: true,
    },
    {
        id: 'enable-cost-accumulator',
        label: 'Real USD Cost Accumulator',
        description: 'Calculate session & turn USD spend using models.dev rates',
        group: 'agent',
        layer: 'both',
        requiresRestart: true,
        defaultEnabled: true,
    },
    {
        id: 'enable-resource-manager',
        label: 'Resource Manager',
        description: 'Show Settings -> Running view for tasks & terminals',
        group: 'agent',
        layer: 'both',
        requiresRestart: true,
        defaultEnabled: true,
    },
    {
        id: 'enable-speed-telemetry',
        label: 'Speed & Turn Telemetry',
        description: 'Show tok/s, TTFT, per-turn breakdown & cache drop alerts',
        group: 'agent',
        layer: 'both',
        requiresRestart: false,
        defaultEnabled: true,
    },
];

const MANAGED_FLAG_IDS = new Set(EXPERIMENT_CATALOG.map((item) => item.id));

const DISABLED_LEGACY_DEFAULTS = {
    'enable-developer-mode': false,
    'enable-git-vcs-ui': false,
    'enable-jj-vcs-ui': false,
    'enable-abfs-workspace-ui': false,
    'google-workspace-mentions': false,
};

const BLOCKED_EXPERIMENTAL_KEYS = [
    'enable-battle-mode',
    'enable-battle-contrib-variants',
    'enable-battle-mode-custom-agents',
    'jetski-autonomous-mode',
    'labs-autonomous-mode',
    'enable-aux-pane-redesign',
    'enable-thought-editing',
    'enable-thought-steering-from-selection',
];

function getDefaultFlags() {
    const out = {};
    for (const item of EXPERIMENT_CATALOG) {
        out[item.id] = Boolean(item.defaultEnabled);
    }
    return out;
}

const SIDEBAR_LIMIT_OPTIONS = [0, 10, 20, -1];
const CONTEXT_TARGET_OPTIONS = [0, 256000, 500000, 1000000];

function getDefaultConfig() {
    return {
        artifactWidth: 'default',
        sidebarChatLimit: 0,
        contextTarget: 0,
    };
}

function sanitizeExperimentsPayload(raw) {
    const defaults = getDefaultFlags();
    const defCfg = getDefaultConfig();
    const flags = { ...defaults };
    const config = { ...defCfg };
    let uiSeen = false;

    if (raw && typeof raw === 'object') {
        const srcFlags = (raw.flags && typeof raw.flags === 'object') ? raw.flags : {};
        for (const id of MANAGED_FLAG_IDS) {
            if (typeof srcFlags[id] === 'boolean') {
                flags[id] = srcFlags[id];
            }
        }
        const srcCfg = (raw.config && typeof raw.config === 'object') ? raw.config : {};
        if (typeof srcCfg.artifactWidth === 'string' && ARTIFACT_WIDTH_OPTIONS.some((o) => o.id === srcCfg.artifactWidth)) {
            config.artifactWidth = srcCfg.artifactWidth;
        }
        if (SIDEBAR_LIMIT_OPTIONS.includes(Number(srcCfg.sidebarChatLimit))) {
            config.sidebarChatLimit = Number(srcCfg.sidebarChatLimit);
        }
        if (CONTEXT_TARGET_OPTIONS.includes(Number(srcCfg.contextTarget))) {
            config.contextTarget = Number(srcCfg.contextTarget);
        }
        if (typeof raw.uiSeen === 'boolean') {
            uiSeen = raw.uiSeen;
        }
    }

    return { flags, config, uiSeen };
}

function mergeCustomFlagOverrides(existingOverrides, experimentsState) {
    const base = (existingOverrides && typeof existingOverrides === 'object' && !Array.isArray(existingOverrides))
        ? { ...existingOverrides }
        : {};
    const state = sanitizeExperimentsPayload(experimentsState);

    for (const [k, v] of Object.entries(DISABLED_LEGACY_DEFAULTS)) {
        if (!(k in base)) base[k] = v;
    }
    for (const bad of BLOCKED_EXPERIMENTAL_KEYS) {
        delete base[bad];
    }
    for (const item of EXPERIMENT_CATALOG) {
        base[item.id] = Boolean(state.flags[item.id]);
    }
    return base;
}

module.exports = {
    ARTIFACT_WIDTH_OPTIONS,
    EXPERIMENT_CATALOG,
    MANAGED_FLAG_IDS,
    DISABLED_LEGACY_DEFAULTS,
    BLOCKED_EXPERIMENTAL_KEYS,
    getDefaultFlags,
    getDefaultConfig,
    sanitizeExperimentsPayload,
    mergeCustomFlagOverrides,
};
