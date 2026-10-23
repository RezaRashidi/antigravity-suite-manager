#!/usr/bin/env bash
# Routines to unpatch F5 backend reload and restore pristine app.asar

unpatch_f5() {
    local custom_app_dir=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --app-dir) custom_app_dir="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    [ -n "$custom_app_dir" ] && APP_INSTALL_DIR="$custom_app_dir"
    ensure_app_install_dir
    local asar_file="${APP_INSTALL_DIR}/resources/app.asar"
    if [ ! -f "$asar_file" ]; then
        log_warn "app.asar not found at ${asar_file}."
        return 0
    fi
    if ! grep -qa "restartLanguageServer" "$asar_file"; then
        log_info "F5 reload patch is not applied. Nothing to revert."
        return 0
    fi

    if grep -qa "multi_account_ui" "$asar_file"; then
        log_info "Reverting F5 patch while preserving account selector..."
        unpatch_antigravity
        patch_selector
    else
        unpatch_antigravity
    fi
    log_success "F5 patch removed successfully."
}

unpatch_antigravity() {
    ensure_app_install_dir
    local asar_file="${APP_INSTALL_DIR}/resources/app.asar"
    local orig_file="${asar_file}.orig"
    local bak2_file="${asar_file}.bak2"

    local src=""
    if [ -f "$orig_file" ]; then
        src="$orig_file"
    elif [ -f "$bak2_file" ]; then
        src="$bak2_file"
    fi

    if [ -z "$src" ]; then
        log_err "No unmodified backup found (checked ${orig_file} and ${bak2_file})."
        return 1
    fi

    log_info "Restoring unmodified original app.asar from $(basename "$src")..."
    fix_permissions "${APP_INSTALL_DIR}"
    cp -f "$src" "$asar_file"
    chmod 644 "$asar_file"

    pkill -f "antigravity-multi-account.py serve" 2>/dev/null || true

    log_success "Successfully restored ${asar_file} to clean state."
    log_info "Antigravity is now completely unpatched."
}
