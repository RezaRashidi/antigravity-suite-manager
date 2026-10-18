#!/usr/bin/env bash
# Environment, configuration paths, colors, and logging helpers.

CACHE_DIR="${ANTIGRAVITY_CACHE_DIR:-/tmp/antigravity-cache}"
APP_INSTALL_DIR="${ANTIGRAVITY_APP_DIR:-}"
IDE_INSTALL_DIR="${ANTIGRAVITY_IDE_DIR:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLI_APP_DIR_SPECIFIED=false
CLI_IDE_DIR_SPECIFIED=false

if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    REAL_USER="$SUDO_USER"
else
    REAL_USER="${USER:-$(whoami)}"
fi
REAL_HOME=$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6)
REAL_HOME="${REAL_HOME:-$HOME}"
export REAL_USER REAL_HOME

PROFILE2_DIR="${REAL_HOME}/.antigravity-profile2"
SHARED_GEMINI_DIR="${REAL_HOME}/.gemini"
SHARED_CONV_DIR="${SHARED_GEMINI_DIR}/antigravity"
SHARED_CONFIG_DIR="${SHARED_CONFIG_DIR:-${SHARED_GEMINI_DIR}/config}"

LOCAL_BIN="${REAL_HOME}/.local/bin"
LOCAL_APPS="${REAL_HOME}/.local/share/applications"
LOCAL_ICONS="${REAL_HOME}/.local/share/icons"

ICONS_CONF_DIR="${REAL_HOME}/.config/antigravity"
ICONS_CONF="${ICONS_CONF_DIR}/icons.conf"
ACC1_ICON_THEME="black"
ACC1_EMBLEM_COLOR="original"
ACC2_ICON_THEME="black"
ACC2_EMBLEM_COLOR="violet"
ACC2_RECOLOR="true"
IDE_ICON_THEME="white"
IDE_EMBLEM_COLOR="original"
CLI_ICON_GIVEN=false
[ -f "$ICONS_CONF" ] && source "$ICONS_CONF"

KEYRING_CONF="${ICONS_CONF_DIR}/keyring.conf"
KEYRING_MODE_APP1="normal"
KEYRING_MODE_APP2="normal"
KEYRING_MODE_IDE="normal"
[ -f "$KEYRING_CONF" ] && source "$KEYRING_CONF"

PATHS_CONF="${ICONS_CONF_DIR}/paths.conf"
[ -f "$PATHS_CONF" ] && source "$PATHS_CONF"

FORCE_INSTALL=false
USE_CACHE=true
SKIP_RTL=false
SKIP_F5=false
APP_URL=""
IDE_URL=""
TARGET_APP_VER=""
TARGET_IDE_VER=""

GREEN="\033[1;32m"
BLUE="\033[1;38;5;75m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
CYAN="\033[1;36m"
NC="\033[0m"
BOLD="\033[1m"

log_info() { echo -e "${BLUE}[INFO]${NC} $1" >&2; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1" >&2; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" >&2; }
log_err() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

mkdir -p "$LOCAL_BIN" "$LOCAL_APPS" "$LOCAL_ICONS" "$SHARED_CONV_DIR" "$SHARED_CONFIG_DIR" "$CACHE_DIR"
