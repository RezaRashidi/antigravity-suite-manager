#!/usr/bin/env bash
# Instance listing and removal routines.

list_instances() {
    local list_py="${LOCAL_BIN}/lib/sh/instance_list.py"
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    [ -f "${script_dir}/instance_list.py" ] && list_py="${script_dir}/instance_list.py"
    python3 "$list_py" "$REAL_HOME" "$PROFILE2_DIR" "$SHARED_CONV_DIR"
}

remove_instance() {
    local itype="$1" iid="$2"
    if [ -z "$itype" ] || [ -z "$iid" ]; then
        echo "Usage: $(basename "$0") remove-instance [app|ide] [instance_id]"
        return 1
    fi
    itype=$(echo "$itype" | tr '[:upper:]' '[:lower:]')
    local wm_class="" profile_dir="" launcher="" desktop=""

    if [ "$itype" = "app" ]; then
        if [ "$iid" = "2" ] || [ "$iid" = "acc2" ]; then
            wm_class="antigravity-2" profile_dir="${PROFILE2_DIR}"
            launcher="${LOCAL_BIN}/antigravity-acc2" desktop="${LOCAL_APPS}/antigravity-2.desktop"
        else
            wm_class="antigravity-app-${iid}" profile_dir="${REAL_HOME}/.antigravity-profile-app-${iid}"
            launcher="${LOCAL_BIN}/antigravity-app-${iid}" desktop="${LOCAL_APPS}/antigravity-app-${iid}.desktop"
        fi
    elif [ "$itype" = "ide" ]; then
        if [ "$iid" = "1" ] || [ "$iid" = "default" ]; then
            wm_class="antigravity-ide" profile_dir="${REAL_HOME}/.gemini/antigravity-ide"
            launcher="${LOCAL_BIN}/antigravity-ide" desktop="${LOCAL_APPS}/antigravity-ide.desktop"
        else
            wm_class="antigravity-ide-${iid}" profile_dir="${REAL_HOME}/.antigravity-ide-profile-${iid}"
            launcher="${LOCAL_BIN}/antigravity-ide-${iid}" desktop="${LOCAL_APPS}/antigravity-ide-${iid}.desktop"
        fi
    fi

    log_warn "Removing instance ${itype^^} '${iid}'..."
    rm -f "$launcher" "$desktop" "${LOCAL_ICONS}/${wm_class}.png" "${LOCAL_ICONS}/hicolor"/*/apps/"${wm_class}.png"
    update-desktop-database "$LOCAL_APPS" 2>/dev/null || true

    if [ -d "$profile_dir" ]; then
        log_info "Backing up profile directory before removal..."
        mv "$profile_dir" "${profile_dir}.removed_bak_$(date +%s)"
    fi
    log_success "Instance ${itype^^} '${iid}' successfully removed."
    [ "$itype" = "app" ] && setup_account_1
}
