#!/usr/bin/env node
/**
 * Antigravity Suite Internal RTL Patcher (App ASAR unpacked dir & IDE resources/app)
 * Zero external dependencies, preserves Multi-Account UI hooks during migration/unpatch.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const RTL_START = '/* ANTIGRAVITY_SUITE_RTL_START */';
const RTL_END = '/* ANTIGRAVITY_SUITE_RTL_END */';
const LEGACY_START = '/* ANTIGRAVITY RTL PATCH */';
const LEGACY_END = '/* END ANTIGRAVITY RTL PATCH */';
const MA_START = '/* MULTI_ACCOUNT_UI_START */';
const MA_END = '/* MULTI_ACCOUNT_UI_END */';
const HOOK_IMPORT = "import './antigravity-rtl-main.js';";
const FONT_SRC_DATA = /font-src[^;]*\bdata:/;

function stripRtlFromUtils(code) {
    let out = code;
    let preservedMa = '';

    // Extract legacy antigravity-rtl block while preserving any nested MULTI_ACCOUNT_UI block
    const legRe = /\/\* ANTIGRAVITY RTL PATCH \*\/[\s\S]*?\/\* END ANTIGRAVITY RTL PATCH \*\//g;
    out = out.replace(legRe, (block) => {
        const maMatch = block.match(/\/\* MULTI_ACCOUNT_UI_START \*\/[\s\S]*?\/\* MULTI_ACCOUNT_UI_END \*\//);
        if (maMatch) preservedMa = maMatch[0];
        const hasLoadUrl = /(?:await|void)\s+win\.loadURL\(url\);/.test(block);
        const parts = [];
        if (preservedMa) parts.push(preservedMa);
        if (hasLoadUrl) parts.push('await win.loadURL(url);');
        return parts.join('\n    ');
    });

    // Strip internal suite RTL block
    out = out.replace(/[ \t]*\/\* ANTIGRAVITY_SUITE_RTL_START \*\/[\s\S]*?\/\* ANTIGRAVITY_SUITE_RTL_END \*\/\r?\n?/g, '');
    return out;
}

function patchApp(unpackedDir) {
    const distDir = path.join(unpackedDir, 'dist');
    const utilsPath = path.join(distDir, 'utils.js');
    if (!fs.existsSync(utilsPath)) {
        throw new Error(`dist/utils.js not found in ${unpackedDir}`);
    }

    const rtlSrcDir = __dirname;
    const rtlDestDir = path.join(distDir, 'rtl');
    fs.mkdirSync(rtlDestDir, { recursive: true });

    for (const file of ['rtl_engine.js', 'rtl_styles.js', 'rtl_ui_app.js', 'rtl_app_hook.js', 'Vazirmatn-Variable.woff2']) {
        fs.copyFileSync(path.join(rtlSrcDir, file), path.join(rtlDestDir, file));
    }

    // Remove legacy root font copy if present
    fs.rmSync(path.join(distDir, 'Vazirmatn-Variable.woff2'), { force: true });

    let code = stripRtlFromUtils(fs.readFileSync(utilsPath, 'utf8'));

    const hookSnippet =
        `    ${RTL_START}\n` +
        `    try { require('./rtl/rtl_app_hook.js')(win); } catch (e) { console.error('[Antigravity RTL] Hook error:', e.message); }\n` +
        `    ${RTL_END}`;

    const anchorRe = /([ \t]*(?:await|void)\s+win\.loadURL\(url\);)/;
    if (!anchorRe.test(code)) {
        throw new Error('Could not find win.loadURL(url) anchor in dist/utils.js');
    }

    code = code.replace(anchorRe, `${hookSnippet}\n$1`);
    fs.writeFileSync(utilsPath, code, 'utf8');
    fs.writeFileSync(path.join(distDir, 'antigravity_rtl_patch.marker'), 'ANTIGRAVITY_SUITE_RTL_PATCH_V1\n', 'utf8');
}

function unpatchApp(unpackedDir) {
    const distDir = path.join(unpackedDir, 'dist');
    const utilsPath = path.join(distDir, 'utils.js');
    if (fs.existsSync(utilsPath)) {
        const cleaned = stripRtlFromUtils(fs.readFileSync(utilsPath, 'utf8'));
        fs.writeFileSync(utilsPath, cleaned, 'utf8');
    }
    fs.rmSync(path.join(distDir, 'rtl'), { recursive: true, force: true });
    fs.rmSync(path.join(distDir, 'Vazirmatn-Variable.woff2'), { force: true });
    fs.rmSync(path.join(distDir, 'antigravity_rtl_patch.marker'), { force: true });
}

function resolveIdeAppDir(inputPath) {
    if (!inputPath || !fs.existsSync(inputPath)) return null;
    if (fs.existsSync(path.join(inputPath, 'out', 'main.js'))) return inputPath;
    const std = path.join(inputPath, 'resources', 'app');
    if (fs.existsSync(path.join(std, 'out', 'main.js'))) return std;
    const mac = path.join(inputPath, 'Contents', 'Resources', 'app');
    if (fs.existsSync(path.join(mac, 'out', 'main.js'))) return mac;
    return null;
}

function getIdePaths(ideAppDir) {
    const outDir = path.join(ideAppDir, 'out');
    const wbDir = path.join(outDir, 'vs', 'code', 'electron-browser', 'workbench');
    const mainJsPath = path.join(outDir, 'main.js');
    const workbenchHtml = path.join(wbDir, 'workbench.html');
    const jetskiHtml = path.join(wbDir, 'workbench-jetski-agent.html');
    return {
        outDir,
        mainJsPath,
        workbenchHtml,
        jetskiHtml,
        mainJsBak: mainJsPath + '.rtl-bak',
        workbenchHtmlBak: workbenchHtml + '.rtl-bak',
        jetskiHtmlBak: jetskiHtml + '.rtl-bak'
    };
}

function buildIdeClientBundle(rtlSrcDir) {
    const engine = fs.readFileSync(path.join(rtlSrcDir, 'rtl_engine.js'), 'utf8');
    const styles = fs.readFileSync(path.join(rtlSrcDir, 'rtl_styles.js'), 'utf8');
    const uiIde = fs.readFileSync(path.join(rtlSrcDir, 'rtl_ui_ide.js'), 'utf8');
    return (
        `${engine}\n;\n${styles}\n;\n${uiIde}\n;\n` +
        `(function(){ if (window.__antigravityMountIdeRtl) window.__antigravityMountIdeRtl('__FONT_BASE64__', __RTL_CONFIG__, __SYSTEM_FONTS__); })();\n`
    );
}

function patchIde(targetPath) {
    const appDir = resolveIdeAppDir(targetPath);
    if (!appDir) throw new Error(`Invalid Antigravity IDE directory: ${targetPath}`);
    const p = getIdePaths(appDir);

    let mainCode = fs.readFileSync(p.mainJsPath, 'utf8');
    if (!mainCode.includes(HOOK_IMPORT)) {
        fs.copyFileSync(p.mainJsPath, p.mainJsBak);
    }

    for (const [file, bak] of [[p.workbenchHtml, p.workbenchHtmlBak], [p.jetskiHtml, p.jetskiHtmlBak]]) {
        if (fs.existsSync(file) && !FONT_SRC_DATA.test(fs.readFileSync(file, 'utf8'))) {
            fs.copyFileSync(file, bak);
        }
    }

    fs.copyFileSync(path.join(__dirname, 'Vazirmatn-Variable.woff2'), path.join(p.outDir, 'Vazirmatn-Variable.woff2'));
    fs.writeFileSync(path.join(p.outDir, 'antigravity-rtl-client.js'), buildIdeClientBundle(__dirname), 'utf8');
    fs.copyFileSync(path.join(__dirname, 'rtl_ide_main.js'), path.join(p.outDir, 'antigravity-rtl-main.js'));

    if (!mainCode.includes(HOOK_IMPORT)) {
        fs.writeFileSync(p.mainJsPath, HOOK_IMPORT + '\n' + mainCode, 'utf8');
    }

    for (const htmlFile of [p.workbenchHtml, p.jetskiHtml]) {
        if (!fs.existsSync(htmlFile)) continue;
        let content = fs.readFileSync(htmlFile, 'utf8');
        if (content.includes('font-src') && !FONT_SRC_DATA.test(content)) {
            content = content.replace(/(font-src[\s\S]*?'self')/i, '$1\n\t\t\t\t\tdata:');
            fs.writeFileSync(htmlFile, content, 'utf8');
        }
    }

    fs.writeFileSync(path.join(p.outDir, 'antigravity_rtl_patch.marker'), 'ANTIGRAVITY_SUITE_RTL_PATCH_V1\n', 'utf8');
}

function unpatchIde(targetPath) {
    const appDir = resolveIdeAppDir(targetPath);
    if (!appDir) return;
    const p = getIdePaths(appDir);

    if (fs.existsSync(p.mainJsBak)) {
        fs.copyFileSync(p.mainJsBak, p.mainJsPath);
        fs.rmSync(p.mainJsBak, { force: true });
    } else if (fs.existsSync(p.mainJsPath)) {
        let code = fs.readFileSync(p.mainJsPath, 'utf8');
        if (code.includes(HOOK_IMPORT)) {
            code = code.replace(HOOK_IMPORT + '\n', '').replace(HOOK_IMPORT, '');
            fs.writeFileSync(p.mainJsPath, code, 'utf8');
        }
    }

    for (const [file, bak] of [[p.workbenchHtml, p.workbenchHtmlBak], [p.jetskiHtml, p.jetskiHtmlBak]]) {
        if (fs.existsSync(bak)) {
            fs.copyFileSync(bak, file);
            fs.rmSync(bak, { force: true });
        }
    }

    for (const f of [
        path.join(p.outDir, 'antigravity-rtl-main.js'),
        path.join(p.outDir, 'antigravity-rtl-client.js'),
        path.join(p.outDir, 'Vazirmatn-Variable.woff2'),
        path.join(p.outDir, 'antigravity_rtl_patch.marker')
    ]) {
        fs.rmSync(f, { force: true });
    }
}

if (require.main === module) {
    const args = process.argv.slice(2);
    const isUnpatch = args.includes('--unpatch');
    const isApp = args.includes('--app');
    const isIde = args.includes('--ide');
    const target = args.find((a) => !a.startsWith('-'));

    if (!target || (!isApp && !isIde)) {
        console.error('Usage: patch_rtl.js <--app|--ide> [--unpatch] <target_dir>');
        process.exit(1);
    }

    try {
        if (isApp) {
            if (isUnpatch) unpatchApp(target);
            else patchApp(target);
        } else if (isIde) {
            if (isUnpatch) unpatchIde(target);
            else patchIde(target);
        }
        console.log('OK');
    } catch (err) {
        console.error(err && err.message ? err.message : String(err));
        process.exit(1);
    }
}

module.exports = {
    stripRtlFromUtils,
    patchApp,
    unpatchApp,
    patchIde,
    unpatchIde,
    buildIdeClientBundle
};
