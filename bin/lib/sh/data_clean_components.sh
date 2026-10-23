#!/usr/bin/env bash
# Component data cleaning routines for Antigravity App, IDE, and History

clean_app_data() {
    local auto_yes=false no_backup=false
    for arg in "$@"; do
        [ "$arg" = "-y" ] || [ "$arg" = "--yes" ] && auto_yes=true
        [ "$arg" = "--no-backup" ] && no_backup=true
    done

    if [ "$auto_yes" != true ]; then
        echo -e "${YELLOW}WARNING: This will delete Antigravity App user data, profiles, and caches.${NC}"
        read -rp "Are you sure you want to proceed? [y/N]: " conf
        case "$conf" in
            y|Y|yes|YES) ;;
            *) log_info "Operation cancelled."; return 0 ;;
        esac
    fi

    log_info "Cleaning Antigravity Desktop App data..."
    local m_script
    m_script="$(get_migration_script)"
    if [ -f "$m_script" ]; then
        local b_flag=""
        [ "$no_backup" = true ] && b_flag="--no-backup"
        python3 "$m_script" clean-data app -y $b_flag
    else
        pkill -f "class=antigravity" 2>/dev/null || true
        rm -rf "${REAL_HOME}/.config/Antigravity" "${PROFILE2_DIR}"
        for d in "${REAL_HOME}"/.antigravity-profile-app-*; do [ -d "$d" ] && rm -rf "$d"; done
        log_success "Antigravity App data cleaned."
    fi
}

clean_ide_data() {
    local auto_yes=false no_backup=false
    for arg in "$@"; do
        [ "$arg" = "-y" ] || [ "$arg" = "--yes" ] && auto_yes=true
        [ "$arg" = "--no-backup" ] && no_backup=true
    done

    if [ "$auto_yes" != true ]; then
        echo -e "${YELLOW}WARNING: This will delete Antigravity IDE state, settings, and profiles.${NC}"
        read -rp "Are you sure you want to proceed? [y/N]: " conf
        case "$conf" in
            y|Y|yes|YES) ;;
            *) log_info "Operation cancelled."; return 0 ;;
        esac
    fi

    log_info "Cleaning Antigravity IDE data..."
    local m_script
    m_script="$(get_migration_script)"
    if [ -f "$m_script" ]; then
        local b_flag=""
        [ "$no_backup" = true ] && b_flag="--no-backup"
        python3 "$m_script" clean-data ide -y $b_flag
    else
        pkill -f "antigravity-ide" 2>/dev/null || true
        rm -rf "${REAL_HOME}/.config/Antigravity IDE" "${REAL_HOME}/.gemide" "${REAL_HOME}/.gemini-ide" "${REAL_HOME}/.gemini/antigravity-ide"
        for d in "${REAL_HOME}"/.antigravity-ide-profile-*; do [ -d "$d" ] && rm -rf "$d"; done
        log_success "Antigravity IDE data cleaned."
    fi
}

clean_history_data() {
    local auto_yes=false no_backup=false
    for arg in "$@"; do
        [ "$arg" = "-y" ] || [ "$arg" = "--yes" ] && auto_yes=true
        [ "$arg" = "--no-backup" ] && no_backup=true
    done

    if [ "$auto_yes" != true ]; then
        echo -e "${RED}WARNING: This will delete shared conversation databases, brain artifacts, and summaries!${NC}"
        read -rp "Are you sure you want to proceed? [y/N]: " conf
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
        python3 "$m_script" clean-data history -y $b_flag
    else
        rm -rf "${SHARED_CONV_DIR}/conversations" "${SHARED_CONV_DIR}/brain" "${SHARED_CONV_DIR}/annotations"
        rm -f "${SHARED_CONV_DIR}"/*summaries* "${SHARED_CONV_DIR}"/*.pb
        mkdir -p "${SHARED_CONV_DIR}/conversations" "${SHARED_CONV_DIR}/brain"
        log_success "Conversation history cleaned."
    fi
}
