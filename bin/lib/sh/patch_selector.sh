#!/usr/bin/env bash
# Antigravity Account Selector & Multi-Account Subsystem Patcher

patch_selector() {
    for arg in "$@"; do [ "$arg" = "--force" ] || [ "$arg" = "-f" ] && FORCE_INSTALL=true; done
    local asar_file="${APP_INSTALL_DIR}/resources/app.asar"
    if [ ! -f "$asar_file" ]; then
        log_warn "app.asar not found at ${asar_file}. Skipping selector patch."
        return 0
    fi

    local patch_fingerprint="ANTIGRAVITY_SUITE_SELECTOR_PATCH_V1"
    if [ "$FORCE_INSTALL" != true ] && grep -qa "$patch_fingerprint" "$asar_file"; then
        log_info "Account selector patch is already applied to app.asar. Skipping."
        return 0
    fi

    log_info "Ensuring permissions before selector patch..."
    fix_permissions "$APP_INSTALL_DIR"

    local patch_js="${LOCAL_BIN}/antigravity-selector-patch.js"
    if [ ! -f "$patch_js" ]; then
        local s_dir
        s_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
        [ -f "${s_dir}/bin/antigravity-selector-patch.js" ] && patch_js="${s_dir}/bin/antigravity-selector-patch.js"
        [ -f "${s_dir}/antigravity-selector-patch.js" ] && patch_js="${s_dir}/antigravity-selector-patch.js"
    fi
    if [ ! -f "$patch_js" ]; then
        log_err "antigravity-selector-patch.js not found in ${LOCAL_BIN} or script dir."
        return 1
    fi

    local orig_file="${asar_file}.orig"
    if [ ! -f "$orig_file" ] && [ -f "$asar_file" ]; then
        log_info "Creating permanent pristine backup at ${orig_file}..."
        cp -p "$asar_file" "$orig_file"
    fi

    local tmp_dir
    tmp_dir=$(mktemp -d /tmp/asar_patch_XXXXXX)

    log_info "Applying account selector patch..."
    npx --yes asar extract "$asar_file" "$tmp_dir/unpacked"
    node "$patch_js" "$tmp_dir/unpacked"
    npx --yes asar pack "$tmp_dir/unpacked" "$tmp_dir/app.asar.patched" --unpack "*.node"
    cp "$tmp_dir/app.asar.patched" "$asar_file"
    rm -rf "$tmp_dir"

    if grep -qa "$patch_fingerprint" "$asar_file" || grep -qa "multi_account_ui" "$asar_file"; then
        log_success "Account selector patch applied and verified successfully."
    else
        log_err "Verification failed: Selector patch marker not found in ${asar_file}!"
        return 1
    fi
}

unpatch_selector() {
    local asar_file="${APP_INSTALL_DIR}/resources/app.asar"
    if [ ! -f "$asar_file" ]; then
        log_warn "app.asar not found at ${asar_file}."
        return 0
    fi

    local patch_fingerprint="ANTIGRAVITY_SUITE_SELECTOR_PATCH_V1"
    if ! grep -qa "$patch_fingerprint" "$asar_file" && ! grep -qa "multi_account_ui" "$asar_file"; then
        log_info "Account selector patch is not applied. Nothing to revert."
        return 0
    fi

    log_info "Removing account selector patch from app.asar..."
    fix_permissions "$APP_INSTALL_DIR"

    local patch_js="${LOCAL_BIN}/antigravity-selector-patch.js"
    if [ ! -f "$patch_js" ]; then
        local s_dir
        s_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
        [ -f "${s_dir}/bin/antigravity-selector-patch.js" ] && patch_js="${s_dir}/bin/antigravity-selector-patch.js"
        [ -f "${s_dir}/antigravity-selector-patch.js" ] && patch_js="${s_dir}/antigravity-selector-patch.js"
    fi

    local tmp_dir
    tmp_dir=$(mktemp -d /tmp/asar_patch_XXXXXX)

    npx --yes asar extract "$asar_file" "$tmp_dir/unpacked"
    node "$patch_js" --unpatch "$tmp_dir/unpacked"
    npx --yes asar pack "$tmp_dir/unpacked" "$tmp_dir/app.asar.patched" --unpack "*.node"
    cp "$tmp_dir/app.asar.patched" "$asar_file"
    rm -rf "$tmp_dir"

    log_success "Account selector patch successfully removed (F5 patch preserved if present)."
}
