#!/usr/bin/env bash
# Helper routines to locate directories, sync skills, and decouple keyrings for selector

ensure_selector_dirs() {
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

get_selector_patch_js() {
    local s_dir; s_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
    local cand
    for cand in \
        "${s_dir}/antigravity-selector-patch.js" \
        "${s_dir}/bin/antigravity-selector-patch.js" \
        "${SCRIPT_DIR}/antigravity-selector-patch.js" \
        "${SCRIPT_DIR}/bin/antigravity-selector-patch.js" \
        "${REAL_HOME}/antigravity-suite-manager/bin/antigravity-selector-patch.js" \
        "${REAL_HOME}/PhpstormProjects/antigravity-suite-manager/bin/antigravity-selector-patch.js" \
        "${LOCAL_BIN}/antigravity-selector-patch.js" \
        "/usr/local/bin/antigravity-selector-patch.js"; do
        if [ -f "$cand" ]; then
            if [ "$cand" != "${LOCAL_BIN}/antigravity-selector-patch.js" ]; then
                mkdir -p "${LOCAL_BIN}"
                cp -f "$cand" "${LOCAL_BIN}/antigravity-selector-patch.js" 2>/dev/null || true
                chmod +x "${LOCAL_BIN}/antigravity-selector-patch.js" 2>/dev/null || true
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
        if [ -n "$r_dir" ] && [ -f "${r_dir}/bin/antigravity-selector-patch.js" ]; then
            cand="${r_dir}/bin/antigravity-selector-patch.js"
            mkdir -p "${LOCAL_BIN}"
            cp -f "$cand" "${LOCAL_BIN}/antigravity-selector-patch.js" 2>/dev/null || true
            chmod +x "${LOCAL_BIN}/antigravity-selector-patch.js" 2>/dev/null || true
            if [ -d "${r_dir}/bin/lib/patch" ]; then
                mkdir -p "${LOCAL_BIN}/lib"
                cp -rf "${r_dir}/bin/lib/patch" "${LOCAL_BIN}/lib/" 2>/dev/null || true
            fi
            echo "$cand"
            return 0
        fi
    fi
}

sync_selector_skills() {
    local r_dir; r_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    for base in "${REAL_HOME:-$HOME}/.gemini" "${REAL_HOME:-$HOME}/.gemide"; do
        mkdir -p "${base}/config/skills" 2>/dev/null || true
        for sk in whoami accounts switch; do
            [ -d "${r_dir}/skills/${sk}" ] && cp -rf "${r_dir}/skills/${sk}" "${base}/config/skills/" 2>/dev/null || true
        done
    done
}

ensure_keyring_decoupled() {
    log_info "Ensuring keyring storage mode is decoupled (Normal File Storage)..."
    local s_dir; s_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
    if declare -f set_keyring_mode >/dev/null 2>&1; then
        set_keyring_mode "all" "normal" >/dev/null 2>&1 || true
    elif declare -f keyring_command >/dev/null 2>&1; then
        keyring_command set all normal >/dev/null 2>&1 || true
    elif [ -f "${s_dir}/bin/antigravity-keyring.py" ]; then
        python3 "${s_dir}/bin/antigravity-keyring.py" set all normal >/dev/null 2>&1 || true
    elif [ -f "${LOCAL_BIN}/antigravity-keyring.py" ]; then
        python3 "${LOCAL_BIN}/antigravity-keyring.py" set all normal >/dev/null 2>&1 || true
    fi

    for c_dir in "${REAL_HOME:-$HOME}/.gemini/cache" "${REAL_HOME:-$HOME}/.gemide/cache" "${REAL_HOME:-$HOME}/.gemini/antigravity-ide/cache"; do
        mkdir -p "$c_dir" 2>/dev/null || true
        touch "${c_dir}/antigravity-keyring-unavailable" 2>/dev/null || true
    done

    if [ ! -f "${REAL_HOME:-$HOME}/.gemini/jetski-standalone-oauth-token" ]; then
        python3 -c "from antigravity_suite.auth.keyring_apply import apply_mode_for_app1; apply_mode_for_app1('normal', migrate_token=True)" 2>/dev/null || true
    fi
}
