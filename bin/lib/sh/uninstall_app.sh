#!/usr/bin/env bash
# Uninstallation routines for Antigravity Desktop App binaries and data

uninstall_app() {
    local with_data=false auto_yes=false
    for arg in "$@"; do
        case "$arg" in
            --with-data|--purge|--purge-data) with_data=true ;;
            --keep-data|--no-data) with_data=false ;;
            -y|--yes) auto_yes=true ;;
        esac
    done

    if [ "$auto_yes" != true ]; then
        echo -e "${YELLOW}WARNING: This will uninstall Antigravity Desktop App binaries and shortcuts.${NC}"
        [ "$with_data" = true ] && echo -e "${RED}ALL App user configurations, profiles, and sessions will also be DELETED!${NC}"
        read -rp "Are you sure you want to proceed? [y/N]: " conf
        case "$conf" in
            y|Y|yes|YES) ;;
            *) log_info "Uninstallation aborted."; return 0 ;;
        esac
    fi

    auto_detect_installations 2>/dev/null || true
    ensure_app_install_dir

    log_info "Stopping active Antigravity App processes..."
    pkill -f "${APP_INSTALL_DIR}/antigravity" 2>/dev/null || true
    pkill -f "class=antigravity" 2>/dev/null || true
    pkill -f "class=antigravity-1" 2>/dev/null || true
    pkill -f "class=antigravity-2" 2>/dev/null || true
    pkill -f "class=antigravity-app-" 2>/dev/null || true
    sleep 1

    if [ "$with_data" = true ]; then
        log_info "Creating safety backup of App data before purge..."
        local m_script
        m_script="$(get_migration_script 2>/dev/null || true)"
        if [ -n "$m_script" ] && [ -f "$m_script" ]; then
            python3 "$m_script" create-backup --category app --label "pre_uninstall_app" 2>/dev/null || true
        fi
        log_info "Purging Antigravity App data..."
        rm -rf "${REAL_HOME}/.config/Antigravity"
        rm -rf "${PROFILE2_DIR}"
        for d in "${REAL_HOME}"/.antigravity-profile-app-*; do [ -d "$d" ] && rm -rf "$d"; done
    else
        log_info "Preserving Antigravity App data and user configurations."
    fi

    log_info "Removing Antigravity App launchers and desktop entries..."
    rm -f "${LOCAL_BIN}/antigravity" "${LOCAL_BIN}/antigravity-1" "${LOCAL_BIN}/antigravity-acc2"
    for b in "${LOCAL_BIN}"/antigravity-app-*; do [ -f "$b" ] && rm -f "$b"; done
    rm -f "${LOCAL_APPS}/antigravity.desktop" "${LOCAL_APPS}/antigravity-1.desktop" "${LOCAL_APPS}/antigravity-2.desktop"
    for d in "${LOCAL_APPS}"/antigravity-app-*.desktop; do [ -f "$d" ] && rm -f "$d"; done
    update-desktop-database "${LOCAL_APPS}" 2>/dev/null || true

    if [ -n "$APP_INSTALL_DIR" ] && [ -d "$APP_INSTALL_DIR" ]; then
        log_info "Removing Antigravity App binaries at ${APP_INSTALL_DIR}..."
        if [ "$EUID" -eq 0 ] || [ -w "$APP_INSTALL_DIR" ]; then
            rm -rf "$APP_INSTALL_DIR"
        else
            sudo rm -rf "$APP_INSTALL_DIR" 2>/dev/null || rm -rf "$APP_INSTALL_DIR" 2>/dev/null || true
        fi
    fi

    log_success "Antigravity App successfully uninstalled."
}
