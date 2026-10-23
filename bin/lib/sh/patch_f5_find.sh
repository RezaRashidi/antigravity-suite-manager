#!/usr/bin/env bash
# Helper routines to locate Antigravity App install directory and F5 patch script

ensure_app_install_dir() {
    [ -n "$APP_INSTALL_DIR" ] && [ -f "${APP_INSTALL_DIR}/resources/app.asar" ] && return 0
    auto_detect_installations 2>/dev/null || true
    [ -n "$APP_INSTALL_DIR" ] && [ -f "${APP_INSTALL_DIR}/resources/app.asar" ] && return 0
    for c in "$ANTIGRAVITY_DETECTED_APP" "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity"; do
        [ -n "$c" ] && [ -f "${c}/resources/app.asar" ] && { APP_INSTALL_DIR="$c"; return 0; }
    done
}

get_f5_patch_js() {
    local s_dir; s_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
    local cand
    for cand in \
        "${LOCAL_BIN}/antigravity-f5-patch.js" \
        "${s_dir}/antigravity-f5-patch.js" \
        "${s_dir}/bin/antigravity-f5-patch.js" \
        "${SCRIPT_DIR}/antigravity-f5-patch.js" \
        "${SCRIPT_DIR}/bin/antigravity-f5-patch.js" \
        "${REAL_HOME}/antigravity-suite-manager/bin/antigravity-f5-patch.js" \
        "${REAL_HOME}/PhpstormProjects/antigravity-suite-manager/bin/antigravity-f5-patch.js" \
        "/usr/local/bin/antigravity-f5-patch.js"; do
        if [ -f "$cand" ]; then
            if [ ! -f "${LOCAL_BIN}/antigravity-f5-patch.js" ]; then
                mkdir -p "${LOCAL_BIN}"
                cp -f "$cand" "${LOCAL_BIN}/antigravity-f5-patch.js" 2>/dev/null || true
                chmod +x "${LOCAL_BIN}/antigravity-f5-patch.js" 2>/dev/null || true
            fi
            echo "$cand"
            return 0
        fi
    done

    if declare -f find_suite_repo_root >/dev/null 2>&1; then
        local r_dir; r_dir=$(find_suite_repo_root 2>/dev/null || true)
        if [ -n "$r_dir" ] && [ -f "${r_dir}/bin/antigravity-f5-patch.js" ]; then
            cand="${r_dir}/bin/antigravity-f5-patch.js"
            mkdir -p "${LOCAL_BIN}"
            cp -f "$cand" "${LOCAL_BIN}/antigravity-f5-patch.js" 2>/dev/null || true
            chmod +x "${LOCAL_BIN}/antigravity-f5-patch.js" 2>/dev/null || true
            echo "$cand"
            return 0
        fi
    fi
}
