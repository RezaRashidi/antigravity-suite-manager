#!/usr/bin/env bash
# Antigravity Conversation Forking Patcher (App & IDE)

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

patch_fork_app() {
    ensure_fork_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    local p_js; p_js="$(get_fork_patch_js)"

    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}. Skipping App fork patch."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-fork-patch.js not found."
        return 1
    fi

    if [ "$FORCE_INSTALL" != true ] && grep -qa "ANTIGRAVITY_SUITE_FORK_PATCH_V1" "$asar"; then
        log_info "Conversation forking already applied to app.asar (${APP_INSTALL_DIR})."
        return 0
    fi
    log_info "Applying Conversation Forking patch to Antigravity App at ${APP_INSTALL_DIR}..."
    fix_permissions "$APP_INSTALL_DIR"

    local orig="${asar}.orig"
    [ ! -f "$orig" ] && cp -p "$asar" "$orig"

    local tmp; tmp=$(mktemp -d /tmp/asar_fork_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    if ! node "$p_js" --app "$tmp/unpacked"; then
        log_err "Fork patch script failed for App."
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
    log_success "Conversation Forking applied to Antigravity App (${APP_INSTALL_DIR})."
}

unpatch_fork_app() {
    ensure_fork_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    local p_js; p_js="$(get_fork_patch_js)"

    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-fork-patch.js not found."
        return 1
    fi

    log_info "Removing Conversation Forking patch from Antigravity App at ${APP_INSTALL_DIR}..."
    fix_permissions "$APP_INSTALL_DIR"

    local tmp; tmp=$(mktemp -d /tmp/asar_fork_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    if ! node "$p_js" --unpatch --app "$tmp/unpacked"; then
        log_err "Fork unpatch script failed for App."
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
    log_success "Conversation Forking removed from Antigravity App (${APP_INSTALL_DIR})."
}

patch_fork_ide() {
    ensure_fork_dirs
    local p_js; p_js="$(get_fork_patch_js)"
    if [ -z "$IDE_INSTALL_DIR" ] || [ ! -d "${IDE_INSTALL_DIR}/resources/app/out" ]; then
        log_warn "IDE out directory not found at ${IDE_INSTALL_DIR:-'<undefined>'}. Skipping IDE fork patch."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-fork-patch.js not found."
        return 1
    fi

    log_info "Applying Conversation Forking patch to Antigravity IDE at ${IDE_INSTALL_DIR}..."
    fix_permissions "$IDE_INSTALL_DIR"
    node "$p_js" --ide "$IDE_INSTALL_DIR"
    if declare -f fix_ide_checksums >/dev/null 2>&1; then
        fix_ide_checksums "$IDE_INSTALL_DIR" 2>/dev/null || true
    fi
    log_success "Conversation Forking applied to Antigravity IDE (${IDE_INSTALL_DIR})."
}

unpatch_fork_ide() {
    ensure_fork_dirs
    local p_js; p_js="$(get_fork_patch_js)"
    if [ -z "$IDE_INSTALL_DIR" ] || [ ! -d "${IDE_INSTALL_DIR}/resources/app/out" ]; then
        log_warn "IDE out directory not found at ${IDE_INSTALL_DIR:-'<undefined>'}."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-fork-patch.js not found."
        return 1
    fi

    log_info "Removing Conversation Forking patch from Antigravity IDE at ${IDE_INSTALL_DIR}..."
    fix_permissions "$IDE_INSTALL_DIR"
    node "$p_js" --unpatch --ide "$IDE_INSTALL_DIR"
    if declare -f fix_ide_checksums >/dev/null 2>&1; then
        fix_ide_checksums "$IDE_INSTALL_DIR" 2>/dev/null || true
    fi
    log_success "Conversation Forking removed from Antigravity IDE (${IDE_INSTALL_DIR})."
}

patch_fork_all() {
    log_info "Applying Conversation Forking to All Targets (App & IDE)..."
    patch_fork_app
    patch_fork_ide
}

unpatch_fork_all() {
    log_info "Removing Conversation Forking from All Targets (App & IDE)..."
    unpatch_fork_app
    unpatch_fork_ide
}
