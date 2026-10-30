#!/usr/bin/env bash
# Full suite update orchestrator

reapply_detected_patches() {
    log_info "Re-applying previously applied patches..."
    if [ "$HAD_APP_SELECTOR" = true ]; then
        log_info "Re-applying Multi-Account Selector to App..."
        FORCE_INSTALL=true patch_selector_app
    fi
    if [ "$HAD_IDE_SELECTOR" = true ]; then
        log_info "Re-applying Multi-Account Selector to IDE..."
        FORCE_INSTALL=true patch_selector_ide
    fi
    if [ "$HAD_APP_RTL" = true ] && [ "$SKIP_RTL" != true ]; then
        log_info "Re-applying RTL patch to App..."
        FORCE_INSTALL=true patch_rtl_app --force
    fi
    if [ "$HAD_IDE_RTL" = true ] && [ "$SKIP_RTL" != true ]; then
        log_info "Re-applying RTL patch to IDE..."
        FORCE_INSTALL=true patch_rtl_ide --force
    fi
    if [ "$HAD_APP_F5" = true ] && [ "$SKIP_F5" != true ]; then
        log_info "Re-applying F5 reload patch to App..."
        FORCE_INSTALL=true patch_f5_reload --force
    fi
    if [ "$HAD_APP_FORK" = true ]; then
        log_info "Re-applying Conversation Forking patch to App..."
        FORCE_INSTALL=true patch_fork_app
    fi
    if [ "$HAD_APP_MODELS" = true ]; then
        log_info "Re-applying Custom Models UI patch to App..."
        FORCE_INSTALL=true patch_models_app
    fi
    if [ "$HAD_IDE_FORK" = true ]; then
        log_info "Re-applying Conversation Forking patch to IDE..."
        FORCE_INSTALL=true patch_fork_ide
    fi
    if [ "$HAD_IDE_SELECTOR" = true ] || [ "$HAD_IDE_RTL" = true ] || [ "$HAD_IDE_FORK" = true ]; then
        fix_ide_checksums "${IDE_INSTALL_DIR}"
    fi
}

update_all() {
    auto_detect_installations
    resolve_dynamic_urls
    log_info "Inspecting pre-update status & patches..."
    check_status

    detect_active_app_patches
    detect_active_ide_patches
    log_info "Pre-update active patch detection:"
    log_info "  • App: Selector=${HAD_APP_SELECTOR}, RTL=${HAD_APP_RTL}, F5=${HAD_APP_F5}, Fork=${HAD_APP_FORK}, Models=${HAD_APP_MODELS}"
    log_info "  • IDE: Selector=${HAD_IDE_SELECTOR}, RTL=${HAD_IDE_RTL}, Fork=${HAD_IDE_FORK}"

    log_info "Starting full suite update..."
    log_info "User configs, databases, keys, and history will be preserved."

    terminate_running_app
    install_binary "Antigravity-App" "$APP_URL" "$TARGET_APP_VER" "$APP_INSTALL_DIR"
    setup_account_1
    if [ -d "$PROFILE2_DIR" ] && [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
        setup_account_2
    fi

    install_binary "Antigravity-IDE" "$IDE_URL" "$TARGET_IDE_VER" "$IDE_INSTALL_DIR"
    setup_ide_shortcuts

    reapply_detected_patches

    log_info "Verifying post-update status & patches..."
    check_status
    log_success "Full suite update routine complete!"
}
