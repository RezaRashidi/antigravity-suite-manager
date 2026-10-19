#!/usr/bin/env bash
# Step 7: Download & Install Google Antigravity Binaries

step_7_install_antigravity() {
    echo -e "\n${BLUE}[Step 7/8] $(get_step_name 7)...${NC}"
    if [ -f "$PATHS_CONF" ]; then
        # shellcheck source=/dev/null
        source "$PATHS_CONF"
    fi

    local app_target="${APP_INSTALL_DIR:-/opt/antigravity2}"
    local ide_target="${IDE_INSTALL_DIR:-/opt/antigravity}"

    local app_exists=false
    local ide_exists=false
    [ -f "${app_target}/resources/app.asar" ] && app_exists=true
    if [ -f "${ide_target}/resources/app/product.json" ] || [ -f "${ide_target}/resources/app/package.json" ]; then
        ide_exists=true
    fi

    local do_install=false
    if [ "$INSTALL_ANTIGRAVITY" = true ]; then
        do_install=true
    elif [ "$app_exists" = false ] || [ "$ide_exists" = false ]; then
        if [ "$NON_INTERACTIVE" = true ]; then
            do_install=true
        elif [ -t 0 ]; then
            echo -e "${YELLOW}Antigravity binaries not fully installed in target directories:${NC}"
            echo -e "  • App (${app_target}): $([ "$app_exists" = true ] && echo -e "${GREEN}Present${NC}" || echo -e "${RED}Missing${NC}")"
            echo -e "  • IDE (${ide_target}): $([ "$ide_exists" = true ] && echo -e "${GREEN}Present${NC}" || echo -e "${RED}Missing${NC}")"
            read -rp "Download and install Google Antigravity now? [Y/n] " inst_ans
            inst_ans="${inst_ans:-Y}"
            [[ "$inst_ans" =~ ^[Yy]$ ]] && do_install=true
        fi
    else
        echo -e "${GREEN}[OK] Antigravity App already present in ${app_target}${NC}"
        echo -e "${GREEN}[OK] Antigravity IDE already present in ${ide_target}${NC}"
        if [ "$NON_INTERACTIVE" != true ] && [ -t 0 ] && [ "$STEP_BY_STEP" = true ]; then
            read -rp "Reinstall/Update binaries from upstream now? [y/N] " re_ans
            [[ "$re_ans" =~ ^[Yy]$ ]] && do_install=true
        fi
    fi

    if [ "$do_install" = true ]; then
        echo -e "${GREEN}Installing / Updating Google Antigravity Suite into configured paths...${NC}"
        "${TARGET_BIN}/manage-antigravity.sh" install all --app-dir "$app_target" --ide-dir "$ide_target"
        "${TARGET_BIN}/manage-antigravity.sh" update-rtl
        "${TARGET_BIN}/manage-antigravity.sh" update-f5
        "${TARGET_BIN}/manage-antigravity.sh" checksums
    fi
}
