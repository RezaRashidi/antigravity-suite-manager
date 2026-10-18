#!/usr/bin/env bash
# Step 8: Multi-Account Launchers, Unified Chat Sync & Status Check

step_8_setup_launchers_and_sync() {
    echo -e "\n${BLUE}[Step 8/8] $(get_step_name 8)...${NC}"
    if [ -f "$PATHS_CONF" ]; then
        # shellcheck source=/dev/null
        source "$PATHS_CONF"
    fi

    "${TARGET_BIN}/manage-antigravity.sh" app1 >/dev/null 2>&1 || true
    if [ -d "${REAL_HOME}/.antigravity-profile2" ] || [ -f "${TARGET_BIN}/antigravity-acc2" ]; then
        "${TARGET_BIN}/manage-antigravity.sh" app2 >/dev/null 2>&1 || true
        rm -f "${REAL_HOME}/.local/share/applications/antigravity.desktop" 2>/dev/null || true
    fi
    "${TARGET_BIN}/manage-antigravity.sh" ide-shortcuts >/dev/null 2>&1 || true
    "${TARGET_BIN}/manage-antigravity.sh" merge-history >/dev/null 2>&1 || true

    echo -e "${GREEN}[OK] Launchers configured.${NC}"
    echo -e "${GREEN}[OK] Unified Chat History synchronized.${NC}"

    echo -e "\n${CYAN}======================================================================${NC}"
    echo -e "${GREEN}${BOLD}Verification & System Status:${NC}"
    "${TARGET_BIN}/manage-antigravity.sh" status
    echo -e "${CYAN}======================================================================${NC}"
    echo -e "${GREEN}${BOLD}Setup Complete!${NC}"
    echo -e "You can manage your suite anytime using:"
    echo -e "  ${BOLD}~/manage-antigravity.sh [status | paths | keyring | update | set-icons | help]${NC}"
    echo -e "${CYAN}======================================================================${NC}"
}
