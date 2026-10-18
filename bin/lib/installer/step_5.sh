#!/usr/bin/env bash
# Step 5: Configure Visual Icon Themes & Recolor

step_5_configure_icons() {
    echo -e "\n${BLUE}[Step 5/8] $(get_step_name 5)...${NC}"
    if [ ! -f "${TARGET_CONF}/icons.conf" ]; then
        cat <<EOF > "${TARGET_CONF}/icons.conf"
# Antigravity Suite Icon Configuration
ACC1_ICON_THEME="black"
ACC1_EMBLEM_COLOR="original"
ACC2_ICON_THEME="black"
ACC2_EMBLEM_COLOR="violet"
ACC2_RECOLOR="true"
IDE_ICON_THEME="white"
IDE_EMBLEM_COLOR="original"
EOF
    fi

    if [ "$NON_INTERACTIVE" != true ] && [ -t 0 ] && [ "$STEP_BY_STEP" = true ]; then
        read -rp "Would you like to customize Icon Themes now? [y/N] " ico_ans
        if [[ "$ico_ans" =~ ^[Yy]$ ]]; then
            "${TARGET_BIN}/manage-antigravity.sh" set-icons
        fi
    fi

    python3 "${TARGET_BIN}/antigravity-generate-icons.py" >/dev/null 2>&1 || true
    chown -R "${REAL_USER}:${REAL_USER}" "$TARGET_CONF" "$TARGET_ICONS" 2>/dev/null || true
    echo -e "${GREEN}[OK] Icon cache generated.${NC}"
}
