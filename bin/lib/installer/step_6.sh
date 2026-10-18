#!/usr/bin/env bash
# Step 6: Configure Keyring / Credential Storage Mode

step_6_configure_keyring() {
    echo -e "\n${BLUE}[Step 6/8] $(get_step_name 6)...${NC}"
    if [ ! -f "${TARGET_CONF}/keyring.conf" ]; then
        cat <<EOF > "${TARGET_CONF}/keyring.conf"
# Antigravity Keyring Storage Configuration
# Values: 'normal' (Basic file storage, no GNOME Keyring) or 'gnome' (GNOME Keyring)
KEYRING_MODE_APP1="normal"
KEYRING_MODE_APP2="normal"
KEYRING_MODE_IDE="normal"
EOF
    fi

    if [ "$NON_INTERACTIVE" != true ] && [ -t 0 ] && [ "$STEP_BY_STEP" = true ]; then
        echo -e "Storage options:"
        echo -e "  [1] Normal File Storage (Bypasses GNOME Keyring - Recommended)"
        echo -e "  [2] GNOME Keyring (Secret Service)"
        read -rp "Select credential storage mode [Default: 1]: " k_ans
        k_ans="${k_ans:-1}"
        if [ "$k_ans" = "2" ]; then
            python3 "${TARGET_BIN}/antigravity-keyring.py" set all gnome >/dev/null 2>&1 || true
            echo -e "${GREEN}[OK] Set storage mode to GNOME Keyring.${NC}"
        else
            python3 "${TARGET_BIN}/antigravity-keyring.py" set all normal >/dev/null 2>&1 || true
            echo -e "${GREEN}[OK] Set storage mode to Normal File Storage.${NC}"
        fi
    else
        # shellcheck source=/dev/null
        source "${TARGET_CONF}/keyring.conf" 2>/dev/null || true
        python3 "${TARGET_BIN}/antigravity-keyring.py" set app1 "${KEYRING_MODE_APP1:-normal}" >/dev/null 2>&1 || true
        python3 "${TARGET_BIN}/antigravity-keyring.py" set app2 "${KEYRING_MODE_APP2:-normal}" >/dev/null 2>&1 || true
        python3 "${TARGET_BIN}/antigravity-keyring.py" set ide "${KEYRING_MODE_IDE:-normal}" >/dev/null 2>&1 || true
        echo -e "${GREEN}[OK] Credential storage configured (App1: ${KEYRING_MODE_APP1:-normal}, App2: ${KEYRING_MODE_APP2:-normal}, IDE: ${KEYRING_MODE_IDE:-normal}).${NC}"
    fi
}
