#!/usr/bin/env bash
# Suite update and cache cleaning routines

update_all() {
    auto_detect_installations
    resolve_dynamic_urls
    log_info "Inspecting pre-update status & patches..."
    check_status

    log_info "Starting full suite update..."
    log_info "User configs, databases, keys, and history will be preserved."

    install_binary "Antigravity-App" "$APP_URL" "$TARGET_APP_VER" "$APP_INSTALL_DIR"
    setup_account_1
    if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
        setup_account_2
    fi

    install_binary "Antigravity-IDE" "$IDE_URL" "$TARGET_IDE_VER" "$IDE_INSTALL_DIR"
    setup_ide_shortcuts

    if [ "$SKIP_RTL" != true ]; then
        patch_rtl_all
    elif [ "$SKIP_F5" != true ]; then
        patch_f5_reload
    fi

    log_info "Verifying post-update status & patches..."
    check_status
    log_success "Full suite update routine complete!"
}

update_app() {
    auto_detect_installations
    resolve_dynamic_urls
    log_info "Updating Antigravity App at ${APP_INSTALL_DIR}..."
    install_binary "Antigravity-App" "$APP_URL" "$TARGET_APP_VER" "$APP_INSTALL_DIR"
    setup_account_1
    if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
        setup_account_2
    fi
    [ "$SKIP_RTL" != true ] && patch_rtl_app "$@"
    [ "$SKIP_F5" != true ] && patch_f5_reload "$@"
    log_success "Antigravity App update routine complete."
}

update_ide() {
    auto_detect_installations
    resolve_dynamic_urls
    log_info "Updating Antigravity IDE at ${IDE_INSTALL_DIR}..."
    install_binary "Antigravity-IDE" "$IDE_URL" "$TARGET_IDE_VER" "$IDE_INSTALL_DIR"
    setup_ide_shortcuts
    [ "$SKIP_RTL" != true ] && patch_rtl_ide "$@"
    fix_ide_checksums "${IDE_INSTALL_DIR}"
    log_success "Antigravity IDE update routine complete."
}

clean_cache() {
    log_info "Cleaning archive cache directory (${CACHE_DIR})..."
    rm -rf "${CACHE_DIR}"/*
    log_success "Archive cache cleared."
}

