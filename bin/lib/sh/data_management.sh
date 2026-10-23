#!/usr/bin/env bash
# Full data purge and interactive data management menu

clean_all_data() {
    local auto_yes=false no_backup=false
    for arg in "$@"; do
        [ "$arg" = "-y" ] || [ "$arg" = "--yes" ] && auto_yes=true
        [ "$arg" = "--no-backup" ] && no_backup=true
    done

    if [ "$auto_yes" != true ]; then
        echo -e "${RED}=====================================================${NC}"
        echo -e "${BOLD}${RED}     WARNING: FULL ANTIGRAVITY DATA PURGE            ${NC}"
        echo -e "${RED}=====================================================${NC}"
        echo "This will delete ALL data (App, IDE, History, Brain, Configs)."
        read -rp "Are you absolutely sure you want to proceed? [y/N]: " conf
        case "$conf" in
            y|Y|yes|YES) ;;
            *) log_info "Operation cancelled."; return 0 ;;
        esac
    fi

    local m_script
    m_script="$(get_migration_script)"
    if [ -f "$m_script" ]; then
        local b_flag=""
        [ "$no_backup" = true ] && b_flag="--no-backup"
        python3 "$m_script" clean-data all -y $b_flag
    else
        clean_app_data -y --no-backup
        clean_ide_data -y --no-backup
        clean_history_data -y --no-backup
        log_success "All Antigravity data cleaned."
    fi
}

clean_data_interactive() {
    echo -e "\n${CYAN}=====================================================${NC}"
    echo -e "${BOLD}${CYAN}            Clean / Delete Antigravity Data          ${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo "1) Delete Antigravity Desktop App Data (Profiles & Sessions)"
    echo "2) Delete Antigravity IDE Data (VS Code State & Workspace)"
    echo "3) Delete Shared Conversation History & Brain Artifacts"
    echo "4) Delete ALL Antigravity Data (Full Clean Slate Reset)"
    echo "0) Return"
    echo -e "${CYAN}-----------------------------------------------------${NC}"
    read -rp "Select option [0-4]: " cchoice
    case "$cchoice" in
        1) clean_app_data ;;
        2) clean_ide_data ;;
        3) clean_history_data ;;
        4) clean_all_data ;;
        *) return 0 ;;
    esac
}
