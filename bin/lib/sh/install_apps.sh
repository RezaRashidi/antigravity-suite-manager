#!/usr/bin/env bash
# App, IDE, and Full Suite installation orchestrator functions.

install_antigravity_app() {
    resolve_dynamic_urls
    check_status

    install_binary "Antigravity-App" "$APP_URL" "$TARGET_APP_VER" "$APP_INSTALL_DIR"
    setup_account_1
    if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
        setup_account_2
    fi

    if [ "$SKIP_RTL" != true ]; then
        patch_rtl_app
    fi
    if [ "$SKIP_F5" != true ]; then
        patch_f5_reload
    fi

    log_info "Verifying post-install status..."
    check_status
}

install_antigravity_ide() {
    resolve_dynamic_urls
    check_status

    install_binary "Antigravity-IDE" "$IDE_URL" "$TARGET_IDE_VER" "$IDE_INSTALL_DIR"
    setup_ide_shortcuts

    if [ "$SKIP_RTL" != true ]; then
        patch_rtl_ide
    fi

    log_info "Verifying post-install status..."
    check_status
}

install_antigravity_all() {
    log_info "Executing Full Antigravity Suite Installation (App + IDE + RTL + F5)..."
    resolve_dynamic_urls
    check_status

    install_binary "Antigravity-App" "$APP_URL" "$TARGET_APP_VER" "$APP_INSTALL_DIR"
    setup_account_1
    if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
        setup_account_2
    fi

    install_binary "Antigravity-IDE" "$IDE_URL" "$TARGET_IDE_VER" "$IDE_INSTALL_DIR"
    setup_ide_shortcuts

    if [ "$SKIP_RTL" != true ]; then
        patch_rtl_all
    fi
    if [ "$SKIP_F5" != true ]; then
        patch_f5_reload
    fi

    log_info "Verifying post-install status..."
    check_status
    log_success "Antigravity Suite Installation Completed Successfully!"
}
