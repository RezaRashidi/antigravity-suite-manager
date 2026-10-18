#!/usr/bin/env bash
# Interactive instance creation wizard orchestrator.

prompt_instance_type() {
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${CYAN}         Create Antigravity Instance / Profile       ${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo "Select Instance Type:\n  1) Antigravity App (Desktop App)\n  2) Antigravity IDE (VS Code Edition)"
    read -rp "Enter choice [1-2]: " t_choice
    case "$t_choice" in 2|ide|IDE) echo "ide" ;; *) echo "app" ;; esac
}

prompt_history_mode() {
    echo -e "\nSelect History Mode:\n  1) Shared (Unified conversations & artifacts) [Default]\n  2) Isolated (Dedicated private conversations)"
    read -rp "Enter choice [1-2]: " m_choice
    case "$m_choice" in 2|isolated|private) echo "isolated" ;; *) echo "shared" ;; esac
}

prompt_accent_hue() {
    echo -e "\nSelect Icon Accent Color / Recolor Glow:\n  1) Violet / Magenta (0.52)\n  2) Emerald Green (0.33)\n  3) Amber Orange (0.12)\n  4) Royal Sapphire Blue (0.60)\n  5) Ruby Rose (0.85)\n  6) Cyan / Teal (0.45)\n  7) Original Colors (No shift)"
    read -rp "Enter choice [1-7, default: 1]: " h_choice
    case "$h_choice" in 2) echo "0.33" ;; 3) echo "0.12" ;; 4) echo "0.60" ;; 5) echo "0.85" ;; 6) echo "0.45" ;; 7) echo "" ;; *) echo "0.52" ;; esac
}

create_instance() {
    local itype="$1" iid="$2" imode="$3" itheme="${4:-black}" ihue="$5"
    auto_detect_installations
    APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/Antigravity-x64}"
    IDE_INSTALL_DIR="${IDE_INSTALL_DIR:-/opt/antigravity-ide}"

    [ -z "$itype" ] && itype=$(prompt_instance_type)
    itype=$(echo "$itype" | tr '[:upper:]' '[:lower:]')
    if [ "$itype" != "app" ] && [ "$itype" != "ide" ]; then
        log_err "Invalid instance type '${itype}'. Must be 'app' or 'ide'."
        return 1
    fi

    if [ -z "$iid" ]; then
        read -rp "Enter instance name or number (e.g. 3, 4, client, work, dev): " iid
    fi
    iid=$(echo "$iid" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9_-]+/-/g; s/^-+|-+$//g')
    [ -z "$iid" ] && { log_err "Instance name cannot be empty."; return 1; }

    [ -z "$imode" ] && imode=$(prompt_history_mode)
    imode=$(echo "$imode" | tr '[:upper:]' '[:lower:]')
    [ -z "$ihue" ] && ihue=$(prompt_accent_hue)

    log_info "Creating ${itype^^} instance '${iid}' [History: ${imode^^}, Theme: ${itheme}, Hue: ${ihue:-None}]..."
    if [ "$itype" = "app" ]; then
        create_app_instance "$iid" "$imode" "$itheme" "$ihue"
    else
        create_ide_instance "$iid" "$imode" "$itheme" "$ihue"
    fi

    log_success "Instance '${iid}' (${itype^^}) created successfully!"
    echo -e "  • Launcher:       ${BOLD}${LOCAL_BIN}/antigravity-${itype}-${iid}${NC}"
    echo -e "  • Desktop Entry:  ${BOLD}${LOCAL_APPS}/antigravity-${itype}-${iid}.desktop${NC}"
    echo -e "  • Profile Dir:    ${BOLD}${REAL_HOME}/.antigravity-${itype}-profile-${iid}${NC}"
    echo -e "  • History Mode:   ${BOLD}${imode^^}${NC}"
}
