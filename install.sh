#!/usr/bin/env bash
# ==============================================================================
# Antigravity Suite Manager - Automated Installer & Manager
# Modularized CLI runner & unified entrypoint
# ==============================================================================
set -e

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" 2>/dev/null && pwd)"

REAL_USER="${REAL_USER:-${SUDO_USER:-${USER:-$LOGNAME}}}"
REAL_HOME="${REAL_HOME:-$HOME}"
if [ -z "$REAL_HOME" ] && [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
    REAL_HOME="$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6 || echo "/home/${REAL_USER}")"
fi
INSTALL_REPO_DIR="${REAL_HOME}/.antigravity-suite-manager"
TARGET_BIN="${REAL_HOME}/.local/bin"
TARGET_ICONS="${REAL_HOME}/.local/share/icons"
TARGET_CONF="${REAL_HOME}/.config/antigravity"

setup_suite_env_and_links() {
    local t_bin="${1:-$TARGET_BIN}"
    local r_dir="${2:-$INSTALL_REPO_DIR}"

    # 1. Register Python site-packages .pth
    local py_ver
    py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3")
    local user_sp="${REAL_HOME}/.local/lib/python${py_ver}/site-packages"
    mkdir -p "$user_sp" 2>/dev/null || true
    echo "${r_dir}/src" > "${user_sp}/antigravity_suite.pth" 2>/dev/null || true

    # 2. Local bin symlinks
    ln -sfn "${t_bin}/manage-antigravity.sh" "${t_bin}/manage-antigravity" 2>/dev/null || true
    ln -sfn "${t_bin}/manage-antigravity.sh" "${t_bin}/antigravity-suite" 2>/dev/null || true
    ln -sfn "${t_bin}/manage-antigravity.sh" "${REAL_HOME}/manage-antigravity.sh" 2>/dev/null || true
    ln -sfn "${t_bin}/manage-antigravity.sh" "${REAL_HOME}/manage-antigravity" 2>/dev/null || true
    [ -f "${t_bin}/install.sh" ] && ln -sfn "${t_bin}/install.sh" "${REAL_HOME}/install.sh" 2>/dev/null || true

    # 3. System-wide /usr/local/bin symlinks
    if [ -w "/usr/local/bin" ]; then
        ln -sfn "${t_bin}/manage-antigravity.sh" "/usr/local/bin/manage-antigravity" 2>/dev/null || true
        ln -sfn "${t_bin}/manage-antigravity.sh" "/usr/local/bin/manage-antigravity.sh" 2>/dev/null || true
        ln -sfn "${t_bin}/manage-antigravity.sh" "/usr/local/bin/antigravity-suite" 2>/dev/null || true
    elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
        sudo -n ln -sfn "${t_bin}/manage-antigravity.sh" "/usr/local/bin/manage-antigravity" 2>/dev/null || true
        sudo -n ln -sfn "${t_bin}/manage-antigravity.sh" "/usr/local/bin/manage-antigravity.sh" 2>/dev/null || true
        sudo -n ln -sfn "${t_bin}/manage-antigravity.sh" "/usr/local/bin/antigravity-suite" 2>/dev/null || true
    fi

    # 4. Add ~/.local/bin to PATH across user shell profiles
    for rc in "${REAL_HOME}/.bashrc" "${REAL_HOME}/.zshrc" "${REAL_HOME}/.profile"; do
        if [ -f "$rc" ]; then
            if ! grep -q '\.local/bin' "$rc" 2>/dev/null; then
                echo -e '\n# Added by Antigravity Suite Manager\nexport PATH="${HOME}/.local/bin:${PATH}"' >> "$rc" 2>/dev/null || true
            fi
        fi
    done
}

# Determine execution mode: local repository clone vs curl/standalone bootstrap
IS_LOCAL_REPO=false
if [ -f "${SCRIPT_DIR}/src/antigravity_suite/__init__.py" ] && [ -f "${SCRIPT_DIR}/bin/manage-antigravity.sh" ]; then
    IS_LOCAL_REPO=true
fi

if [ "$IS_LOCAL_REPO" = true ]; then
    setup_suite_env_and_links "$TARGET_BIN" "$SCRIPT_DIR"
    export ANTIGRAVITY_SUITE_DIR="$SCRIPT_DIR"
    export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"
    exec bash "${SCRIPT_DIR}/bin/manage-antigravity.sh" "$@"
else
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

    mkdir -p "$TARGET_BIN" "$TARGET_ICONS" "$TARGET_CONF"
    if [ -d "${INSTALL_REPO_DIR}/bin" ]; then
        cp -rf "${INSTALL_REPO_DIR}/bin/"* "${TARGET_BIN}/" 2>/dev/null || sudo -n cp -rf "${INSTALL_REPO_DIR}/bin/"* "${TARGET_BIN}/" 2>/dev/null || true
        chmod +x "${TARGET_BIN}/"* 2>/dev/null || true
    fi
    if [ -f "${INSTALL_REPO_DIR}/install.sh" ]; then
        cp -f "${INSTALL_REPO_DIR}/install.sh" "${TARGET_BIN}/" 2>/dev/null || true
        chmod +x "${TARGET_BIN}/install.sh" 2>/dev/null || true
    fi
    if [ -d "${INSTALL_REPO_DIR}/assets" ]; then
        cp -f "${INSTALL_REPO_DIR}/assets"/antigravity-master-*.png "${TARGET_ICONS}/" 2>/dev/null || true
    fi

    setup_suite_env_and_links "$TARGET_BIN" "$INSTALL_REPO_DIR"

    export ANTIGRAVITY_SUITE_DIR="$INSTALL_REPO_DIR"
    export PYTHONPATH="${INSTALL_REPO_DIR}/src:${PYTHONPATH:-}"

    MANAGE_SH="${INSTALL_REPO_DIR}/bin/manage-antigravity.sh"
    [ ! -f "$MANAGE_SH" ] && MANAGE_SH="${TARGET_BIN}/manage-antigravity.sh"

    if [ -r /dev/tty ] && [ ! -t 0 ]; then
        exec bash "$MANAGE_SH" "$@" < /dev/tty
    else
        exec bash "$MANAGE_SH" "$@"
    fi
fi
