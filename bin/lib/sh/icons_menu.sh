#!/usr/bin/env bash
# Interactive icon configuration menu

configure_icons_interactive() {
    local target="${1:-all}"
    case "$target" in
        app1|acc1|1)
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "${CYAN}   Configure Antigravity (Account 1) Icon            ${NC}"
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "Current: BG: ${BOLD}${ACC1_ICON_THEME}${NC} | Emblem: ${BOLD}${ACC1_EMBLEM_COLOR}${NC}"
            echo -e "${CYAN}-----------------------------------------------------${NC}"
            prompt_acc1_icon
            ;;
        ide)
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "${CYAN}        Configure Antigravity IDE Icon               ${NC}"
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "Current: BG: ${BOLD}${IDE_ICON_THEME}${NC} | Emblem: ${BOLD}${IDE_EMBLEM_COLOR}${NC}"
            echo -e "${CYAN}-----------------------------------------------------${NC}"
            prompt_ide_icon
            ;;
        app2|acc2|2)
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "${CYAN}   Configure Antigravity (Account 2) Icon            ${NC}"
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "Current: BG: ${BOLD}${ACC2_ICON_THEME}${NC} | Emblem: ${BOLD}${ACC2_EMBLEM_COLOR}${NC}"
            echo -e "${CYAN}-----------------------------------------------------${NC}"
            prompt_acc2_icon
            ;;
        *)
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "${CYAN}        Configure Antigravity Suite Icons            ${NC}"
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "Current Configuration:"
            echo -e "  • Antigravity 1:    BG: ${BOLD}${ACC1_ICON_THEME}${NC} | Emblem: ${BOLD}${ACC1_EMBLEM_COLOR}${NC}"
            echo -e "  • Antigravity IDE:  BG: ${BOLD}${IDE_ICON_THEME}${NC} | Emblem: ${BOLD}${IDE_EMBLEM_COLOR}${NC}"
            if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
                echo -e "  • Antigravity 2:    BG: ${BOLD}${ACC2_ICON_THEME}${NC} | Emblem: ${BOLD}${ACC2_EMBLEM_COLOR}${NC}"
            fi
            echo -e "${CYAN}-----------------------------------------------------${NC}"
            prompt_acc1_icon
            prompt_ide_icon
            if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
                prompt_acc2_icon
            fi
            ;;
    esac
    apply_icons_config
}
