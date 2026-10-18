#!/usr/bin/env bash
# Installer environment, paths, colors, and configuration targets

GREEN="\033[1;32m"
BLUE="\033[1;38;5;75m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
CYAN="\033[1;36m"
NC="\033[0m"
BOLD="\033[1m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." 2>/dev/null && pwd)"

REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6)
REAL_HOME="${REAL_HOME:-$HOME}"
export REAL_USER REAL_HOME

TARGET_BIN="${REAL_HOME}/.local/bin"
TARGET_ICONS="${REAL_HOME}/.local/share/icons"
TARGET_CONF="${REAL_HOME}/.config/antigravity"
PATHS_CONF="${TARGET_CONF}/paths.conf"
ICONS_CONF="${TARGET_CONF}/icons.conf"
KEYRING_CONF="${TARGET_CONF}/keyring.conf"

START_STEP=1
ONLY_STEP=0
STEP_BY_STEP=false
NON_INTERACTIVE=false
INSTALL_ANTIGRAVITY=false
CLI_APP_DIR=""
CLI_IDE_DIR=""

if [ -f "$PATHS_CONF" ]; then
    # shellcheck source=/dev/null
    source "$PATHS_CONF"
fi
APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/antigravity2}"
IDE_INSTALL_DIR="${IDE_INSTALL_DIR:-/opt/antigravity}"
