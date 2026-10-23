#!/usr/bin/env bash
# Uninstallation routines for Antigravity IDE binaries and data

uninstall_ide() {
    local with_data=false auto_yes=false
    for arg in "$@"; do
        case "$arg" in
            --with-data|--purge|--purge-data) with_data=true ;;
            --keep-data|--no-data) with_data=false ;;
            -y|--yes) auto_yes=true ;;
        esac
    done

    if [ "$auto_yes" != true ]; then
        echo -e "${YELLOW}WARNING: This will uninstall Antigravity IDE binaries and shortcuts.${NC}"
        [ "$with_data" = true ] && echo -e "${RED}ALL IDE user settings, workspace state, and profiles will also be DELETED!${NC}"
        read -rp "Are you sure you want to proceed? [y/N]: " conf
        case "$conf" in
            y|Y|yes|YES) ;;
            *) log_info "Uninstallation aborted."; return 0 ;;
        esac
    fi

    auto_detect_installations 2>/dev/null || true
    ensure_rtl_dirs

    log_info "Stopping active Antigravity IDE processes..."
    pkill -f "${IDE_INSTALL_DIR}/antigravity-ide" 2>/dev/null || true
    pkill -f "class=antigravity-ide" 2>/dev/null || true
    sleep 1

    if [ "$with_data" = true ]; then
        log_info "Creating safety backup of IDE data before purge..."
        local m_script
        m_script="$(get_migration_script 2>/dev/null || true)"
        if [ -n "$m_script" ] && [ -f "$m_script" ]; then
            python3 "$m_script" create-backup --category ide --label "pre_uninstall_ide" 2>/dev/null || true
        fi
        log_info "Purging Antigravity IDE data..."
        rm -rf "${REAL_HOME}/.config/Antigravity IDE"
        rm -rf "${REAL_HOME}/.gemide"
        rm -rf "${REAL_HOME}/.gemini-ide"
        rm -rf "${REAL_HOME}/.gemini/antigravity-ide"
        for d in "${REAL_HOME}"/.antigravity-ide-profile-*; do [ -d "$d" ] && rm -rf "$d"; done
    else
        log_info "Preserving Antigravity IDE data and configurations."
    fi

    log_info "Removing Antigravity IDE launchers and desktop entries..."
    rm -f "${LOCAL_BIN}/antigravity-ide"
    for b in "${LOCAL_BIN}"/antigravity-ide-*; do [ -f "$b" ] && rm -f "$b"; done
    rm -f "${LOCAL_APPS}/antigravity-ide.desktop"
    for d in "${LOCAL_APPS}"/antigravity-ide-*.desktop; do [ -f "$d" ] && rm -f "$d"; done
    update-desktop-database "${LOCAL_APPS}" 2>/dev/null || true

    if [ -n "$IDE_INSTALL_DIR" ] && [ -d "$IDE_INSTALL_DIR" ]; then
        log_info "Removing Antigravity IDE binaries at ${IDE_INSTALL_DIR}..."
        if [ "$EUID" -eq 0 ] || [ -w "$IDE_INSTALL_DIR" ]; then
            rm -rf "$IDE_INSTALL_DIR"
        else
            sudo rm -rf "$IDE_INSTALL_DIR" 2>/dev/null || rm -rf "$IDE_INSTALL_DIR" 2>/dev/null || true
        fi
    fi

    log_success "Antigravity IDE successfully uninstalled."
}
