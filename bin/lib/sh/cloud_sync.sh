#!/usr/bin/env bash
# Cloud Synchronization Bash Orchestrator

find_cloud_sync_script() {
    local sdir
    sdir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    for cand in "${sdir}/bin/antigravity-cloud-sync.py" "${LOCAL_BIN}/antigravity-cloud-sync.py" "${sdir}/antigravity-cloud-sync.py"; do
        if [ -f "$cand" ]; then echo "$cand"; return 0; fi
    done
    return 1
}

dispatch_cloud_sync() {
    local py_script
    py_script="$(find_cloud_sync_script)"
    if [ -z "$py_script" ]; then
        log_err "antigravity-cloud-sync.py not found."
        return 1
    fi

    if [ $# -gt 0 ]; then
        python3 "$py_script" "$@"
        return $?
    fi

    interactive_cloud_sync "$py_script"
}

interactive_cloud_sync() {
    local py_script="$1"
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${CYAN}   Antigravity Cloud Synchronization (Rclone)        ${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo "1) View Cloud Sync Status & Available Remotes"
    echo "2) Push Local Chats to Cloud (Flush WAL & Upload)"
    echo "3) Pull Remote Chats (Fast-Forward, Provision & Merge)"
    echo "4) Configure Cloud Remote Name (Default: agy-vault)"
    echo "0) Cancel / Back"
    echo -e "${CYAN}-----------------------------------------------------${NC}"
    read -rp "Select an option [0-4]: " cchoice

    case "$cchoice" in
        1) python3 "$py_script" status ;;
        2) python3 "$py_script" push ;;
        3) python3 "$py_script" pull ;;
        4)
            read -rp "Enter Rclone Remote Name (e.g., agy-vault): " new_rem
            if [ -n "$new_rem" ]; then
                python3 "$py_script" set-remote "$new_rem"
            fi
            ;;
        0) return 0 ;;
        *) log_err "Invalid selection." ;;
    esac
}
