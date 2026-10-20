// Multi-Account Patcher: Language Server Endpoint Patch
const fs = require('fs');
const path = require('path');

function patchLanguageServer(distDir) {
    const lsPath = path.join(distDir, 'languageServer.js');
    if (!fs.existsSync(lsPath)) return;
    let code = fs.readFileSync(lsPath, 'utf8');
    if (!code.includes("require('./multi_account_router')")) {
        code = "try { require('./multi_account_router').startMultiAccountRouter(); } catch (_) {}\n" + code;
    }
    code = code.replace(
        "'--cloud_code_endpoint',\n            'https://daily-cloudcode-pa.googleapis.com'",
        "'--cloud_code_endpoint',\n            (process.env.ANTIGRAVITY_CLOUD_CODE_ENDPOINT || 'http://127.0.0.1:41999')"
    );
    fs.writeFileSync(lsPath, code, 'utf8');
}

function unpatchLanguageServer(distDir) {
    const lsPath = path.join(distDir, 'languageServer.js');
    if (!fs.existsSync(lsPath)) return;
    let code = fs.readFileSync(lsPath, 'utf8');
    code = code.replace("try { require('./multi_account_router').startMultiAccountRouter(); } catch (_) {}\n", "");
    code = code.replace(
        "(process.env.ANTIGRAVITY_CLOUD_CODE_ENDPOINT || 'http://127.0.0.1:41999')",
        "'https://daily-cloudcode-pa.googleapis.com'"
    );
    fs.writeFileSync(lsPath, code, 'utf8');
}

module.exports = { patchLanguageServer, unpatchLanguageServer };
