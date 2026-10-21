// Antigravity IDE Multi-Account Subsystem Patcher
const fs = require('fs');
const path = require('path');
const { patchUiInjection, unpatchUiInjection } = require('./patch_multi_account_ui_inject');

function copyFileSafe(src, dst) {
    if (fs.existsSync(src)) {
        fs.mkdirSync(path.dirname(dst), { recursive: true });
        fs.copyFileSync(src, dst);
    }
}

function patchIdeLanguageServer(ideDir) {
    const lsScript = path.join(ideDir, 'resources/app/extensions/antigravity/bin/language_server_linux_x64');
    if (!fs.existsSync(lsScript)) return;
    let code = fs.readFileSync(lsScript, 'utf8');
    if (!code.includes('PROXY_ENDPOINT')) {
        const patchBlock = 'PROXY_ENDPOINT="${ANTIGRAVITY_CLOUD_CODE_ENDPOINT:-http://127.0.0.1:41999}"\n';
        code = code.replace('ARGS=()', patchBlock + 'ARGS=()');
        code = code.replace(/--cloud_code_endpoint=https:\/\/daily-cloudcode-pa\.googleapis\.com/g, '--cloud_code_endpoint=${PROXY_ENDPOINT}');
        code = code.replace(/"https:\/\/daily-cloudcode-pa\.googleapis\.com"/g, '"${PROXY_ENDPOINT}"');
        fs.writeFileSync(lsScript, code, { mode: 0o755 });
    }
}

function unpatchIdeLanguageServer(ideDir) {
    const lsScript = path.join(ideDir, 'resources/app/extensions/antigravity/bin/language_server_linux_x64');
    if (!fs.existsSync(lsScript)) return;
    let code = fs.readFileSync(lsScript, 'utf8');
    code = code.replace(/PROXY_ENDPOINT="[^"]+"\n/g, '');
    code = code.replace(/--cloud_code_endpoint=\$\{PROXY_ENDPOINT\}/g, '--cloud_code_endpoint=https://daily-cloudcode-pa.googleapis.com');
    code = code.replace(/"\$\{PROXY_ENDPOINT\}"/g, '"https://daily-cloudcode-pa.googleapis.com"');
    fs.writeFileSync(lsScript, code, { mode: 0o755 });
}

function patchIdeMultiAccount(ideDir) {
    console.log('[Patch] Applying Multi-Account selector to Antigravity IDE in:', ideDir);
    const outDir = path.join(ideDir, 'resources/app/out');
    if (!fs.existsSync(outDir)) return;

    patchUiInjection(outDir);
    const hookSrc = path.join(__dirname, 'antigravity-multi-account-ide.js');
    copyFileSafe(hookSrc, path.join(outDir, 'antigravity-multi-account-ide.js'));

    const mainJs = path.join(outDir, 'main.js');
    if (fs.existsSync(mainJs)) {
        let code = fs.readFileSync(mainJs, 'utf8');
        const imp = "import './antigravity-multi-account-ide.js';\n";
        if (!code.includes(imp)) {
            code = imp + code;
            fs.writeFileSync(mainJs, code, 'utf8');
        }
    }
    patchIdeLanguageServer(ideDir);
    const marker = path.join(outDir, 'antigravity_ide_selector_patch.marker');
    try { fs.writeFileSync(marker, 'ANTIGRAVITY_SUITE_IDE_SELECTOR_PATCH_V1\n', 'utf8'); } catch (_) {}
}

function unpatchIdeMultiAccount(ideDir) {
    console.log('[Patch] Removing Multi-Account selector from Antigravity IDE in:', ideDir);
    const outDir = path.join(ideDir, 'resources/app/out');
    if (!fs.existsSync(outDir)) return;

    const mainJs = path.join(outDir, 'main.js');
    if (fs.existsSync(mainJs)) {
        let code = fs.readFileSync(mainJs, 'utf8');
        code = code.replace("import './antigravity-multi-account-ide.js';\n", '');
        fs.writeFileSync(mainJs, code, 'utf8');
    }
    unpatchUiInjection(outDir);
    const hookDst = path.join(outDir, 'antigravity-multi-account-ide.js');
    if (fs.existsSync(hookDst)) fs.unlinkSync(hookDst);
    unpatchIdeLanguageServer(ideDir);

    const marker = path.join(outDir, 'antigravity_ide_selector_patch.marker');
    if (fs.existsSync(marker)) fs.unlinkSync(marker);
}

module.exports = { patchIdeMultiAccount, unpatchIdeMultiAccount };
