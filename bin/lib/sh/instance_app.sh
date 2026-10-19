#!/usr/bin/env bash
# Dynamic setup and configuration for Antigravity App instances (1, 2, N).

setup_app_profile_symlinks() {
    local prof="$1"
    mkdir -p "${prof}/.gemini/cache" "${prof}/.local/share"
    touch "${prof}/.gemini/cache/antigravity-keyring-unavailable"
    ln -sfn "$LOCAL_APPS" "${prof}/.local/share/applications"
    ln -sfn "$LOCAL_ICONS" "${prof}/.local/share/icons"
    ln -sfn "$SHARED_CONV_DIR" "${prof}/.gemini/antigravity"
    ln -sfn "$SHARED_CONFIG_DIR" "${prof}/.gemini/config"
    [ -f "$SHARED_GEMINI_DIR/GEMINI.md" ] && ln -sfn "$SHARED_GEMINI_DIR/GEMINI.md" "${prof}/.gemini/GEMINI.md"
    for sj in projects.json settings.json .env state.json trustedFolders.json; do
        [ -f "$SHARED_GEMINI_DIR/$sj" ] && ln -sfn "$SHARED_GEMINI_DIR/$sj" "${prof}/.gemini/$sj"
    done
}

setup_app_instance() {
    local iid="${1:-1}"
    auto_detect_installations
    [ -z "$APP_INSTALL_DIR" ] && APP_INSTALL_DIR="/opt/antigravity2"
    apply_icons_config || true

    local prof udata wm desk title comm icon pass_store="" symlink="" r_cmd="" other=false
    if [ "$iid" = "1" ] || [ "$iid" = "primary" ]; then
        [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ] && other=true
        for p in "${REAL_HOME}"/.antigravity-profile-app-*; do [ -d "$p" ] && other=true; done
        wm="antigravity"; desk="antigravity.desktop"; title="Antigravity"; comm="Antigravity AI Platform"; icon="antigravity"
        [ "$other" = true ] && { wm="antigravity-1"; desk="antigravity-1.desktop"; title="Antigravity (Account 1)"; icon="antigravity-1"; }
        [ "$KEYRING_MODE_APP1" = "normal" ] && pass_store="--password-store=basic "
        prof="${REAL_HOME}"; udata="${REAL_HOME}/.config/Antigravity"; symlink="${LOCAL_BIN}/antigravity"
    elif [ "$iid" = "2" ] || [ "$iid" = "acc2" ]; then
        prof="${PROFILE2_DIR}"; udata="${PROFILE2_DIR}/.config/Antigravity"
        wm="antigravity-2"; desk="antigravity-2.desktop"; title="Antigravity (Account 2)"; comm="Antigravity AI Platform - Account 2"; icon="antigravity-acc2"
        [ "$KEYRING_MODE_APP2" = "normal" ] && pass_store="--password-store=basic "
        r_cmd="${LOCAL_BIN}/antigravity-acc2 --restart"
        setup_app_profile_symlinks "$prof"
    else
        prof="${REAL_HOME}/.antigravity-profile-app-${iid}"; udata="${prof}/.config/Antigravity"
        wm="antigravity-app-${iid}"; desk="${wm}.desktop"; title="Antigravity App (${iid})"; comm="Antigravity AI Platform - Instance ${iid}"; icon="${wm}"
        pass_store="--password-store=basic "
        r_cmd="${LOCAL_BIN}/${wm} --restart"
        setup_app_profile_symlinks "$prof"
    fi

    local target_bin="${LOCAL_BIN}/${wm}"
    [ "$iid" = "1" ] || [ "$iid" = "primary" ] && target_bin="${LOCAL_BIN}/antigravity-1"
    [ "$iid" = "2" ] || [ "$iid" = "acc2" ] && target_bin="${LOCAL_BIN}/antigravity-acc2"

    write_dynamic_app_launcher "$target_bin" "$prof" "$udata" "$wm" "$desk" "${LOCAL_ICONS}/${icon}.png" "${LOCAL_ICONS}/${icon}-tray.png" "$pass_store" "$symlink"
    write_app_desktop_entry "${LOCAL_APPS}/${desk}" "$title" "$comm" "${target_bin} %U" "${icon}" "$wm" "$r_cmd"
    if [ "$iid" = "1" ] || [ "$iid" = "primary" ]; then
        [ "$other" = true ] && rm -f "${LOCAL_APPS}/antigravity.desktop" 2>/dev/null || rm -f "${LOCAL_APPS}/antigravity-1.desktop" 2>/dev/null || true
        ensure_account1_icons "$icon"
        xdg-mime default "${desk}" x-scheme-handler/antigravity 2>/dev/null || true
    fi
    update-desktop-database "${LOCAL_APPS}" 2>/dev/null || true
    [ "$iid" != "1" ] && [ "$iid" != "primary" ] && setup_app_instance 1
    log_success "${title} configured."
}

setup_account_1() { setup_app_instance 1; }
setup_account_2() { setup_app_instance 2; }
