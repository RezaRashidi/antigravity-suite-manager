#!/usr/bin/env bash
# Auto-bootstrap installer if executed outside cloned repository (curl / pipe)

check_auto_bootstrap() {
    if [ -f "${SCRIPT_DIR}/bin/manage-antigravity.sh" ] || [ -f "${SCRIPT_DIR}/manage-antigravity.sh" ] || [ -f "${REAL_HOME}/.local/bin/manage-antigravity.sh" ] || [ -f "${REAL_HOME}/.antigravity-suite-manager/bin/manage-antigravity.sh" ]; then
        return 0
    fi
    if [ -z "${BASH_SOURCE[1]:-}" ] || [ ! -f "${SCRIPT_DIR}/src/scale_icon.c" ] || [ ! -f "${SCRIPT_DIR}/bin/manage-antigravity.sh" ]; then
        echo -e "${CYAN}======================================================================${NC}"
        echo -e "${BOLD}${CYAN}   Bootstrapping Antigravity Suite Manager from GitHub...${NC}"
        echo -e "${CYAN}======================================================================${NC}"

        INSTALL_REPO_DIR="${REAL_HOME}/.antigravity-suite-manager"
        if [ -d "${INSTALL_REPO_DIR}/.git" ]; then
            echo -e "${BLUE}Existing repository found at ${INSTALL_REPO_DIR}, updating...${NC}"
            git -C "$INSTALL_REPO_DIR" fetch --depth=1 origin main 2>/dev/null || true
            git -C "$INSTALL_REPO_DIR" clean -fd 2>/dev/null || true
            git -C "$INSTALL_REPO_DIR" reset --hard origin/main 2>/dev/null || git -C "$INSTALL_REPO_DIR" pull --ff-only 2>/dev/null || true
        elif command -v git >/dev/null 2>&1; then
            echo -e "${BLUE}Cloning repository to ${INSTALL_REPO_DIR}...${NC}"
            git clone --depth=1 https://github.com/RezaRashidi/antigravity-suite-manager.git "$INSTALL_REPO_DIR"
        else
            echo -e "${BLUE}Downloading repository to ${INSTALL_REPO_DIR}...${NC}"
            mkdir -p "$INSTALL_REPO_DIR"
            curl -fsSL https://github.com/RezaRashidi/antigravity-suite-manager/archive/refs/heads/main.tar.gz | tar -xz -C "$INSTALL_REPO_DIR" --strip-components=1
        fi

        echo -e "${GREEN}[OK] Repository ready at ${INSTALL_REPO_DIR}${NC}\n"

        mkdir -p "${REAL_HOME}/.local/bin" "${REAL_HOME}/.local/share/icons" "${REAL_HOME}/.config/antigravity"
        if [ -d "${INSTALL_REPO_DIR}/bin" ]; then
            cp -rf "${INSTALL_REPO_DIR}/bin/"* "${REAL_HOME}/.local/bin/" 2>/dev/null || sudo -n cp -rf "${INSTALL_REPO_DIR}/bin/"* "${REAL_HOME}/.local/bin/" 2>/dev/null || true
            chmod +x "${REAL_HOME}/.local/bin/"* 2>/dev/null || true
        fi
        if [ -d "${INSTALL_REPO_DIR}/assets" ]; then
            cp -f "${INSTALL_REPO_DIR}/assets"/antigravity-master-*.png "${REAL_HOME}/.local/share/icons/" 2>/dev/null || true
        fi

        # Register python package and symlinks
        local py_ver
        py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3")
        local user_sp="${REAL_HOME}/.local/lib/python${py_ver}/site-packages"
        mkdir -p "$user_sp" 2>/dev/null || true
        echo "${INSTALL_REPO_DIR}/src" > "${user_sp}/antigravity_suite.pth" 2>/dev/null || true

        ln -sfn "${REAL_HOME}/.local/bin/manage-antigravity.sh" "${REAL_HOME}/.local/bin/manage-antigravity" 2>/dev/null || true
        ln -sfn "${REAL_HOME}/.local/bin/manage-antigravity.sh" "${REAL_HOME}/.local/bin/antigravity-suite" 2>/dev/null || true
        ln -sfn "${REAL_HOME}/.local/bin/manage-antigravity.sh" "${REAL_HOME}/manage-antigravity.sh" 2>/dev/null || true
        ln -sfn "${REAL_HOME}/.local/bin/manage-antigravity.sh" "${REAL_HOME}/manage-antigravity" 2>/dev/null || true

        if [ -w "/usr/local/bin" ]; then
            ln -sfn "${REAL_HOME}/.local/bin/manage-antigravity.sh" "/usr/local/bin/manage-antigravity" 2>/dev/null || true
            ln -sfn "${REAL_HOME}/.local/bin/manage-antigravity.sh" "/usr/local/bin/manage-antigravity.sh" 2>/dev/null || true
            ln -sfn "${REAL_HOME}/.local/bin/manage-antigravity.sh" "/usr/local/bin/antigravity-suite" 2>/dev/null || true
        elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
            sudo -n ln -sfn "${REAL_HOME}/.local/bin/manage-antigravity.sh" "/usr/local/bin/manage-antigravity" 2>/dev/null || true
            sudo -n ln -sfn "${REAL_HOME}/.local/bin/manage-antigravity.sh" "/usr/local/bin/manage-antigravity.sh" 2>/dev/null || true
            sudo -n ln -sfn "${REAL_HOME}/.local/bin/manage-antigravity.sh" "/usr/local/bin/antigravity-suite" 2>/dev/null || true
        fi

        for rc in "${REAL_HOME}/.bashrc" "${REAL_HOME}/.zshrc" "${REAL_HOME}/.profile"; do
            if [ -f "$rc" ]; then
                if ! grep -q '\.local/bin' "$rc" 2>/dev/null; then
                    echo -e '\n# Added by Antigravity Suite Manager\nexport PATH="${HOME}/.local/bin:${PATH}"' >> "$rc" 2>/dev/null || true
                fi
            fi
        done

        if [ -r /dev/tty ] && [ ! -t 0 ]; then
            exec bash "${INSTALL_REPO_DIR}/install.sh" "$@" < /dev/tty
        else
            exec bash "${INSTALL_REPO_DIR}/install.sh" "$@"
        fi
    fi
}
