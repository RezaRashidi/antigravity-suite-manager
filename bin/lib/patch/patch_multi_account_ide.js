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

function isElfBinary(filePath) {
    try {
        if (!fs.existsSync(filePath)) return false;
        const stat = fs.statSync(filePath);
        if (stat.size < 4) return false;
        const fd = fs.openSync(filePath, 'r');
        const buf = Buffer.alloc(4);
        fs.readSync(fd, buf, 0, 4, 0);
        fs.closeSync(fd);
        return buf[0] === 0x7f && buf[1] === 0x45 && buf[2] === 0x4c && buf[3] === 0x46;
    } catch (_) {
        return false;
    }
}

function getIdeLsWrapperScript() {
    return `#!/usr/bin/env bash
# ==============================================================================
# Antigravity IDE Multi-Account Language Server Wrapper
# ==============================================================================
DIR="$(cd "$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
BIN="$DIR/language_server_linux_x64.bin"

if [ ! -f "$BIN" ]; then
    echo "[ERROR] Antigravity Language Server binary not found: $BIN" >&2
    exit 1
fi

PROXY_ENDPOINT="\${ANTIGRAVITY_CLOUD_CODE_ENDPOINT:-http://127.0.0.1:41999}"
ARGS=()
HAS_ENDPOINT=0

for arg in "$@"; do
    if [[ "$arg" == --cloud_code_endpoint=* ]] || [[ "$arg" == "-cloud_code_endpoint="* ]]; then
        ARGS+=("--cloud_code_endpoint=\${PROXY_ENDPOINT}")
        HAS_ENDPOINT=1
    elif [[ "$arg" == "https://cloudcode-pa.googleapis.com" ]] || [[ "$arg" == "https://daily-cloudcode-pa.googleapis.com" ]]; then
        ARGS+=("\${PROXY_ENDPOINT}")
        HAS_ENDPOINT=1
    else
        ARGS+=("$arg")
    fi
done

if [[ $HAS_ENDPOINT -eq 0 ]]; then
    ARGS+=("--cloud_code_endpoint=\${PROXY_ENDPOINT}")
fi

exec "$BIN" "\${ARGS[@]}"
`;
}

function patchIdeLanguageServer(ideDir) {
    const binDir = path.join(ideDir, 'resources/app/extensions/antigravity/bin');
    const lsScript = path.join(binDir, 'language_server_linux_x64');
    const lsBin = path.join(binDir, 'language_server_linux_x64.bin');
    const lsOrig = path.join(binDir, 'language_server_linux_x64.bin.orig');

    if (!fs.existsSync(binDir)) return;

    if (isElfBinary(lsScript)) {
        if (!fs.existsSync(lsOrig)) {
            copyFileSafe(lsScript, lsOrig);
            try { fs.chmodSync(lsOrig, 0o755); } catch (_) {}
        }
        try { fs.unlinkSync(lsBin); } catch (_) {}
        fs.renameSync(lsScript, lsBin);
        try { fs.chmodSync(lsBin, 0o755); } catch (_) {}
    } else if (isElfBinary(lsBin)) {
        if (!fs.existsSync(lsOrig)) {
            copyFileSafe(lsBin, lsOrig);
            try { fs.chmodSync(lsOrig, 0o755); } catch (_) {}
        }
    } else if (isElfBinary(lsOrig)) {
        copyFileSafe(lsOrig, lsBin);
        try { fs.chmodSync(lsBin, 0o755); } catch (_) {}
    }

    if (fs.existsSync(lsBin)) {
        fs.writeFileSync(lsScript, getIdeLsWrapperScript(), { encoding: 'utf8', mode: 0o755 });
        try { fs.chmodSync(lsScript, 0o755); } catch (_) {}
        try { fs.chmodSync(lsBin, 0o755); } catch (_) {}
    }
}

function unpatchIdeLanguageServer(ideDir) {
    const binDir = path.join(ideDir, 'resources/app/extensions/antigravity/bin');
    const lsScript = path.join(binDir, 'language_server_linux_x64');
    const lsBin = path.join(binDir, 'language_server_linux_x64.bin');
    const lsOrig = path.join(binDir, 'language_server_linux_x64.bin.orig');

    if (!fs.existsSync(binDir)) return;

    if (isElfBinary(lsBin)) {
        try { fs.unlinkSync(lsScript); } catch (_) {}
        fs.renameSync(lsBin, lsScript);
        try { fs.chmodSync(lsScript, 0o755); } catch (_) {}
    } else if (isElfBinary(lsOrig)) {
        try { fs.unlinkSync(lsScript); } catch (_) {}
        copyFileSafe(lsOrig, lsScript);
        try { fs.chmodSync(lsScript, 0o755); } catch (_) {}
        try { fs.unlinkSync(lsBin); } catch (_) {}
    }
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
