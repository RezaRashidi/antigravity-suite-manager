// Multi-Account Patcher: Language Server Endpoint Patch
const fs = require('fs');
const path = require('path');

function patchLanguageServer(distDir) {
    const lsPath = path.join(distDir, 'languageServer.js');
    if (!fs.existsSync(lsPath)) return;
    let code = fs.readFileSync(lsPath, 'utf8');
    if (!code.includes("require('./multi_account_router.js')")) {
        code = "try { require('./multi_account_router.js').startMultiAccountRouter(); } catch (_) {}\n" + code;
    }
    code = code.replace(
        /['"]--cloud_code_endpoint['"]\s*,\s*['"]https:\/\/(?:daily-)?cloudcode-pa\.googleapis\.com['"]/g,
        "'--cloud_code_endpoint',\n            (process.env.ANTIGRAVITY_CLOUD_CODE_ENDPOINT || 'http://127.0.0.1:41999')"
    );
    if (!code.includes('/* AGY_AICODE_ENDPOINT_START */')) {
        code = code.replace(
            /(env\['ANTIGRAVITY_SERVER_CSRF_TOKEN'\]\s*=\s*csrf;)/,
            "$1\n        /* AGY_AICODE_ENDPOINT_START */\n        if (!env['AICODE_ENDPOINT_URL']) env['AICODE_ENDPOINT_URL'] = (process.env.ANTIGRAVITY_CLOUD_CODE_ENDPOINT || 'http://127.0.0.1:41999');\n        /* AGY_AICODE_ENDPOINT_END */"
        );
    }
    fs.writeFileSync(lsPath, code, 'utf8');
}

function unpatchLanguageServer(distDir) {
    const lsPath = path.join(distDir, 'languageServer.js');
    if (!fs.existsSync(lsPath)) return;
    let code = fs.readFileSync(lsPath, 'utf8');
    code = code.replace("try { require('./multi_account_router.js').startMultiAccountRouter(); } catch (_) {}\n", "");
    code = code.replace(/[ \t]*\/\* AGY_AICODE_ENDPOINT_START \*\/[\s\S]*?\/\* AGY_AICODE_ENDPOINT_END \*\/\r?\n?/g, "");
    code = code.replace(
        /\(process\.env\.ANTIGRAVITY_CLOUD_CODE_ENDPOINT\s*\|\|\s*['"]http:\/\/127\.0\.0\.1:41999['"]\)/g,
        "'https://daily-cloudcode-pa.googleapis.com'"
    );
    fs.writeFileSync(lsPath, code, 'utf8');
}

module.exports = { patchLanguageServer, unpatchLanguageServer };
