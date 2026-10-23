#!/usr/bin/env bash
# Suite-level uninstallation and interactive uninstallation menu

uninstall_all() {
    local with_data=false auto_yes=false
    for arg in "$@"; do
        case "$arg" in
            --with-data|--purge|--purge-data) with_data=true ;;
            --keep-data|--no-data) with_data=false ;;
            -y|--yes) auto_yes=true ;;
        esac
    done

    if [ "$auto_yes" != true ]; then
        echo -e "${RED}=====================================================${NC}"
        echo -e "${BOLD}${RED}  WARNING: FULL ANTIGRAVITY SUITE UNINSTALLATION     ${NC}"
        echo -e "${RED}=====================================================${NC}"
        echo "This will uninstall BOTH Antigravity App and Antigravity IDE."
        if [ "$with_data" = true ]; then
            echo -e "${RED}ALL data, chat history, brain artifacts, and configs will be DELETED!${NC}"
        else
            echo "All user data, chat history, and configs will be PRESERVED."
        fi
        read -rp "Are you sure you want to proceed? [y/N]: " conf
        case "$conf" in
            y|Y|yes|YES) ;;
            *) log_info "Uninstallation aborted."; return 0 ;;
        esac
    fi

    # Stop sync daemon
    systemctl --user stop antigravity-sync.service 2>/dev/null || true
    systemctl --user disable antigravity-sync.service 2>/dev/null || true
    pkill -f "antigravity-apply-icon.py --daemon" 2>/dev/null || true
    pkill -f "antigravity-merge-history.py" 2>/dev/null || true

    if [ "$with_data" = true ]; then
        uninstall_app --with-data -y
        uninstall_ide --with-data -y
        log_info "Purging shared Gemini and suite data..."
        rm -rf "${SHARED_GEMINI_DIR}"
        # Preserve backups directory inside config
        if [ -d "${REAL_HOME}/.config/antigravity" ]; then
            find "${REAL_HOME}/.config/antigravity" -mindepth 1 -maxdepth 1 ! -name backups -exec rm -rf {} + 2>/dev/null || true
        fi
    else
        uninstall_app --keep-data -y
        uninstall_ide --keep-data -y
    fi

    log_success "Complete Antigravity Suite uninstallation finished."
}

uninstall_menu_interactive() {
    echo -e "\n${CYAN}=====================================================${NC}"
    echo -e "${BOLD}${CYAN}            Uninstall Antigravity Suite              ${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo "1) Uninstall Antigravity Desktop App (Keep User Data)"
    echo "2) Uninstall Antigravity Desktop App (Purge All App Data)"
    echo "3) Uninstall Antigravity IDE (Keep User Data)"
    echo "4) Uninstall Antigravity IDE (Purge All IDE Data)"
    echo "5) Uninstall Both App & IDE (Keep User Data)"
    echo "6) Uninstall Everything (Purge All Binaries & User Data)"
    echo "0) Return"
    echo -e "${CYAN}-----------------------------------------------------${NC}"
    read -rp "Select an option [0-6]: " uchoice
    case "$uchoice" in
        1) uninstall_app --keep-data ;;
        2) uninstall_app --with-data ;;
        3) uninstall_ide --keep-data ;;
        4) uninstall_ide --with-data ;;
        5) uninstall_all --keep-data ;;
        6) uninstall_all --with-data ;;
        *) return 0 ;;
    esac
}
