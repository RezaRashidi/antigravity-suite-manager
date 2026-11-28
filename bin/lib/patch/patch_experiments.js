'use strict';

/**
 * Antigravity Suite Unified Experiments, Conversation Forking, DevUI Cost & Open-IDE Patcher (App & IDE).
 */

const fs = require('fs');
const path = require('path');
const { patchMainJs, replaceCostDollarIcon, restoreCostDollarIcon } = require('./experiments/main_js_patcher.js');
const {
    patchAppConversationForking,
    unpatchAppConversationForking,
    patchIdeConversationForking,
    unpatchIdeConversationForking,
} = require('./patch_conversation_forking.js');
const { patchAppOpenIde, unpatchAppOpenIde } = require('./patch_open_ide.js');

const EXP_APP_START = '/* ANTIGRAVITY_SUITE_EXPERIMENTS_START */';
const EXP_APP_END = '/* ANTIGRAVITY_SUITE_EXPERIMENTS_END */';
const DEV_UI_START = '/* SUITE_DEV_UI_START */';
const DEV_UI_END = '/* SUITE_DEV_UI_END */';
const DEV_UI_ENV_START = '/* SUITE_DEV_UI_ENV_START */';
const DEV_UI_ENV_END = '/* SUITE_DEV_UI_ENV_END */';
const IDE_HOOK_IMPORT = "import './antigravity-experiments-main.js';\n";

function copyFolderSync(src, dst) {
    fs.mkdirSync(dst, { recursive: true });
    for (const f of fs.readdirSync(src)) {
        const s = path.join(src, f);
        const d = path.join(dst, f);
        if (fs.lstatSync(s).isDirectory()) copyFolderSync(s, d);
        else fs.copyFileSync(s, d);
    }
}

function stripAppExperimentsHooks(distDir) {
    const utilsPath = path.join(distDir, 'utils.js');
    if (fs.existsSync(utilsPath)) {
        let code = fs.readFileSync(utilsPath, 'utf8');
        code = code.replace(/[ \t]*\/\* ANTIGRAVITY_SUITE_EXPERIMENTS_START \*\/[\s\S]*?\/\* ANTIGRAVITY_SUITE_EXPERIMENTS_END \*\/\r?\n?/g, '');
        fs.writeFileSync(utilsPath, code, 'utf8');
    }

    const lsPath = path.join(distDir, 'languageServer.js');
    if (fs.existsSync(lsPath)) {
        let code = fs.readFileSync(lsPath, 'utf8');
        code = code.replace(/[ \t]*\/\* SUITE_DEV_UI_START \*\/[\s\S]*?\/\* SUITE_DEV_UI_END \*\/\r?\n?/g, '');
        code = code.replace(/[ \t]*\/\* SUITE_DEV_UI_ENV_START \*\/[\s\S]*?\/\* SUITE_DEV_UI_ENV_END \*\/\r?\n?/g, '');
        fs.writeFileSync(lsPath, code, 'utf8');
    }
}

function patchAppExperiments(unpackedDir) {
    const distDir = path.join(unpackedDir, 'dist');
    const utilsPath = path.join(distDir, 'utils.js');
    if (!fs.existsSync(utilsPath)) {
        throw new Error(`dist/utils.js not found in ${unpackedDir}`);
    }

    stripAppExperimentsHooks(distDir);

    const patchDir = __dirname;
    fs.copyFileSync(path.join(patchDir, 'experiments_catalog.js'), path.join(distDir, 'experiments_catalog.js'));
    copyFolderSync(path.join(patchDir, 'experiments'), path.join(distDir, 'experiments'));
    copyFolderSync(path.join(patchDir, 'router'), path.join(distDir, 'router'));

    // 1. Inject UI & console persistence hook into dist/utils.js before win.loadURL(url)
    let utilsCode = fs.readFileSync(utilsPath, 'utf8');
    const hookSnippet =
        `    ${EXP_APP_START}\n` +
        `    try { require('./experiments/experiments_app_hook.js')(win); } catch (e) { console.error('[Suite Experiments] Hook error:', e.message); }\n` +
        `    ${EXP_APP_END}`;
    const anchorRe = /([ \t]*(?:await|void)\s+win\.loadURL\(url\);)/;
    if (!anchorRe.test(utilsCode)) {
        throw new Error('Could not find win.loadURL(url) anchor in dist/utils.js');
    }
    utilsCode = utilsCode.replace(anchorRe, `${hookSnippet}\n$1`);
    fs.writeFileSync(utilsPath, utilsCode, 'utf8');

    // 2. Hook in-process AGY_DEV_UI_URL server into dist/languageServer.js
    const lsPath = path.join(distDir, 'languageServer.js');
    if (fs.existsSync(lsPath)) {
        let lsCode = fs.readFileSync(lsPath, 'utf8');
        const lsWaitAnchor = /([ \t]*const loginShellEnv = await shellEnvReads\.take\(\);)/;
        if (lsWaitAnchor.test(lsCode)) {
            const initSnippet =
                `    ${DEV_UI_START}\n` +
                `    const __suiteDevUiUrl = (!options?.wsl && !process.env.AGY_DEV_UI_URL) ? await require('./experiments/dev_ui_server.js').ensureDevUiServer(exports.LS_BINARY) : null;\n` +
                `    ${DEV_UI_END}`;
            lsCode = lsCode.replace(lsWaitAnchor, `$1\n${initSnippet}`);
        }
        const envAnchor = /(env\['ANTIGRAVITY_SERVER_CSRF_TOKEN'\]\s*=\s*csrf;)/;
        if (envAnchor.test(lsCode)) {
            const envSnippet =
                `        ${DEV_UI_ENV_START}\n` +
                `        if (typeof __suiteDevUiUrl === 'string' && __suiteDevUiUrl) env['AGY_DEV_UI_URL'] = __suiteDevUiUrl;\n` +
                `        ${DEV_UI_ENV_END}`;
            lsCode = lsCode.replace(envAnchor, `$1\n${envSnippet}`);
        }
        fs.writeFileSync(lsPath, lsCode, 'utf8');
    }

    // 0. Fold Conversation Forking (--dev_mode cleanup + preload flags) & Native Open in IDE titlebar button
    patchAppConversationForking(unpackedDir);
    patchAppOpenIde(unpackedDir);

    fs.writeFileSync(path.join(distDir, 'antigravity_experiments_patch.marker'), 'ANTIGRAVITY_SUITE_EXPERIMENTS_PATCH_V1\n', 'utf8');
}

function unpatchAppExperiments(unpackedDir) {
    const distDir = path.join(unpackedDir, 'dist');
    unpatchAppOpenIde(unpackedDir);
    unpatchAppConversationForking(unpackedDir);
    stripAppExperimentsHooks(distDir);
    fs.rmSync(path.join(distDir, 'experiments'), { recursive: true, force: true });
    fs.rmSync(path.join(distDir, 'antigravity_experiments_patch.marker'), { force: true });
}

function resolveIdeAppDir(inputPath) {
    if (!inputPath || !fs.existsSync(inputPath)) return null;
    if (fs.existsSync(path.join(inputPath, 'out', 'main.js'))) return inputPath;
    const std = path.join(inputPath, 'resources', 'app');
    if (fs.existsSync(path.join(std, 'out', 'main.js'))) return std;
    return null;
}

function patchIdeExperiments(ideDir) {
    const ideAppDir = resolveIdeAppDir(ideDir);
    if (!ideAppDir) throw new Error(`IDE out/main.js not found under ${ideDir}`);
    const outDir = path.join(ideAppDir, 'out');
    const patchDir = __dirname;

    fs.copyFileSync(path.join(patchDir, 'experiments_catalog.js'), path.join(outDir, 'experiments_catalog.js'));
    fs.copyFileSync(path.join(patchDir, 'experiments', 'experiments_ui_ide.js'), path.join(outDir, 'experiments_ui_ide.js'));
    fs.copyFileSync(path.join(patchDir, 'experiments', 'suite_features_ui.js'), path.join(outDir, 'suite_features_ui.js'));
    fs.copyFileSync(path.join(patchDir, 'experiments', 'experiments_ide_main.js'), path.join(outDir, 'antigravity-experiments-main.js'));
    fs.copyFileSync(path.join(patchDir, 'experiments', 'relaunch_helper.js'), path.join(outDir, 'relaunch_helper.js'));

    const mainJsPath = path.join(outDir, 'main.js');
    let mainCode = fs.readFileSync(mainJsPath, 'utf8');
    if (!mainCode.includes('antigravity-experiments-main.js')) {
        mainCode = IDE_HOOK_IMPORT + mainCode;
        fs.writeFileSync(mainJsPath, mainCode, 'utf8');
    }

    // Reprice native .costSummary, replace circular dollar icon, and apply context target in IDE jetskiAgent/main.js
    const jetskiMain = path.join(outDir, 'jetskiAgent', 'main.js');
    const jetskiBak = `${jetskiMain}.exp-bak`;
    if (fs.existsSync(jetskiMain)) {
        const cur = fs.readFileSync(jetskiMain, 'utf8');
        const baseSource = fs.existsSync(jetskiBak) ? fs.readFileSync(jetskiBak, 'utf8') : cur;
        if (!fs.existsSync(jetskiBak)) fs.copyFileSync(jetskiMain, jetskiBak);
        let pricingMod = null;
        try { pricingMod = require('./router/pricing.js'); } catch (_) {}
        const table = pricingMod ? pricingMod.buildCompactTable(pricingMod.readCachedPrices()) : {};
        const patched = patchMainJs(baseSource, {
            enableIndicator: false,
            priceTable: table,
            replaceCostIcon: true,
            enableSidebarLimit: true,
            enableContextTarget: true,
        });
        if (patched.report.costs.ok || patched.report.costIcon.count > 0 || patched.report.contextTarget.count > 0) {
            fs.writeFileSync(jetskiMain, patched.source, 'utf8');
        }
    }

    // Replace circular dollar icon in-place in IDE workbench without clobbering selector/fork patches
    const wbMain = path.join(outDir, 'vs', 'workbench', 'workbench.desktop.main.js');
    if (fs.existsSync(wbMain)) {
        const iconRes = replaceCostDollarIcon(fs.readFileSync(wbMain, 'utf8'));
        if (iconRes.count > 0) fs.writeFileSync(wbMain, iconRes.source, 'utf8');
    }

    // Apply IDE Conversation Forking unlock alongside experiments (only when IDE root exists)
    const rootIdeDir = path.resolve(ideAppDir, '..', '..');
    patchIdeConversationForking(rootIdeDir);

    fs.writeFileSync(path.join(outDir, 'antigravity_ide_experiments_patch.marker'), 'ANTIGRAVITY_SUITE_IDE_EXPERIMENTS_PATCH_V1\n', 'utf8');
}

function unpatchIdeExperiments(ideDir) {
    const ideAppDir = resolveIdeAppDir(ideDir);
    if (!ideAppDir) return;
    const outDir = path.join(ideAppDir, 'out');
    const rootIdeDir = path.resolve(ideAppDir, '..', '..');

    unpatchIdeConversationForking(rootIdeDir);

    const mainJsPath = path.join(outDir, 'main.js');
    if (fs.existsSync(mainJsPath)) {
        let code = fs.readFileSync(mainJsPath, 'utf8');
        code = code.replace(IDE_HOOK_IMPORT, '');
        fs.writeFileSync(mainJsPath, code, 'utf8');
    }

    const jetskiMain = path.join(outDir, 'jetskiAgent', 'main.js');
    const jetskiBak = `${jetskiMain}.exp-bak`;
    if (fs.existsSync(jetskiBak)) {
        fs.copyFileSync(jetskiBak, jetskiMain);
        fs.unlinkSync(jetskiBak);
    }

    const wbMain = path.join(outDir, 'vs', 'workbench', 'workbench.desktop.main.js');
    const wbBak = `${wbMain}.exp-bak`;
    if (fs.existsSync(wbBak)) {
        fs.copyFileSync(wbBak, wbMain);
        fs.unlinkSync(wbBak);
    } else if (fs.existsSync(wbMain)) {
        const res = restoreCostDollarIcon(fs.readFileSync(wbMain, 'utf8'));
        if (res.count > 0) fs.writeFileSync(wbMain, res.source, 'utf8');
    }

    for (const f of ['experiments_ui_ide.js', 'suite_features_ui.js', 'antigravity-experiments-main.js', 'relaunch_helper.js', 'antigravity_ide_experiments_patch.marker']) {
        fs.rmSync(path.join(outDir, f), { force: true });
    }
}

module.exports = {
    patchAppExperiments,
    unpatchAppExperiments,
    patchIdeExperiments,
    unpatchIdeExperiments,
};
