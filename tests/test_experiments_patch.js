'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { test } = require('node:test');

const ROOT = path.resolve(__dirname, '..');
const catalog = require(path.join(ROOT, 'bin/lib/patch/experiments_catalog.js'));
const expRouter = require(path.join(ROOT, 'bin/lib/patch/router/experiments.js'));
const pricing = require(path.join(ROOT, 'bin/lib/patch/router/pricing.js'));
const mainPatcher = require(path.join(ROOT, 'bin/lib/patch/experiments/main_js_patcher.js'));
const { patchAppExperiments, unpatchAppExperiments, patchIdeExperiments, unpatchIdeExperiments } = require(path.join(ROOT, 'bin/lib/patch/patch_experiments.js'));

test('experiment catalog excludes unsafe or natively-active overrides and merges customFlagOverrides without clobbering', () => {
    const ids = new Set(catalog.EXPERIMENT_CATALOG.map((x) => x.id));
    for (const required of [
        'enable-input-draft-persistence',
        'configure-artifact-width',
        'enable-enhanced-file-viewer',
        'enable-open-with',
        'enable-conversation-groups',
        'enable-open-in-ide-button',
        'enable-compact-layout',
        'enable-fulltext-search',
        'enable-file-context-menu',
        'enable-speed-telemetry',
        'enable-resource-manager',
        'enable-cost-accumulator',
        'enable-context-usage-indicator',
        'enable-conversation-forking',
    ]) {
        assert.ok(ids.has(required), `missing expected catalog flag ${required}`);
    }
    assert.ok(!ids.has('enable-review'));
    assert.ok(!ids.has('enable-deepagent'));
    assert.ok(!ids.has('enable-subagent-dropdown-models'));
    assert.ok(!ids.has('guidelinesOverride'));
    assert.ok(!ids.has('enable-agy-hub-cua-macos'));

    const existing = { 'user-custom-flag': true, 'enable-battle-mode': true };
    const merged = catalog.mergeCustomFlagOverrides(existing, {
        flags: { 'enable-resource-manager': false, 'enable-conversation-forking': false },
        config: { artifactWidth: 'wide' },
    });
    assert.strictEqual(merged['user-custom-flag'], true);
    assert.strictEqual(merged['enable-battle-mode'], undefined);
    assert.strictEqual(merged['enable-resource-manager'], false);
    assert.strictEqual(merged['enable-conversation-forking'], false);
    assert.strictEqual(merged['enable-input-draft-persistence'], true);
});

test('mergeRpcExperimentsResponse handles listExperiments flags and fetchConfig experimentConfig arrays', () => {
    const tmpHome = fs.mkdtempSync(path.join(os.tmpdir(), 'exp-test-'));
    const origHome = process.env.REAL_HOME;
    process.env.REAL_HOME = tmpHome;
    try {
        expRouter.writeExperimentsPatch({
            flags: { 'enable-resource-manager': true, 'enable-context-usage-indicator': false, 'enable-cost-accumulator': true },
            config: { artifactWidth: 'full' },
        });
        const listRes = JSON.parse(expRouter.mergeRpcExperimentsResponse(JSON.stringify({
            experimentIds: ['1'],
            flags: [{ name: 'enable-context-usage-indicator', boolValue: true }],
        })));
        const ctxEntry = listRes.flags.find((f) => f.name === 'enable-context-usage-indicator');
        const resEntry = listRes.flags.find((f) => f.name === 'enable-resource-manager');
        assert.strictEqual(ctxEntry.boolValue, false);
        assert.strictEqual(resEntry.boolValue, true);

        const emptyList = JSON.parse(expRouter.mergeRpcExperimentsResponse('{}', '/v1internal:listExperiments'));
        assert.strictEqual(emptyList.flags.find((f) => f.name === 'enable-cost-accumulator').boolValue, true);
        assert.strictEqual(emptyList.flags.find((f) => f.name === 'enable-context-usage-indicator').boolValue, false);
        assert.strictEqual(emptyList.flags.find((f) => f.name === 'enable-fork-at-historical-step').boolValue, true);

        const cfgRes = JSON.parse(expRouter.mergeRpcExperimentsResponse(JSON.stringify({
            experimentConfig: { experimentFlags: [] },
        }), '/v1alpha:fetchConfig'));
        const costEntry = cfgRes.experimentConfig.experimentFlags.find((f) => f.name === 'enable-cost-accumulator');
        assert.strictEqual(costEntry.boolValue, true);
    } finally {
        if (origHome === undefined) delete process.env.REAL_HOME;
        else process.env.REAL_HOME = origHome;
        fs.rmSync(tmpHome, { recursive: true, force: true });
    }
});

test('main_js_patcher injects native Context Indicator and reprices costSummary accurately', () => {
    const fakeMain =
        'const F={useState:()=>[],useEffect:()=>{},useRef:()=>({}),createElement:()=>{},Component:class{}};F.createElement("div");' +
        '(0,F.useState)(0),(0,F.useState)(1),(0,F.useState)(2),(0,F.useState)(3),(0,F.useState)(4),(0,F.useState)(5),' +
        '(0,F.useState)(6),(0,F.useState)(7),(0,F.useState)(8),(0,F.useState)(9),(0,F.useState)(10),(0,F.useState)(11),' +
        '(0,F.useState)(12),(0,F.useState)(13),(0,F.useState)(14),(0,F.useState)(15),(0,F.useState)(16),(0,F.useState)(17),' +
        '(0,F.useState)(18),(0,F.useState)(19),(0,F.useState)(20);' +
        'const mO=(e,t)=>{var r=[],{optimisticState:n,trueState:i}=h(e,t);return r};' +
        'const s={contextUsageIndicator:void 0,x:1};' +
        'function applyCost(b,c){b.costSummary!==void 0&&(c.costSummary=b.costSummary)}';

    const det = mainPatcher.detectNames(fakeMain);
    assert.strictEqual(det.ok, true);
    assert.strictEqual(det.react, 'F');
    assert.strictEqual(det.stateHook, 'mO');

    const res = mainPatcher.patchMainJs(fakeMain, {
        enableIndicator: true,
        priceTable: { 'gemini-4-hydrogen': [2.0, 12.0, 0.2] },
    });
    assert.strictEqual(res.report.indicator.ok, true);
    assert.strictEqual(res.report.costs.ok, true);
    assert.ok(res.source.includes('contextUsageIndicator:{Indicator:'));
    assert.ok(!res.source.includes('contextUsageIndicator:void 0,'));

    // Verify circular dollar icon replacement in both App and IDE styles
    const appIcon = 'F.createElement("circle",{cx:"12",cy:"12",r:"10"}),F.createElement("path",{d:"M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"}),F.createElement("path",{d:"M12 18V6"})';
    const ideIcon = 'd("circle",{cx:"12",cy:"12",r:"10"}),d("path",{d:"M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"}),d("path",{d:"M12 18V6"})';
    const rAppIcon = mainPatcher.replaceCostDollarIcon(appIcon);
    const rIdeIcon = mainPatcher.replaceCostDollarIcon(ideIcon);
    assert.strictEqual(rAppIcon.count, 1);
    assert.strictEqual(rIdeIcon.count, 1);
    assert.ok(!rAppIcon.source.includes('"circle"'));
    assert.ok(rAppIcon.source.includes('F.createElement("path",{d:"M4 20h16"})'));
    assert.ok(rIdeIcon.source.includes('d("path",{d:"M12 16V6"})'));

    // Execute generated cost repricer directly against a zero-priced costSummary
    const repriceFn = new Function(`${res.source}; const out={}; applyCost({costSummary:{total:{turn:{pricing:{modelName:"Gemini 4 Hydrogen (High)",inputPricePerMillionTokens:0,outputPricePerMillionTokens:0,cacheReadPricePerMillionTokens:0},estimatedCostUsd:0,input:{tokens:1000000},cacheRead:{tokens:0},output:{tokens:500000}}}}}, out); return out.costSummary;`)();
    assert.strictEqual(repriceFn.total.turn.estimatedCostUsd, 8.0);
    assert.strictEqual(repriceFn.total.turn.pricing.inputPricePerMillionTokens, 2.0);
});

test('patchAppExperiments and patchIdeExperiments unify Experiments, Forking, Cost and Open-IDE cleanly', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'patch-exp-'));
    try {
        // Synthetic App unpacked dir including preload, ideInstall constants, and --dev_mode
        const appDir = path.join(tmp, 'app');
        const distDir = path.join(appDir, 'dist');
        fs.mkdirSync(path.join(distDir, 'ideInstall'), { recursive: true });
        const origUtils = 'async function load(win, url) {\n    await win.loadURL(url);\n}\n';
        const origLs = "async function startLanguageServer(port, csrf, options = {}) {\n    const args = [\n            '--enable_sidecars',\n            '--dev_mode',\n    ];\n    const loginShellEnv = await shellEnvReads.take();\n    const env = {};\n    env['ANTIGRAVITY_SERVER_CSRF_TOKEN'] = csrf;\n}\n";
        const origPreload = "console.log('orig preload');\n";
        const origConst = "function p() { switch(process.platform) { case 'linux': return '/x'; } }\n";
        fs.writeFileSync(path.join(distDir, 'utils.js'), origUtils);
        fs.writeFileSync(path.join(distDir, 'languageServer.js'), origLs);
        fs.writeFileSync(path.join(distDir, 'preload.js'), origPreload);
        fs.writeFileSync(path.join(distDir, 'ideInstall', 'constants.js'), origConst);

        patchAppExperiments(appDir);
        assert.ok(fs.readFileSync(path.join(distDir, 'utils.js'), 'utf8').includes('experiments_app_hook.js'));
        assert.ok(fs.readFileSync(path.join(distDir, 'languageServer.js'), 'utf8').includes('dev_ui_server.js'));
        assert.ok(!fs.readFileSync(path.join(distDir, 'languageServer.js'), 'utf8').includes("'--dev_mode'"));
        const patchedPreload = fs.readFileSync(path.join(distDir, 'preload.js'), 'utf8');
        assert.ok(patchedPreload.includes('FORK_EXP_PRELOAD_START'));
        assert.ok(patchedPreload.includes('OPEN_IDE_PRELOAD_START'));
        assert.ok(patchedPreload.includes('enable-open-in-ide-button'));
        assert.ok(fs.readFileSync(path.join(distDir, 'ideInstall', 'constants.js'), 'utf8').includes('OPEN_IDE_CONST_START'));
        patchAppExperiments(appDir); // idempotent second call
        assert.strictEqual(fs.readFileSync(path.join(distDir, 'utils.js'), 'utf8').split('ANTIGRAVITY_SUITE_EXPERIMENTS_START').length - 1, 1);
        assert.strictEqual(fs.readFileSync(path.join(distDir, 'preload.js'), 'utf8').split('OPEN_IDE_PRELOAD_START').length - 1, 1);

        unpatchAppExperiments(appDir);
        assert.strictEqual(fs.readFileSync(path.join(distDir, 'utils.js'), 'utf8'), origUtils);
        assert.strictEqual(fs.readFileSync(path.join(distDir, 'preload.js'), 'utf8'), origPreload);
        assert.strictEqual(fs.readFileSync(path.join(distDir, 'ideInstall', 'constants.js'), 'utf8'), origConst);
        assert.ok(!fs.readFileSync(path.join(distDir, 'languageServer.js'), 'utf8').includes('dev_ui_server.js'));
        assert.ok(!fs.existsSync(path.join(distDir, 'experiments')));
        assert.ok(!fs.existsSync(path.join(distDir, 'antigravity_fork_patch.marker')));
        assert.ok(!fs.existsSync(path.join(distDir, 'antigravity_open_ide_patch.marker')));

        // Synthetic IDE dir including workbench & conversationForking
        const ideDir = path.join(tmp, 'ide');
        const outDir = path.join(ideDir, 'resources/app/out');
        fs.mkdirSync(path.join(outDir, 'jetskiAgent'), { recursive: true });
        fs.mkdirSync(path.join(outDir, 'vs/workbench'), { recursive: true });
        const origIdeMain = 'const f=cfg.get("conversationForking")?.enabled??!1;\n';
        const origJetski = 't.costSummary!==void 0&&(r.costSummary=t.costSummary);const k=cfg.get("conversationForking")?.enabled??!1;\n';
        const origWb = 'const w=cfg.get("conversationForking")?.enabled??!1;\n';
        fs.writeFileSync(path.join(outDir, 'main.js'), origIdeMain);
        fs.writeFileSync(path.join(outDir, 'jetskiAgent/main.js'), origJetski);
        fs.writeFileSync(path.join(outDir, 'vs/workbench/workbench.desktop.main.js'), origWb);

        patchIdeExperiments(ideDir);
        assert.ok(fs.readFileSync(path.join(outDir, 'main.js'), 'utf8').includes('antigravity-experiments-main.js'));
        assert.ok(fs.readFileSync(path.join(outDir, 'main.js'), 'utf8').includes('/*FORK_EXP*/!0'));
        assert.ok(fs.readFileSync(path.join(outDir, 'vs/workbench/workbench.desktop.main.js'), 'utf8').includes('/*FORK_EXP*/!0'));
        assert.ok(!fs.readFileSync(path.join(outDir, 'jetskiAgent/main.js'), 'utf8').includes('r.costSummary=t.costSummary)'));

        unpatchIdeExperiments(ideDir);
        assert.strictEqual(fs.readFileSync(path.join(outDir, 'main.js'), 'utf8'), origIdeMain);
        assert.strictEqual(fs.readFileSync(path.join(outDir, 'jetskiAgent/main.js'), 'utf8'), origJetski);
        assert.strictEqual(fs.readFileSync(path.join(outDir, 'vs/workbench/workbench.desktop.main.js'), 'utf8'), origWb);
    } finally {
        fs.rmSync(tmp, { recursive: true, force: true });
    }
});

test('pricing normalizeModelKey handles Antigravity codenames and Vertex suffixes', () => {
    const tmpHome = fs.mkdtempSync(path.join(os.tmpdir(), 'price-test-'));
    const origHome = process.env.REAL_HOME;
    process.env.REAL_HOME = tmpHome;
    try {
        assert.strictEqual(pricing.normalizeModelKey('gemini-4-hydrogen-high'), 'gemini-4-hydrogen');
        assert.strictEqual(pricing.normalizeModelKey('MODEL_VERTEX_CLAUDE_SONNET_4_5'), 'claude-sonnet-4-5');
        const rate = pricing.resolveModelRate('gemini-4-neon-xhigh');
        assert.strictEqual(rate.input, 2.0);
        assert.strictEqual(rate.output, 12.0);
    } finally {
        if (origHome === undefined) delete process.env.REAL_HOME;
        else process.env.REAL_HOME = origHome;
        fs.rmSync(tmpHome, { recursive: true, force: true });
    }
});

test('sidebar limit, context target patches, multi-account dashboard and fulltext search work', () => {
    const sampleLs = 'M=l[O.id]??!0;I=Math.max(0,5-O.pinnedIds.length);var z=aa?6:30,T=X.items.length>z,(Y?X.items.slice(0,z):X.items);checkpointConfig:r?ic(K.CheckpointConfigSchema,{contextWindow:r}):void 0';
    const sb = mainPatcher.patchSidebarChatLimit(sampleLs);
    assert.strictEqual(sb.count, 2);
    assert.ok(sb.source.includes('__SUITE_SIDEBAR_LIMIT'));
    const ct = mainPatcher.patchContextTarget(sb.source);
    assert.strictEqual(ct.count, 1);
    assert.ok(ct.source.includes('maxTokenLimit:Number(globalThis.__SUITE_CONTEXT_TARGET)'));

    const ideSrc = 'checkpointConfig:h!==void 0?Be(H3r,{maxTokenLimit:h}):void 0';
    const ctIde = mainPatcher.patchContextTarget(ideSrc);
    assert.strictEqual(ctIde.count, 1);
    assert.ok(ctIde.source.includes('__SUITE_CONTEXT_TARGET'));

    const san = catalog.sanitizeExperimentsPayload({ config: { sidebarChatLimit: -1, contextTarget: 500000 } });
    assert.strictEqual(san.config.sidebarChatLimit, -1);
    assert.strictEqual(san.config.contextTarget, 500000);

    const tmpHome = fs.mkdtempSync(path.join(os.tmpdir(), 'usage-live-test-'));
    const origHome = process.env.REAL_HOME;
    process.env.REAL_HOME = tmpHome;
    try {
        const accDir = path.join(tmpHome, '.config', 'antigravity', 'accounts');
        fs.mkdirSync(accDir, { recursive: true });
        fs.writeFileSync(path.join(accDir, 'bindings.json'), JSON.stringify({
            '11111111-1111-1111-1111-111111111111': { email: 'user1@example.com' },
            '22222222-2222-2222-2222-222222222222': { email: 'user2@example.com' },
        }));
        const b1 = path.join(tmpHome, '.gemini', 'antigravity', 'brain', '11111111-1111-1111-1111-111111111111', '.system_generated', 'logs');
        const b2 = path.join(tmpHome, '.gemini', 'antigravity', 'brain', '22222222-2222-2222-2222-222222222222', '.system_generated', 'logs');
        fs.mkdirSync(b1, { recursive: true });
        fs.mkdirSync(b2, { recursive: true });
        const nowIso = new Date().toISOString();
        const t1Iso = new Date(Date.now() - 60000).toISOString();
        fs.writeFileSync(path.join(b1, 'transcript.jsonl'), [
            JSON.stringify({ role: 'user', user_input: 'debug nginx upstream', timestamp: t1Iso }),
            JSON.stringify({ step_index: 1, model: 'claude-sonnet-4-6', input_tokens: 1000, cache_read_tokens: 9000, output_tokens: 500, timestamp: t1Iso }),
            JSON.stringify({ step_index: 2, model: 'claude-sonnet-4-6', input_tokens: 8000, cache_read_tokens: 2000, output_tokens: 400, timestamp: nowIso }),
        ].join('\n'));
        fs.writeFileSync(path.join(b2, 'transcript.jsonl'), [
            JSON.stringify({ role: 'user', user_input: 'deploy redis cluster', timestamp: nowIso }),
            JSON.stringify({ step_index: 1, model: 'gemini-4-hydrogen', input_tokens: 5000, cache_read_tokens: 5000, output_tokens: 1000, timestamp: nowIso }),
        ].join('\n'));

        const usageLive = require(path.join(ROOT, 'bin/lib/patch/router/usage_live.js'));
        usageLive.recordStreamStart('11111111-1111-1111-1111-111111111111', 'claude-sonnet-4-6');
        usageLive.recordStreamUsageChunk('11111111-1111-1111-1111-111111111111', '{"candidatesTokenCount":120,"promptTokenCount":5000,"cachedContentTokenCount":4000}', 'claude-sonnet-4-6');
        usageLive.recordStreamEnd('11111111-1111-1111-1111-111111111111');

        const active = usageLive.getActiveCascadeUsage('11111111-1111-1111-1111-111111111111');
        assert.strictEqual(active.accountEmail, 'user1@example.com');
        assert.strictEqual(active.cacheAnomalies.length, 1);
        assert.ok(active.ttftMs > 0);

        const dashAll = usageLive.getMultiAccountDashboard({ range: 'all', account: 'all' });
        assert.strictEqual(dashAll.accounts.length, 2);
        assert.strictEqual(dashAll.totals.anomalies, 1);
        const dashOne = usageLive.getMultiAccountDashboard({ range: 'all', account: 'user2@example.com' });
        assert.strictEqual(dashOne.totals.sessions, 1);

        const searchRes = usageLive.searchAllTranscripts('nginx upstream', 10);
        assert.strictEqual(searchRes.results.length, 1);
        assert.strictEqual(searchRes.results[0].accountEmail, 'user1@example.com');
    } finally {
        if (origHome === undefined) delete process.env.REAL_HOME;
        else process.env.REAL_HOME = origHome;
        fs.rmSync(tmpHome, { recursive: true, force: true });
    }
});
