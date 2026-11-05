#!/usr/bin/env bash
# Antigravity IDE version checking and patch prerequisite helpers

MIN_IDE_VERSION="${MIN_IDE_VERSION:-2.6.0}"

get_ide_installed_version() {
    local target_ide="${1:-$IDE_INSTALL_DIR}"
    if [ -z "$target_ide" ] || [ ! -d "$target_ide" ]; then
        for c in "$target_ide" "$IDE_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_IDE" "/opt/antigravity-ide" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity-ide"; do
            [ -n "$c" ] && [ -d "${c}/resources/app" ] && { target_ide="$c"; break; }
        done
    fi
    [ -z "$target_ide" ] && return 1
    python3 -c "
import json, os
target = '${target_ide}'
v = None
prod = os.path.join(target, 'resources', 'app', 'product.json')
if os.path.isfile(prod):
    try:
        with open(prod, 'r', encoding='utf-8') as f:
            d = json.load(f)
            v = d.get('ideVersion') or d.get('version')
    except Exception: pass
if not v:
    pkg = os.path.join(target, 'resources', 'app', 'package.json')
    if os.path.isfile(pkg):
        try:
            with open(pkg, 'r', encoding='utf-8') as f:
                d = json.load(f)
                v = d.get('version')
        except Exception: pass
print(v or '')
" 2>/dev/null || true
}

check_ide_min_version() {
    local target_ide="${1:-$IDE_INSTALL_DIR}"
    local min_ver="${2:-$MIN_IDE_VERSION}"
    [ -z "$min_ver" ] && min_ver="2.6.0"

    if [ -z "$target_ide" ] || [ ! -d "$target_ide" ]; then
        for c in "$target_ide" "$IDE_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_IDE" "/opt/antigravity-ide" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity-ide"; do
            [ -n "$c" ] && [ -d "${c}/resources/app" ] && { target_ide="$c"; IDE_INSTALL_DIR="$c"; break; }
        done
    fi

    if [ -z "$target_ide" ] || [ ! -d "$target_ide" ]; then
        log_err "Antigravity IDE directory not found at '${target_ide:-<undefined>}'. Cannot patch IDE."
        return 1
    fi

    local ide_ver
    ide_ver=$(get_ide_installed_version "$target_ide")

    if [ -z "$ide_ver" ] || [ "$ide_ver" = "Unknown" ]; then
        log_err "Unable to determine Antigravity IDE version at ${target_ide}. Antigravity IDE v${min_ver}+ is required."
        return 1
    fi

    local is_ge
    is_ge=$(python3 -c "
import re, sys
def parse(s):
    nums = [int(x) for x in re.findall(r'\d+', str(s))]
    while len(nums) < 3: nums.append(0)
    return tuple(nums)
sys.exit(0 if parse('${ide_ver}') >= parse('${min_ver}') else 1)
" 2>/dev/null && echo "yes" || echo "no")

    if [ "$is_ge" != "yes" ]; then
        log_err "Antigravity IDE v${min_ver}+ is required for patching (detected: v${ide_ver} at ${target_ide})."
        log_info "Please update Antigravity IDE first ('manage-antigravity.sh update ide' or install latest release)."
        return 1
    fi

    return 0
}
