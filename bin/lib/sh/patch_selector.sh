#!/usr/bin/env bash
# Antigravity Account Selector Patcher (App & IDE)

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
        "${LOCAL_BIN}/antigravity-selector-patch.js" \
        "${s_dir}/antigravity-selector-patch.js" \
        "${s_dir}/bin/antigravity-selector-patch.js" \
        "${SCRIPT_DIR}/antigravity-selector-patch.js" \
        "${SCRIPT_DIR}/bin/antigravity-selector-patch.js" \
        "${REAL_HOME}/antigravity-suite-manager/bin/antigravity-selector-patch.js" \
        "${REAL_HOME}/PhpstormProjects/antigravity-suite-manager/bin/antigravity-selector-patch.js" \
        "/usr/local/bin/antigravity-selector-patch.js"; do
        if [ -f "$cand" ]; then
            if [ ! -f "${LOCAL_BIN}/antigravity-selector-patch.js" ]; then
                mkdir -p "${LOCAL_BIN}"
                cp -f "$cand" "${LOCAL_BIN}/antigravity-selector-patch.js" 2>/dev/null || true
                chmod +x "${LOCAL_BIN}/antigravity-selector-patch.js" 2>/dev/null || true
            fi
            local cand_dir; cand_dir="$(dirname "$cand")"
            if [ -d "${cand_dir}/lib/patch" ] && [ ! -d "${LOCAL_BIN}/lib/patch" ]; then
                mkdir -p "${LOCAL_BIN}/lib"
                cp -rf "${cand_dir}/lib/patch" "${LOCAL_BIN}/lib/" 2>/dev/null || true
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
            if [ -d "${r_dir}/bin/lib/patch" ] && [ ! -d "${LOCAL_BIN}/lib/patch" ]; then
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

patch_selector_app() {
    ensure_selector_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    local p_js; p_js="$(get_selector_patch_js)"

    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}. Skipping App selector patch."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-selector-patch.js not found."
        return 1
    fi

    if [ "$FORCE_INSTALL" != true ] && grep -qa "ANTIGRAVITY_SUITE_SELECTOR_PATCH_V1" "$asar"; then
        log_info "Account selector already applied to app.asar (${APP_INSTALL_DIR})."
        return 0
    fi
    log_info "Applying account selector to Antigravity App at ${APP_INSTALL_DIR}..."
    fix_permissions "$APP_INSTALL_DIR"

    local orig="${asar}.orig"
    [ ! -f "$orig" ] && cp -p "$asar" "$orig"

    local tmp; tmp=$(mktemp -d /tmp/asar_patch_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    if ! node "$p_js" --app "$tmp/unpacked"; then
        log_err "Selector patch script failed for App."
        rm -rf "$tmp"
        return 1
    fi

    if ! run_asar pack "$tmp/unpacked" "$tmp/app.asar.patched" --unpack "*.node"; then
        log_err "Failed to pack patched app.asar."
        rm -rf "$tmp"
        return 1
    fi

    cp "$tmp/app.asar.patched" "$asar"
    rm -rf "$tmp"
    sync_selector_skills
    log_success "Account selector applied to Antigravity App (${APP_INSTALL_DIR})."
}

unpatch_selector_app() {
    ensure_selector_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    local p_js; p_js="$(get_selector_patch_js)"

    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-selector-patch.js not found."
        return 1
    fi

    log_info "Removing account selector from Antigravity App at ${APP_INSTALL_DIR}..."
    fix_permissions "$APP_INSTALL_DIR"

    local tmp; tmp=$(mktemp -d /tmp/asar_patch_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    if ! node "$p_js" --app --unpatch "$tmp/unpacked"; then
        log_err "Selector unpatch script failed for App."
        rm -rf "$tmp"
        return 1
    fi

    if ! run_asar pack "$tmp/unpacked" "$tmp/app.asar.patched" --unpack "*.node"; then
        log_err "Failed to pack unpatched app.asar."
        rm -rf "$tmp"
        return 1
    fi

    cp "$tmp/app.asar.patched" "$asar"
    rm -rf "$tmp"
    log_success "Account selector removed from Antigravity App (${APP_INSTALL_DIR})."
}

patch_selector_ide() {
    ensure_selector_dirs
    local ide="${IDE_INSTALL_DIR}"
    local p_js; p_js="$(get_selector_patch_js)"

    if [ ! -d "$ide" ]; then
        log_warn "Antigravity IDE directory not found at ${ide:-'<undefined>'}. Skipping IDE selector patch."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-selector-patch.js not found."
        return 1
    fi

    local marker="${ide}/resources/app/out/antigravity_ide_selector_patch.marker"
    if [ "$FORCE_INSTALL" != true ] && [ -f "$marker" ]; then
        log_info "Account selector already applied to IDE (${ide})."
        return 0
    fi
    log_info "Applying account selector to Antigravity IDE at ${ide}..."
    fix_permissions "$ide"
    if ! node "$p_js" --ide "$ide"; then
        log_err "Selector patch script failed for IDE."
        return 1
    fi
    sync_selector_skills
    fix_ide_checksums "$ide"
    log_success "Account selector applied to Antigravity IDE (${ide})."
}

unpatch_selector_ide() {
    ensure_selector_dirs
    local ide="${IDE_INSTALL_DIR}"
    local p_js; p_js="$(get_selector_patch_js)"

    if [ ! -d "$ide" ]; then
        log_warn "Antigravity IDE directory not found at ${ide:-'<undefined>'}."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-selector-patch.js not found."
        return 1
    fi

    log_info "Removing account selector from Antigravity IDE at ${ide}..."
    fix_permissions "$ide"
    if ! node "$p_js" --ide --unpatch "$ide"; then
        log_err "Selector unpatch script failed for IDE."
        return 1
    fi
    fix_ide_checksums "$ide"
    log_success "Account selector removed from Antigravity IDE (${ide})."
}

patch_selector() {
    for arg in "$@"; do [ "$arg" = "--force" ] || [ "$arg" = "-f" ] && FORCE_INSTALL=true; done
    case "${SUB_COMMAND:-${1:-all}}" in
        app) patch_selector_app "$@" ;;
        ide) patch_selector_ide "$@" ;;
        all|*)
            local err=0
            patch_selector_app "$@" || err=1
            patch_selector_ide "$@" || err=1
            return $err
            ;;
    esac
}

unpatch_selector() {
    case "${SUB_COMMAND:-${1:-all}}" in
        app) unpatch_selector_app "$@" ;;
        ide) unpatch_selector_ide "$@" ;;
        all|*)
            local err=0
            unpatch_selector_app "$@" || err=1
            unpatch_selector_ide "$@" || err=1
            return $err
            ;;
    esac
}
