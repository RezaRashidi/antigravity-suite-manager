#!/usr/bin/env bash
# Antigravity Suite Manager - Automated Installer & Manager
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
    local t_bin="${1:-$TARGET_BIN}" r_dir="${2:-$INSTALL_REPO_DIR}"
    local py_ver
    py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3")
    local user_sp="${REAL_HOME}/.local/lib/python${py_ver}/site-packages"
    mkdir -p "$user_sp" "$t_bin" 2>/dev/null || true
    echo "${r_dir}/src" > "${user_sp}/antigravity_suite.pth" 2>/dev/null || true

    for lk in "${t_bin}/manage-antigravity" "${t_bin}/antigravity-suite" "${REAL_HOME}/manage-antigravity.sh" "${REAL_HOME}/manage-antigravity"; do
        ln -sfn "${t_bin}/manage-antigravity.sh" "$lk" 2>/dev/null || true
    done
    [ -f "${t_bin}/install.sh" ] && ln -sfn "${t_bin}/install.sh" "${REAL_HOME}/install.sh" 2>/dev/null || true

    local sys_target=""
    [ -w "/usr/local/bin" ] && sys_target="/usr/local/bin"
    [ -z "$sys_target" ] && command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null && sys_target="sudo"
    if [ "$sys_target" = "/usr/local/bin" ]; then
        for lk in manage-antigravity manage-antigravity.sh antigravity-suite; do
            ln -sfn "${t_bin}/manage-antigravity.sh" "/usr/local/bin/${lk}" 2>/dev/null || true
        done
    elif [ "$sys_target" = "sudo" ]; then
        for lk in manage-antigravity manage-antigravity.sh antigravity-suite; do
            sudo -n ln -sfn "${t_bin}/manage-antigravity.sh" "/usr/local/bin/${lk}" 2>/dev/null || true
        done
    fi

    for rc in "${REAL_HOME}/.bashrc" "${REAL_HOME}/.zshrc" "${REAL_HOME}/.profile"; do
        [ -f "$rc" ] && ! grep -q '\.local/bin' "$rc" 2>/dev/null && \
            echo -e '\n# Added by Antigravity Suite Manager\nexport PATH="${HOME}/.local/bin:${PATH}"' >> "$rc" 2>/dev/null || true
    done
}

IS_LOCAL_REPO=false
if [ -f "${SCRIPT_DIR}/src/antigravity_suite/__init__.py" ] && [ -f "${SCRIPT_DIR}/bin/manage-antigravity.sh" ]; then
    IS_LOCAL_REPO=true
fi

if [ "$IS_LOCAL_REPO" = true ]; then
    setup_suite_env_and_links "$TARGET_BIN" "$SCRIPT_DIR"
    export ANTIGRAVITY_SUITE_DIR="$SCRIPT_DIR"
    export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"
    exec bash "${SCRIPT_DIR}/bin/manage-antigravity.sh" "$@"
fi

echo -e "\033[1;36m=== Bootstrapping Antigravity Suite Manager from GitHub... ===\033[0m"
if [ -d "${INSTALL_REPO_DIR}/.git" ]; then
    git -C "$INSTALL_REPO_DIR" fetch --depth=1 origin main 2>/dev/null || true
    git -C "$INSTALL_REPO_DIR" clean -fd 2>/dev/null || true
    git -C "$INSTALL_REPO_DIR" reset --hard origin/main 2>/dev/null || git -C "$INSTALL_REPO_DIR" pull --ff-only 2>/dev/null || true
elif command -v git >/dev/null 2>&1; then
    git clone --depth=1 https://github.com/RezaRashidi/antigravity-suite-manager.git "$INSTALL_REPO_DIR"
else
    mkdir -p "$INSTALL_REPO_DIR"
    curl -fsSL https://github.com/RezaRashidi/antigravity-suite-manager/archive/refs/heads/main.tar.gz | tar -xz -C "$INSTALL_REPO_DIR" --strip-components=1
fi

mkdir -p "$TARGET_BIN" "$TARGET_ICONS" "$TARGET_CONF"
if [ -d "${INSTALL_REPO_DIR}/bin" ]; then
    for f in "${INSTALL_REPO_DIR}/bin"/*; do
        [ -f "$f" ] || continue
        ln -sfn "$f" "${TARGET_BIN}/$(basename "$f")" 2>/dev/null || cp -f "$f" "${TARGET_BIN}/" 2>/dev/null || true
        chmod +x "${TARGET_BIN}/$(basename "$f")" 2>/dev/null || true
    done
    if [ -d "${INSTALL_REPO_DIR}/bin/lib" ]; then
        [ ! -L "${TARGET_BIN}/lib" ] && rm -rf "${TARGET_BIN}/lib" 2>/dev/null || true
        ln -sfn "${INSTALL_REPO_DIR}/bin/lib" "${TARGET_BIN}/lib" 2>/dev/null || true
    fi
fi
[ -f "${INSTALL_REPO_DIR}/install.sh" ] && cp -f "${INSTALL_REPO_DIR}/install.sh" "${TARGET_BIN}/" 2>/dev/null && chmod +x "${TARGET_BIN}/install.sh" 2>/dev/null || true
[ -d "${INSTALL_REPO_DIR}/assets" ] && cp -f "${INSTALL_REPO_DIR}/assets"/antigravity-master-*.png "${TARGET_ICONS}/" 2>/dev/null || true

setup_suite_env_and_links "$TARGET_BIN" "$INSTALL_REPO_DIR"
export ANTIGRAVITY_SUITE_DIR="$INSTALL_REPO_DIR"
export PYTHONPATH="${INSTALL_REPO_DIR}/src:${PYTHONPATH:-}"

MANAGE_SH="${INSTALL_REPO_DIR}/bin/manage-antigravity.sh"
[ ! -f "$MANAGE_SH" ] && MANAGE_SH="${TARGET_BIN}/manage-antigravity.sh"
if [ -r /dev/tty ] && [ ! -t 0 ]; then
    exec bash "$MANAGE_SH" "$@" < /dev/tty
fi
exec bash "$MANAGE_SH" "$@"
