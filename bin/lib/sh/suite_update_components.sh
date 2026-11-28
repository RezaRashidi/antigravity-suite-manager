#!/usr/bin/env bash
# Component-level updates for App and IDE, and cache cleanup

update_app() {
    auto_detect_installations
    resolve_dynamic_urls
    log_info "Updating Antigravity App at ${APP_INSTALL_DIR}..."
    detect_active_app_patches
    log_info "Pre-update active App patches: Selector=${HAD_APP_SELECTOR}, RTL=${HAD_APP_RTL}, Experiments/Fork/OpenIDE=${HAD_APP_EXPERIMENTS}, WinBounds=${HAD_APP_WINDOW_BOUNDS}, Models=${HAD_APP_MODELS}"

    terminate_running_app
    install_binary "Antigravity-App" "$APP_URL" "$TARGET_APP_VER" "$APP_INSTALL_DIR"
    setup_account_1
    if [ -d "$PROFILE2_DIR" ] && [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
        setup_account_2
    fi

    log_info "Re-applying previously applied App patches..."
    [ "$HAD_APP_MODELS" = true ] && { FORCE_INSTALL=true patch_models_app; }
    [ "$HAD_APP_RTL" = true ] && [ "$SKIP_RTL" != true ] && { FORCE_INSTALL=true patch_rtl_app --force; }
    [ "$HAD_APP_SELECTOR" = true ] && { FORCE_INSTALL=true patch_selector_app; }
    [ "$HAD_APP_EXPERIMENTS" = true ] && { FORCE_INSTALL=true patch_experiments_app; }
    [ "$HAD_APP_WINDOW_BOUNDS" = true ] && { FORCE_INSTALL=true patch_window_bounds_app; }

    log_success "Antigravity App update routine complete."
}

update_ide() {
    auto_detect_installations
    resolve_dynamic_urls
    log_info "Updating Antigravity IDE at ${IDE_INSTALL_DIR}..."
    detect_active_ide_patches
    log_info "Pre-update active IDE patches: Selector=${HAD_IDE_SELECTOR}, RTL=${HAD_IDE_RTL}, Experiments/Fork=${HAD_IDE_EXPERIMENTS}"

    install_binary "Antigravity-IDE" "$IDE_URL" "$TARGET_IDE_VER" "$IDE_INSTALL_DIR"
    setup_ide_shortcuts

    log_info "Re-applying previously applied IDE patches..."
    [ "$HAD_IDE_SELECTOR" = true ] && { FORCE_INSTALL=true patch_selector_ide; }
    [ "$HAD_IDE_RTL" = true ] && [ "$SKIP_RTL" != true ] && { FORCE_INSTALL=true patch_rtl_ide --force; }
    [ "$HAD_IDE_EXPERIMENTS" = true ] && { FORCE_INSTALL=true patch_experiments_ide; }

    if [ "$HAD_IDE_SELECTOR" = true ] || [ "$HAD_IDE_RTL" = true ] || [ "$HAD_IDE_EXPERIMENTS" = true ]; then
        fix_ide_checksums "${IDE_INSTALL_DIR}"
    fi
    log_success "Antigravity IDE update routine complete."
}

clean_cache() {
    log_info "Cleaning archive cache directory (${CACHE_DIR})..."
    rm -rf "${CACHE_DIR}"/*
    log_success "Archive cache cleared."
}
