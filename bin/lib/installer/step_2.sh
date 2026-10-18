#!/usr/bin/env bash
# Step 2: Configure / Change Installation Paths & Targets

step_2_configure_paths() {
    echo -e "\n${BLUE}[Step 2/8] $(get_step_name 2)...${NC}"
    local DETECT_SCRIPT="${SCRIPT_DIR}/bin/antigravity-detect.py"
    if [ ! -f "$DETECT_SCRIPT" ] && [ -n "${INSTALL_REPO_DIR:-}" ]; then
        DETECT_SCRIPT="${INSTALL_REPO_DIR}/bin/antigravity-detect.py"
    fi
    if [ ! -f "$DETECT_SCRIPT" ]; then
        DETECT_SCRIPT="${TARGET_BIN}/antigravity-detect.py"
    fi

    if [ -f "$DETECT_SCRIPT" ]; then
        if [ -n "$CLI_APP_DIR" ] || [ -n "$CLI_IDE_DIR" ]; then
            python3 "$DETECT_SCRIPT" --set-app-dir "${CLI_APP_DIR:-$APP_INSTALL_DIR}" --set-ide-dir "${CLI_IDE_DIR:-$IDE_INSTALL_DIR}"
        elif [ "$NON_INTERACTIVE" = true ]; then
            python3 "$DETECT_SCRIPT" --set-defaults-if-missing
        else
            python3 "$DETECT_SCRIPT" --configure-paths
        fi
    else
        mkdir -p "$TARGET_CONF"
        local local_custom="${CUSTOM_ANTIGRAVITY_PATHS:-}"
        if [ -f "$PATHS_CONF" ] && [ -z "$local_custom" ]; then
            local_custom=$(grep -E '^(CUSTOM_ANTIGRAVITY_PATHS|CUSTOM_PATHS)=' "$PATHS_CONF" | head -n 1 | cut -d'=' -f2- | tr -d '"' | tr -d "'")
        fi
        cat <<EOF > "$PATHS_CONF"
# Antigravity Suite Installation Paths Configuration
APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/antigravity2}"
IDE_INSTALL_DIR="${IDE_INSTALL_DIR:-/opt/antigravity}"
EOF
        if [ -n "$local_custom" ]; then
            echo "CUSTOM_ANTIGRAVITY_PATHS=\"${local_custom}\"" >> "$PATHS_CONF"
        fi
    fi

    if [ -f "$PATHS_CONF" ]; then
        # shellcheck source=/dev/null
        source "$PATHS_CONF"
    fi
    echo -e "${GREEN}[OK] Configured App: ${APP_INSTALL_DIR:-/opt/antigravity2} | IDE: ${IDE_INSTALL_DIR:-/opt/antigravity}${NC}"
}
