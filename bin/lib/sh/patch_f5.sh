#!/usr/bin/env bash
# F5 backend reload and window/tray isolation patcher.

ensure_app_install_dir() {
    [ -n "$APP_INSTALL_DIR" ] && [ -f "${APP_INSTALL_DIR}/resources/app.asar" ] && return 0
    auto_detect_installations 2>/dev/null || true
    [ -n "$APP_INSTALL_DIR" ] && [ -f "${APP_INSTALL_DIR}/resources/app.asar" ] && return 0
    for c in "$ANTIGRAVITY_DETECTED_APP" "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity"; do
        [ -n "$c" ] && [ -f "${c}/resources/app.asar" ] && { APP_INSTALL_DIR="$c"; return 0; }
    done
}

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

    local orig_file="${asar_file}.orig"
    if [ ! -f "$orig_file" ] && [ -f "$asar_file" ]; then
        log_info "Creating permanent pristine backup at ${orig_file}..."
        cp -p "$asar_file" "$orig_file"
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

unpatch_f5() {
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
