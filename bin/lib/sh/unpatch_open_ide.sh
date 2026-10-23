#!/usr/bin/env bash
# Routines to revert native 'Open in IDE' titlebar button patch

unpatch_open_ide_app() {
    ensure_app_install_dir
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    local p_js; p_js="$(get_open_ide_patch_js)"

    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "patch_open_ide.js not found."
        return 1
    fi

    log_info "Removing Native 'Open in IDE' patch from Antigravity App at ${APP_INSTALL_DIR}..."
    fix_permissions "$APP_INSTALL_DIR"

    local tmp; tmp=$(mktemp -d /tmp/asar_open_ide_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    if ! node "$p_js" --unpatch "$tmp/unpacked"; then
        log_err "Open IDE unpatch script failed."
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
    log_success "Native 'Open in IDE' button patch removed from Antigravity App."
}
