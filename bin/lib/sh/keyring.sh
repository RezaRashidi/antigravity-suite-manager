#!/usr/bin/env bash
# Keyring and credential storage management routines

keyring_command() {
    local sdir
    sdir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    local tool=""
    if [ -f "${sdir}/antigravity-keyring.py" ]; then
        tool="${sdir}/antigravity-keyring.py"
    elif [ -f "${LOCAL_BIN}/antigravity-keyring.py" ]; then
        tool="${LOCAL_BIN}/antigravity-keyring.py"
    fi
    if [ -z "$tool" ]; then
        log_err "antigravity-keyring.py not found in ${sdir} or ${LOCAL_BIN}."
        return 1
    fi
    python3 "$tool" "$@"
}

keyring_status() {
    keyring_command status
}

keyring_purge() {
    keyring_command purge
}

set_keyring_mode() {
    local target="${1:-all}"
    local mode="${2:-normal}"
    keyring_command set "$target" "$mode"
}

configure_keyring_interactive() {
    local has_acc2=false
    [ -f "${LOCAL_BIN}/antigravity-acc2" ] && [ -d "${PROFILE2_DIR}" ] && has_acc2=true

    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${CYAN}   Configure Keyring & Credential Storage Mode       ${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    if [ "$has_acc2" = true ]; then
        echo "1) Switch Account 1 to Normal File Storage (Bypass GNOME Keyring)"
        echo "2) Switch Account 1 to GNOME Keyring (Secret Service)"
        echo "3) Switch Account 2 to Normal File Storage (Bypass GNOME Keyring)"
        echo "4) Switch Account 2 to GNOME Keyring (Secret Service)"
    else
        echo "1) Switch Antigravity App to Normal File Storage (Bypass GNOME Keyring)"
        echo "2) Switch Antigravity App to GNOME Keyring (Secret Service)"
        echo "3) Switch Antigravity IDE to Normal File Storage (Bypass GNOME Keyring)"
        echo "4) Switch Antigravity IDE to GNOME Keyring (Secret Service)"
    fi
    echo "5) Switch ALL Instances to Normal File Storage (Bypass Everywhere)"
    echo "6) Switch ALL Instances to GNOME Keyring"
    echo "7) Purge Antigravity Credentials from GNOME Keyring"
    echo "8) View Detailed Keyring & Credential Status"
    echo "0) Cancel / Back"
    echo -e "${CYAN}-----------------------------------------------------${NC}"
    read -rp "Select an option [0-8]: " kchoice

    case "$kchoice" in
        1) set_keyring_mode "app1" "normal" ;;
        2) set_keyring_mode "app1" "gnome" ;;
        3) [ "$has_acc2" = true ] && set_keyring_mode "app2" "normal" || set_keyring_mode "ide" "normal" ;;
        4) [ "$has_acc2" = true ] && set_keyring_mode "app2" "gnome" || set_keyring_mode "ide" "gnome" ;;
        5) set_keyring_mode "all" "normal" ;;
        6) set_keyring_mode "all" "gnome" ;;
        7) keyring_purge ;;
        8) keyring_status ;;
        0) return 0 ;;
        *) log_err "Invalid selection." ;;
    esac
}
