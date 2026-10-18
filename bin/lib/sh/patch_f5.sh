#!/usr/bin/env bash
# F5 backend reload and window/tray isolation patcher.

patch_f5_reload() {
    local asar_file="${APP_INSTALL_DIR}/resources/app.asar"
    if [ ! -f "$asar_file" ]; then
        log_warn "app.asar not found at ${asar_file}. Skipping F5 sync patch."
        return 0
    fi

    if [ "$FORCE_INSTALL" != true ] && grep -qa "restartLanguageServer" "$asar_file" && grep -qa "ANTIGRAVITY_TRAY_ICON_PATH" "$asar_file"; then
        log_info "F5 reload & profile isolation patch is already applied to app.asar. Skipping."
        return 0
    fi

    log_info "Ensuring permissions before F5 sync patch..."
    fix_permissions "$APP_INSTALL_DIR"

    log_info "Applying manual F5 backend reload and window/tray isolation patch..."
    local patch_js="${LOCAL_BIN}/antigravity-f5-patch.js"
    if [ ! -f "$patch_js" ]; then
        local s_dir
        s_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
        [ -f "${s_dir}/bin/antigravity-f5-patch.js" ] && patch_js="${s_dir}/bin/antigravity-f5-patch.js"
        [ -f "${s_dir}/antigravity-f5-patch.js" ] && patch_js="${s_dir}/antigravity-f5-patch.js"
    fi
    if [ ! -f "$patch_js" ]; then
        log_err "antigravity-f5-patch.js not found in ${LOCAL_BIN} or script dir."
        return 1
    fi

    local tmp_dir
    tmp_dir=$(mktemp -d /tmp/asar_patch_XXXXXX)

    npx --yes asar extract "$asar_file" "$tmp_dir/unpacked"
    node "$patch_js" "$tmp_dir/unpacked"
    npx --yes asar pack "$tmp_dir/unpacked" "$tmp_dir/app.asar.patched" --unpack "*.node"
    cp "$tmp_dir/app.asar.patched" "$asar_file"
    rm -rf "$tmp_dir"

    if grep -qa "restartLanguageServer" "$asar_file"; then
        log_success "F5 manual sync patch applied and verified successfully."
    else
        log_err "Verification failed: F5 patch marker not found in ${asar_file}!"
        return 1
    fi
}
