#!/usr/bin/env bash
# Helper routines to locate directories and JS patcher for conversation forking

ensure_fork_dirs() {
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

get_fork_patch_js() {
    local s_dir; s_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
    local cand
    for cand in \
        "${s_dir}/antigravity-fork-patch.js" \
        "${s_dir}/bin/antigravity-fork-patch.js" \
        "${SCRIPT_DIR}/antigravity-fork-patch.js" \
        "${SCRIPT_DIR}/bin/antigravity-fork-patch.js" \
        "${REAL_HOME}/antigravity-suite-manager/bin/antigravity-fork-patch.js" \
        "${REAL_HOME}/PhpstormProjects/antigravity-suite-manager/bin/antigravity-fork-patch.js" \
        "${LOCAL_BIN}/antigravity-fork-patch.js" \
        "/usr/local/bin/antigravity-fork-patch.js"; do
        if [ -f "$cand" ]; then
            if [ "$cand" != "${LOCAL_BIN}/antigravity-fork-patch.js" ]; then
                mkdir -p "${LOCAL_BIN}"
                cp -f "$cand" "${LOCAL_BIN}/antigravity-fork-patch.js" 2>/dev/null || true
                chmod +x "${LOCAL_BIN}/antigravity-fork-patch.js" 2>/dev/null || true
                local cand_dir; cand_dir="$(dirname "$cand")"
                if [ -d "${cand_dir}/lib/patch" ]; then
                    mkdir -p "${LOCAL_BIN}/lib"
                    cp -rf "${cand_dir}/lib/patch" "${LOCAL_BIN}/lib/" 2>/dev/null || true
                elif [ -d "${cand_dir}/../lib/patch" ]; then
                    mkdir -p "${LOCAL_BIN}/lib"
                    cp -rf "${cand_dir}/../lib/patch" "${LOCAL_BIN}/lib/" 2>/dev/null || true
                fi
            fi
            echo "$cand"
            return 0
        fi
    done

    if declare -f find_suite_repo_root >/dev/null 2>&1; then
        local r_dir; r_dir=$(find_suite_repo_root 2>/dev/null || true)
        if [ -n "$r_dir" ] && [ -f "${r_dir}/bin/antigravity-fork-patch.js" ]; then
            cand="${r_dir}/bin/antigravity-fork-patch.js"
            mkdir -p "${LOCAL_BIN}"
            cp -f "$cand" "${LOCAL_BIN}/antigravity-fork-patch.js" 2>/dev/null || true
            chmod +x "${LOCAL_BIN}/antigravity-fork-patch.js" 2>/dev/null || true
            if [ -d "${r_dir}/bin/lib/patch" ]; then
                mkdir -p "${LOCAL_BIN}/lib"
                cp -rf "${r_dir}/bin/lib/patch" "${LOCAL_BIN}/lib/" 2>/dev/null || true
            fi
            echo "$cand"
            return 0
        fi
    fi
}
