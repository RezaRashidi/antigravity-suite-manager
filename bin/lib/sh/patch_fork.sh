#!/usr/bin/env bash
# Antigravity Conversation Forking Patcher (App & IDE)

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

patch_fork_all() {
    log_info "Applying Conversation Forking to All Targets (App & IDE)..."
    patch_fork_app
    patch_fork_ide
}
