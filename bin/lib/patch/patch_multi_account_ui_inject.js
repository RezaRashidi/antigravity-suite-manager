// Multi-Account Patcher: UI and Styles Injection in utils.js
const fs = require('fs');
const path = require('path');

function copyFolderRecursiveSync(source, target) {
    if (!fs.existsSync(target)) fs.mkdirSync(target, { recursive: true });
    if (fs.lstatSync(source).isDirectory()) {
        for (const file of fs.readdirSync(source)) {
            const curSource = path.join(source, file);
            if (fs.lstatSync(curSource).isDirectory()) copyFolderRecursiveSync(curSource, path.join(target, file));
            else fs.copyFileSync(curSource, path.join(target, file));
        }
    }
}

function copySubsystemFiles(distDir) {
    const patchDir = path.dirname(__filename);
    for (const f of ['multi_account_router.js', 'multi_account_ui.js']) {
        const src = path.join(patchDir, f);
        if (fs.existsSync(src)) {
            fs.copyFileSync(src, path.join(distDir, f));
            if (f === 'multi_account_router.js') {
                fs.copyFileSync(src, path.join(distDir, 'multi_account_router.cjs'));
            }
        }
    }
    for (const d of ['router', 'ui']) {
        const src = path.join(patchDir, d);
        if (fs.existsSync(src)) copyFolderRecursiveSync(src, path.join(distDir, d));
    }
    const routerPkg = path.join(distDir, 'router', 'package.json');
    try {
        fs.writeFileSync(routerPkg, JSON.stringify({ type: 'commonjs' }, null, 2), 'utf8');
    } catch (_) {}
}

function unpatchUiInjection(distDir) {
    const utilsPath = path.join(distDir, 'utils.js');
    if (fs.existsSync(utilsPath)) {
        let code = fs.readFileSync(utilsPath, 'utf8');
        code = code.replace(/\/\* MULTI_ACCOUNT_UI_START \*\/[\s\S]*?\/\* MULTI_ACCOUNT_UI_END \*\//g, '');
        code = code.replace(/try\s*\{\s*const (?:cssPath|uiCodePath)[\s\S]*?console\.error\('\[MultiAccount\] UI injection error:'[^\n]*\n\s*\}/g, '');
        fs.writeFileSync(utilsPath, code, 'utf8');
    }
    for (const f of ['multi_account_router.js', 'multi_account_router.cjs', 'multi_account_ui.js']) {
        const p = path.join(distDir, f);
        if (fs.existsSync(p)) fs.unlinkSync(p);
    }
    for (const d of ['router', 'ui']) {
        const p = path.join(distDir, d);
        if (fs.existsSync(p)) fs.rmSync(p, { recursive: true, force: true });
    }
}

function patchUiInjection(distDir) {
    unpatchUiInjection(distDir);
    copySubsystemFiles(distDir);
    const utilsPath = path.join(distDir, 'utils.js');
    if (!fs.existsSync(utilsPath)) return;
    let code = fs.readFileSync(utilsPath, 'utf8');
    if (!code.includes('MULTI_ACCOUNT_UI_START')) {
        const snippet = `/* MULTI_ACCOUNT_UI_START */
    const __injectMultiAccountUI = () => {
        try {
            const cssPath = require('path').join(__dirname, 'ui', 'styles.css');
            if (require('fs').existsSync(cssPath)) void win.webContents.insertCSS(require('fs').readFileSync(cssPath, 'utf8'));
            for (const s of ['ui/flyout.js', 'ui/mount.js', 'multi_account_ui.js']) {
                const sp = require('path').join(__dirname, s);
                if (require('fs').existsSync(sp)) void win.webContents.executeJavaScript(require('fs').readFileSync(sp, 'utf8')).catch(e => console.error('[MultiAccount] ' + s + ' error:', e.message));
            }
        } catch (e) { console.error('[MultiAccount] UI injection error:', e.message); }
    };
    win.webContents.on('dom-ready', __injectMultiAccountUI);
    win.webContents.on('did-finish-load', __injectMultiAccountUI);
    /* MULTI_ACCOUNT_UI_END */`;
        code = code.replace("win.webContents.on('dom-ready', () => {", snippet + "\n    win.webContents.on('dom-ready', () => {");
        fs.writeFileSync(utilsPath, code, 'utf8');
    }
}

module.exports = { patchUiInjection, unpatchUiInjection };
