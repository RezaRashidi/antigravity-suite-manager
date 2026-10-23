#!/usr/bin/env bash
# Helper routines for RTL patch directory detection, runner, and checksum fixes

ensure_rtl_dirs() {
    auto_detect_installations 2>/dev/null || true
    if [ -z "$APP_INSTALL_DIR" ] || [ ! -f "${APP_INSTALL_DIR}/resources/app.asar" ]; then
        for c in "$APP_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_APP" "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity"; do
            [ -n "$c" ] && [ -f "${c}/resources/app.asar" ] && { APP_INSTALL_DIR="$c"; break; }
        done
    fi
    if [ -z "$IDE_INSTALL_DIR" ] || [ ! -d "${IDE_INSTALL_DIR}/resources/app/out" ]; then
        for c in "$IDE_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_IDE" "/opt/antigravity-ide" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity-ide"; do
            [ -n "$c" ] && [ -d "${c}/resources/app/out" ] && { IDE_INSTALL_DIR="$c"; break; }
        done
    fi
}

run_antigravity_rtl() {
    if command -v antigravity-rtl >/dev/null 2>&1; then
        antigravity-rtl "$@"
    elif [ -x "${REAL_HOME:-$HOME}/.local/bin/antigravity-rtl" ]; then
        "${REAL_HOME:-$HOME}/.local/bin/antigravity-rtl" "$@"
    elif [ -x "${REAL_HOME:-$HOME}/.local/node_modules/.bin/antigravity-rtl" ]; then
        "${REAL_HOME:-$HOME}/.local/node_modules/.bin/antigravity-rtl" "$@"
    elif command -v npx >/dev/null 2>&1; then
        npx --yes antigravity-rtl@latest "$@"
    else
        log_err "Neither 'antigravity-rtl' nor 'npx' is available."
        return 1
    fi
}

fix_ide_checksums() {
    local target_ide="${1:-$IDE_INSTALL_DIR}"
    [ ! -d "$target_ide" ] && return 0
    local cs_tool="${LOCAL_BIN}/antigravity-checksums.py"
    if [ ! -f "$cs_tool" ]; then
        local s_dir
        s_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
        [ -f "${s_dir}/bin/antigravity-checksums.py" ] && cs_tool="${s_dir}/bin/antigravity-checksums.py"
    fi
    if [ -f "$cs_tool" ]; then
        python3 "$cs_tool" "$target_ide" 2>/dev/null || true
    fi
}
