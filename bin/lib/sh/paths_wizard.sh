#!/usr/bin/env bash
# Installation paths configuration and setup wizard dispatch

find_detect_script() {
    local sdir
    sdir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    if [ -f "${sdir}/bin/antigravity-detect.py" ]; then
        echo "${sdir}/bin/antigravity-detect.py"
    elif [ -f "${sdir}/antigravity-detect.py" ]; then
        echo "${sdir}/antigravity-detect.py"
    elif [ -f "${LOCAL_BIN}/antigravity-detect.py" ]; then
        echo "${LOCAL_BIN}/antigravity-detect.py"
    fi
}

configure_paths() {
    local detect_script
    detect_script="$(find_detect_script)"
    if [ -z "$detect_script" ]; then
        log_err "antigravity-detect.py not found."
        return 1
    fi
    python3 "$detect_script" --configure-paths
    if [ -f "$PATHS_CONF" ]; then
        # shellcheck source=/dev/null
        source "$PATHS_CONF"
    fi
    if [ -t 0 ]; then
        read -rp "Re-generate desktop shortcuts with updated paths now? [Y/n] " regen_ans
        regen_ans="${regen_ans:-Y}"
        if [[ "$regen_ans" =~ ^[Yy]$ ]]; then
            setup_account_1
            if [ -d "$PROFILE2_DIR" ] && [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
                setup_account_2
            fi
            setup_ide_shortcuts
            log_success "Updated desktop launchers with new installation paths."
        fi
    fi
}

handle_paths_command() {
    local detect_script
    detect_script="$(find_detect_script)"
    if [ ${#CMD_ARGS[@]} -gt 0 ] && [ -n "$detect_script" ]; then
        python3 "$detect_script" "${CMD_ARGS[@]}"
        [ -f "$PATHS_CONF" ] && source "$PATHS_CONF"
    else
        configure_paths
    fi
}

handle_wizard_command() {
    local sdir
    sdir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    local installer=""
    for cand in "${sdir}/install.sh" "${REAL_HOME}/PhpstormProjects/antigravity-suite-manager/install.sh"; do
        [ -f "$cand" ] && installer="$cand" && break
    done
    if [ -n "$installer" ]; then
        exec "$installer" "${CMD_ARGS[@]}"
    else
        log_err "install.sh not found."
    fi
}
