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

# If manage-antigravity.sh is NOT found, handle automated bootstrapping (curl | bash)
if [ ! -f "$MANAGE_SH" ]; then
    if [ -f "${LIB_INSTALLER_DIR}/bootstrap.sh" ]; then
        # shellcheck source=/dev/null
        source "${LIB_INSTALLER_DIR}/env.sh" 2>/dev/null || true
        # shellcheck source=/dev/null
        source "${LIB_INSTALLER_DIR}/bootstrap.sh"
        check_auto_bootstrap "$@"
    fi
fi

if [ -f "$MANAGE_SH" ]; then
    exec "$MANAGE_SH" "$@"
else
    echo "Error: manage-antigravity.sh not found." >&2
    exit 1
fi
