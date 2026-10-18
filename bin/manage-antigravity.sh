#!/usr/bin/env bash
# Antigravity & Antigravity IDE Suite Manager
# Main modular CLI entry point
set -e

# Wayland / X11 desktop environment flags
# --ozone-platform=x11
export ELECTRON_OZONE_PLATFORM_HINT="x11"

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" && pwd)"
LIB_SH_DIR=""
for cand in "${SCRIPT_DIR}/lib/sh" "/usr/local/bin/lib/sh" "${HOME}/.local/bin/lib/sh"; do
    if [ -d "$cand" ]; then
        LIB_SH_DIR="$cand"
        break
    fi
done

if [ -z "$LIB_SH_DIR" ]; then
    echo "Error: Antigravity bash library not found (searched ${SCRIPT_DIR}/lib/sh)" >&2
    exit 1
fi

# Source environment definitions first
# shellcheck source=/dev/null
source "${LIB_SH_DIR}/env.sh"

# Source all sub-scripts
for mod in "${LIB_SH_DIR}"/*.sh; do
    [ -f "$mod" ] || continue
    [ "$(basename "$mod")" = "env.sh" ] && continue
    # shellcheck source=/dev/null
    source "$mod"
done

# Parse CLI arguments and dispatch command
parse_cli_args "$@"
dispatch_command
