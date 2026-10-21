#!/usr/bin/env bash
# Step 4: Install Scripts, Libraries, Master Icons & Symlink

step_4_deploy_scripts() {
    echo -e "\n${BLUE}[Step 4/8] $(get_step_name 4)...${NC}"
    mkdir -p "$TARGET_BIN" "$TARGET_ICONS" "$TARGET_CONF"

    # Deploy all bin scripts and libraries
    if [ -d "${SCRIPT_DIR}/bin" ]; then
        for f in "${SCRIPT_DIR}/bin"/*; do
            [ -f "$f" ] || continue
            cp -f "$f" "${TARGET_BIN}/" 2>/dev/null || sudo -n cp -f "$f" "${TARGET_BIN}/" 2>/dev/null || true
            chmod +x "${TARGET_BIN}/$(basename "$f")" 2>/dev/null || true
        done
        if [ -d "${SCRIPT_DIR}/bin/lib" ]; then
            mkdir -p "${TARGET_BIN}/lib"
            cp -rf "${SCRIPT_DIR}/bin/lib/"* "${TARGET_BIN}/lib/" 2>/dev/null || sudo -n cp -rf "${SCRIPT_DIR}/bin/lib/"* "${TARGET_BIN}/lib/" 2>/dev/null || true
        fi
    fi

    # Deploy install.sh entrypoint
    if [ -f "${SCRIPT_DIR}/install.sh" ]; then
        cp -f "${SCRIPT_DIR}/install.sh" "${TARGET_BIN}/" 2>/dev/null || sudo -n cp -f "${SCRIPT_DIR}/install.sh" "${TARGET_BIN}/" 2>/dev/null || true
        chmod +x "${TARGET_BIN}/install.sh" 2>/dev/null || true
        ln -sfn "${TARGET_BIN}/install.sh" "${REAL_HOME}/install.sh" 2>/dev/null || true
    fi

    # Register antigravity_suite package in user and system site-packages
    local py_ver
    py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3")
    local user_sp="${REAL_HOME}/.local/lib/python${py_ver}/site-packages"
    mkdir -p "$user_sp" 2>/dev/null || true
    echo "${SCRIPT_DIR}/src" > "${user_sp}/antigravity_suite.pth" 2>/dev/null || true
    chown -R "${REAL_USER}:${REAL_USER}" "${REAL_HOME}/.local/lib" 2>/dev/null || true
    local sys_sp
    sys_sp=$(python3 -c 'import site; print(site.getsitepackages()[0])' 2>/dev/null || true)
    if [ -n "$sys_sp" ] && [ -w "$sys_sp" ]; then
        echo "${SCRIPT_DIR}/src" > "${sys_sp}/antigravity_suite.pth" 2>/dev/null || true
    fi

    if [ -d "${SCRIPT_DIR}/assets" ]; then
        cp -f "${SCRIPT_DIR}/assets"/antigravity-master-*.png "${TARGET_ICONS}/" 2>/dev/null || true
        [ -f "${TARGET_ICONS}/antigravity-master-black.png" ] && cp -f "${TARGET_ICONS}/antigravity-master-black.png" "${TARGET_ICONS}/antigravity-1.png" 2>/dev/null || true
        [ -f "${TARGET_ICONS}/antigravity-master-black.png" ] && cp -f "${TARGET_ICONS}/antigravity-master-black.png" "${TARGET_ICONS}/antigravity.png" 2>/dev/null || true
        [ -f "${TARGET_ICONS}/antigravity-master-white.png" ] && cp -f "${TARGET_ICONS}/antigravity-master-white.png" "${TARGET_ICONS}/antigravity-ide.png" 2>/dev/null || true
    fi

    ln -sfn "${TARGET_BIN}/manage-antigravity.sh" "${REAL_HOME}/manage-antigravity.sh"
    chown -R "${REAL_USER}:${REAL_USER}" "$TARGET_BIN" "$TARGET_ICONS" "$TARGET_CONF" "${REAL_HOME}/manage-antigravity.sh" "${REAL_HOME}/install.sh" 2>/dev/null || true
    echo -e "${GREEN}[OK] Installed management tools to ${TARGET_BIN} and symlinked ~/manage-antigravity.sh${NC}"
}
