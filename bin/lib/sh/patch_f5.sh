#!/usr/bin/env bash
# F5 backend reload and window/tray isolation patcher.

patch_f5_reload() {
    for arg in "$@"; do [ "$arg" = "--force" ] || [ "$arg" = "-f" ] && FORCE_INSTALL=true; done
    ensure_app_install_dir
    local asar_file="${APP_INSTALL_DIR}/resources/app.asar"
    if [ ! -f "$asar_file" ]; then
        log_warn "app.asar not found at ${asar_file}. Skipping F5 sync patch."
        return 0
    fi

    local patch_fingerprint="ANTIGRAVITY_SUITE_F5_PATCH_V3"
    if [ "$FORCE_INSTALL" != true ] && grep -qa "$patch_fingerprint" "$asar_file"; then
        log_info "F5 reload & profile isolation patch is already applied to app.asar. Skipping."
        return 0
    fi

    log_info "Ensuring permissions before F5 sync patch..."
    fix_permissions "$APP_INSTALL_DIR"

    log_info "Applying manual F5 backend reload and window/tray isolation patch..."
    local patch_js
    patch_js="$(get_f5_patch_js)"
    if [ -z "$patch_js" ] || [ ! -f "$patch_js" ]; then
        log_err "antigravity-f5-patch.js not found in ${LOCAL_BIN} or script dir."
        return 1
    fi

    local orig_file="${asar_file}.orig"
    if [ ! -f "$orig_file" ] && [ -f "$asar_file" ]; then
        log_info "Creating permanent pristine backup at ${orig_file}..."
        cp -p "$asar_file" "$orig_file"
    fi

    local tmp_dir
    tmp_dir=$(mktemp -d /tmp/asar_patch_XXXXXX)

    if ! run_asar extract "$asar_file" "$tmp_dir/unpacked"; then
        log_err "Failed to extract ${asar_file}."
        rm -rf "$tmp_dir"
        return 1
    fi

    if ! node "$patch_js" "$tmp_dir/unpacked"; then
        log_err "F5 patch script failed."
        rm -rf "$tmp_dir"
        return 1
    fi

    if ! run_asar pack "$tmp_dir/unpacked" "$tmp_dir/app.asar.patched" --unpack "*.node"; then
        log_err "Failed to pack patched app.asar."
        rm -rf "$tmp_dir"
        return 1
    fi

    cp "$tmp_dir/app.asar.patched" "$asar_file"
    rm -rf "$tmp_dir"

    if grep -qa "restartLanguageServer" "$asar_file"; then
        log_success "F5 manual sync patch applied and verified successfully."
    else
        log_err "Verification failed: F5 patch marker not found in ${asar_file}!"
        return 1
    fi
}
