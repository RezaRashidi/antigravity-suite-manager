#!/usr/bin/env bash
# Helper routines to locate directories and JS patcher for Unified Experiments, Forking & Open-IDE

ensure_open_ide_symlink() {
    local ide_target="${IDE_INSTALL_DIR:-/opt/antigravity-ide}"
    local link_path="${REAL_HOME:-$HOME}/.local/share/antigravity-ide"
    if [ -d "$ide_target" ] && [ ! -e "$link_path" ]; then
        mkdir -p "$(dirname "$link_path")" 2>/dev/null || true
        ln -sf "$ide_target" "$link_path" 2>/dev/null || true
    fi
}

ensure_experiments_dirs() {
    auto_detect_installations 2>/dev/null || true
    if [ -z "$APP_INSTALL_DIR" ] || [ ! -f "${APP_INSTALL_DIR}/resources/app.asar" ]; then
        for c in "$APP_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_APP" "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity"; do
            [ -n "$c" ] && [ -f "${c}/resources/app.asar" ] && { APP_INSTALL_DIR="$c"; break; }
        done
    fi
    if [ -z "$IDE_INSTALL_DIR" ] || [ ! -d "${IDE_INSTALL_DIR}/resources/app/out" ]; then
        for c in "$IDE_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_IDE" "/opt/antigravity-ide" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity-ide"; do
            [ -n "$c" ] && [ -d "${c}/resources/app/out" ] && { IDE_INSTALL_DIR="$c"; break; }
        done
    fi
}

get_experiments_patch_js() {
    local s_dir; s_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
    local cand
    for cand in \
        "${s_dir}/antigravity-experiments-patch.js" \
        "${s_dir}/bin/antigravity-experiments-patch.js" \
        "${SCRIPT_DIR}/antigravity-experiments-patch.js" \
        "${SCRIPT_DIR}/bin/antigravity-experiments-patch.js" \
        "${REAL_HOME}/.antigravity-suite-manager/bin/antigravity-experiments-patch.js" \
        "${LOCAL_BIN}/antigravity-experiments-patch.js" \
        "/usr/local/bin/antigravity-experiments-patch.js"; do
        if [ -f "$cand" ]; then
            echo "$cand"
            return 0
        fi
    done

    if declare -f find_suite_repo_root >/dev/null 2>&1; then
        local r_dir; r_dir=$(find_suite_repo_root 2>/dev/null || true)
        if [ -n "$r_dir" ] && [ -f "${r_dir}/bin/antigravity-experiments-patch.js" ]; then
            echo "${r_dir}/bin/antigravity-experiments-patch.js"
            return 0
        fi
    fi
}
