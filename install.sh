#!/usr/bin/env bash
# ==============================================================================
# Antigravity Suite Manager - Step-by-Step Automated Installer & Wizard
# Modularized CLI runner
# ==============================================================================
set -eo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" 2>/dev/null && pwd)"
LIB_INSTALLER_DIR="${SCRIPT_DIR}/bin/lib/installer"

if [ ! -d "$LIB_INSTALLER_DIR" ]; then
    LIB_INSTALLER_DIR="${HOME}/.local/bin/lib/installer"
fi

# Source environment definitions
# shellcheck source=/dev/null
source "${LIB_INSTALLER_DIR}/env.sh"

# Handle automated bootstrapping if invoked via curl | bash
# shellcheck source=/dev/null
source "${LIB_INSTALLER_DIR}/bootstrap.sh"
check_auto_bootstrap "$@"

# Source step definitions and runner engine
for mod in "${LIB_INSTALLER_DIR}"/*.sh; do
    [ -f "$mod" ] || continue
    case "$(basename "$mod")" in
        env.sh|bootstrap.sh) continue ;;
        *)
            # shellcheck source=/dev/null
            source "$mod"
            ;;
    esac
done

parse_installer_cli "$@"
run_installer_workflow
