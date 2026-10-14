#!/usr/bin/env bash
# ==============================================================================
# Antigravity Suite Manager - Automated Installer
# Installs CLI tools, C resampler, and icon assets to user environment.
# ==============================================================================
set -eo pipefail

GREEN="\033[1;32m"
BLUE="\033[1;34m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
CYAN="\033[1;36m"
NC="\033[0m"
BOLD="\033[1m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_BIN="${HOME}/.local/bin"
TARGET_ICONS="${HOME}/.local/share/icons"
TARGET_CONF="${HOME}/.config/antigravity"

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}             Antigravity Suite Manager Installer                      ${NC}"
echo -e "${CYAN}======================================================================${NC}"

# 1. Verify Prerequisites
echo -e "${BLUE}[1/5] Checking build and runtime dependencies...${NC}"
MISSING=()
for cmd in python3 gcc tar curl; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        MISSING+=("$cmd")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${RED}[ERROR] Missing required packages: ${MISSING[*]}${NC}"
    echo -e "${YELLOW}Please install them first (e.g. sudo apt install ${MISSING[*]})${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Core dependencies verified.${NC}"

# 2. Prepare directories
echo -e "${BLUE}[2/5] Creating user directories...${NC}"
mkdir -p "$TARGET_BIN" "$TARGET_ICONS" "$TARGET_CONF"

# 3. Compile C Bicubic Resampler
echo -e "${BLUE}[3/5] Compiling Catmull-Rom bicubic image resampler...${NC}"
if [ -f "${SCRIPT_DIR}/src/scale_icon.c" ]; then
    gcc -O3 -Wall "${SCRIPT_DIR}/src/scale_icon.c" -lm -o "${TARGET_BIN}/scale_icon"
    chmod +x "${TARGET_BIN}/scale_icon"
    echo -e "${GREEN}[OK] Resampler compiled to ${TARGET_BIN}/scale_icon${NC}"
else
    echo -e "${YELLOW}[WARN] src/scale_icon.c not found, skipping compilation.${NC}"
fi

# 4. Install binaries and assets
echo -e "${BLUE}[4/5] Installing scripts and master icon assets...${NC}"
cp -f "${SCRIPT_DIR}/bin/manage-antigravity.sh" "${TARGET_BIN}/"
cp -f "${SCRIPT_DIR}/bin/antigravity-generate-icons.py" "${TARGET_BIN}/"
cp -f "${SCRIPT_DIR}/bin/antigravity-apply-icon.py" "${TARGET_BIN}/"
chmod +x "${TARGET_BIN}/manage-antigravity.sh" "${TARGET_BIN}/antigravity-generate-icons.py" "${TARGET_BIN}/antigravity-apply-icon.py"

# Master icons
if [ -d "${SCRIPT_DIR}/assets" ]; then
    cp -f "${SCRIPT_DIR}/assets"/antigravity-master-*.png "${TARGET_ICONS}/" 2>/dev/null || true
fi

# Symlink to ~/manage-antigravity.sh
ln -sfn "${TARGET_BIN}/manage-antigravity.sh" "${HOME}/manage-antigravity.sh"

# Default configuration if not exists
if [ ! -f "${TARGET_CONF}/icons.conf" ]; then
    cat <<EOF > "${TARGET_CONF}/icons.conf"
# Antigravity Suite Icon Configuration
ACC1_ICON_THEME="black"
ACC2_ICON_THEME="black"
ACC2_RECOLOR="true"
IDE_ICON_THEME="white"
EOF
fi

# 5. Initialize icons
echo -e "${BLUE}[5/5] Initializing icon cache and resolutions...${NC}"
python3 "${TARGET_BIN}/antigravity-generate-icons.py" >/dev/null 2>&1 || true

echo -e "${CYAN}======================================================================${NC}"
echo -e "${GREEN}${BOLD}Installation Complete!${NC}"
echo -e "You can now manage your Antigravity suite using:"
echo -e "  ${BOLD}~/manage-antigravity.sh [status | update | set-icons | help]${NC}"
echo -e "Or add ${TARGET_BIN} to your PATH to run ${BOLD}manage-antigravity.sh${NC} directly."
echo -e "${CYAN}======================================================================${NC}"
