#!/usr/bin/env bash
# Installation detection logic delegating to antigravity-detect.py

get_detect_script() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    if [ -f "${script_dir}/bin/antigravity-detect.py" ]; then
        echo "${script_dir}/bin/antigravity-detect.py"
    elif [ -f "${script_dir}/antigravity-detect.py" ]; then
        echo "${script_dir}/antigravity-detect.py"
    elif [ -f "${LOCAL_BIN}/antigravity-detect.py" ]; then
        echo "${LOCAL_BIN}/antigravity-detect.py"
    fi
}

auto_detect_installations() {
    local detect_script
    detect_script=$(get_detect_script)
    local prev_app_dir="$APP_INSTALL_DIR"
    local prev_ide_dir="$IDE_INSTALL_DIR"

    if [ -n "$detect_script" ]; then
        local env_vars
        env_vars=$(python3 "$detect_script" --env 2>/dev/null || true)
        if [ -n "$env_vars" ]; then
            eval "$env_vars"
        fi
    fi

    if [ "$CLI_APP_DIR_SPECIFIED" = true ]; then
        APP_INSTALL_DIR="$prev_app_dir"
    else
        APP_INSTALL_DIR="${ANTIGRAVITY_APP_DIR:-${APP_INSTALL_DIR:-$ANTIGRAVITY_DETECTED_APP}}"
        if [ -z "$APP_INSTALL_DIR" ] || [ ! -d "$APP_INSTALL_DIR" ]; then
            for c in "$ANTIGRAVITY_DETECTED_APP" "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity" "${REAL_HOME}/.local/share/antigravity"; do
                [ -n "$c" ] && [ -d "$c" ] && { APP_INSTALL_DIR="$c"; break; }
            done
        fi
        APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/antigravity2}"
    fi

    if [ "$CLI_IDE_DIR_SPECIFIED" = true ]; then
        IDE_INSTALL_DIR="$prev_ide_dir"
    else
        IDE_INSTALL_DIR="${ANTIGRAVITY_IDE_DIR:-${IDE_INSTALL_DIR:-$ANTIGRAVITY_DETECTED_IDE}}"
        if [ -z "$IDE_INSTALL_DIR" ] || [ ! -d "$IDE_INSTALL_DIR" ]; then
            for c in "$ANTIGRAVITY_DETECTED_IDE" "/opt/antigravity-ide" "/opt/antigravity" "${REAL_HOME}/.local/share/antigravity-ide"; do
                [ -n "$c" ] && [ -d "$c" ] && { IDE_INSTALL_DIR="$c"; break; }
            done
        fi
        IDE_INSTALL_DIR="${IDE_INSTALL_DIR:-/opt/antigravity}"
    fi

    if [ -n "$ANTIGRAVITY_DETECTED_APP_VER" ] && [ -z "$TARGET_APP_VER" ]; then
        TARGET_APP_VER="$ANTIGRAVITY_DETECTED_APP_VER"
    fi
    if [ -n "$ANTIGRAVITY_DETECTED_IDE_VER" ] && [ -z "$TARGET_IDE_VER" ]; then
        TARGET_IDE_VER="$ANTIGRAVITY_DETECTED_IDE_VER"
    fi
}

detect_installations() {
    local detect_script
    detect_script=$(get_detect_script)
    if [ -n "$detect_script" ]; then
        python3 "$detect_script"
    else
        log_err "antigravity-detect.py not found in script dir or ${LOCAL_BIN}."
    fi
}
