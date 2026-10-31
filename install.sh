#!/usr/bin/env bash
# ==============================================================================
# Antigravity Suite Manager - Automated Installer & Manager
# Modularized CLI runner & unified entrypoint
# ==============================================================================
set -e

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" 2>/dev/null && pwd)"
LIB_INSTALLER_DIR="${SCRIPT_DIR}/bin/lib/installer"
[ ! -d "$LIB_INSTALLER_DIR" ] && LIB_INSTALLER_DIR="${SCRIPT_DIR}/lib/installer"
[ ! -d "$LIB_INSTALLER_DIR" ] && LIB_INSTALLER_DIR="${HOME}/.local/bin/lib/installer"

# Locate unified manage-antigravity.sh
MANAGE_SH="${SCRIPT_DIR}/bin/manage-antigravity.sh"
[ ! -f "$MANAGE_SH" ] && MANAGE_SH="${SCRIPT_DIR}/manage-antigravity.sh"
[ ! -f "$MANAGE_SH" ] && MANAGE_SH="${HOME}/.local/bin/manage-antigravity.sh"
[ ! -f "$MANAGE_SH" ] && MANAGE_SH="${HOME}/.antigravity-suite-manager/bin/manage-antigravity.sh"

# If manage-antigravity.sh is NOT found, handle automated bootstrapping (curl | bash)
if [ ! -f "$MANAGE_SH" ]; then
    if [ -f "${LIB_INSTALLER_DIR}/bootstrap.sh" ]; then
        # shellcheck source=/dev/null
        source "${LIB_INSTALLER_DIR}/env.sh" 2>/dev/null || true
        # shellcheck source=/dev/null
        source "${LIB_INSTALLER_DIR}/bootstrap.sh"
        check_auto_bootstrap "$@"
    else
        # Standalone curl pipe fallback bootstrap
        REAL_USER="${REAL_USER:-${SUDO_USER:-${USER:-$LOGNAME}}}"
        REAL_HOME="${REAL_HOME:-$HOME}"
        if [ -z "$REAL_HOME" ] && [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
            REAL_HOME="$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6 || echo "/home/${REAL_USER}")"
        fi
        INSTALL_REPO_DIR="${REAL_HOME}/.antigravity-suite-manager"
        CYAN='\033[1;36m'
        BOLD='\033[1m'
        NC='\033[0m'
        BLUE='\033[1;38;5;75m'
        GREEN='\033[1;32m'

        echo -e "${CYAN}======================================================================${NC}"
        echo -e "${BOLD}${CYAN}   Bootstrapping Antigravity Suite Manager from GitHub...${NC}"
        echo -e "${CYAN}======================================================================${NC}"

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

        MANAGE_SH="${INSTALL_REPO_DIR}/bin/manage-antigravity.sh"
        [ ! -f "$MANAGE_SH" ] && MANAGE_SH="${REAL_HOME}/.local/bin/manage-antigravity.sh"

        if [ -r /dev/tty ] && [ ! -t 0 ]; then
            exec bash "$MANAGE_SH" "$@" < /dev/tty
        else
            exec bash "$MANAGE_SH" "$@"
        fi
    fi
fi

if [ -f "$MANAGE_SH" ]; then
    exec "$MANAGE_SH" "$@"
else
    echo "Error: manage-antigravity.sh not found." >&2
    exit 1
fi
