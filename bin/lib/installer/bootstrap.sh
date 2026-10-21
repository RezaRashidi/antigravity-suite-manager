#!/usr/bin/env bash
# Auto-bootstrap installer if executed outside cloned repository (curl / pipe)

check_auto_bootstrap() {
    if [ -f "${SCRIPT_DIR}/bin/manage-antigravity.sh" ] || [ -f "${SCRIPT_DIR}/manage-antigravity.sh" ] || [ -f "${REAL_HOME}/.local/bin/manage-antigravity.sh" ]; then
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

        if [ -r /dev/tty ] && [ ! -t 0 ]; then
            exec bash "${INSTALL_REPO_DIR}/install.sh" "$@" < /dev/tty
        else
            exec bash "${INSTALL_REPO_DIR}/install.sh" "$@"
        fi
    fi
}
