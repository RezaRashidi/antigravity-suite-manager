#!/usr/bin/env bash
# Dedicated creator for custom Antigravity App instances and profiles.

create_app_instance() {
    local iid="$1"
    local imode="$2"
    local itheme="${3:-black}"
    local ihue="$4"

    if [[ "$iid" =~ ^[0-9]+$ ]] && [ "$iid" -eq 2 ]; then
        log_info "Instance 2 for App corresponds to Account 2. Delegating to setup_account_2..."
        setup_account_2 && return 0
    fi

    local profile_dir="${REAL_HOME}/.antigravity-profile-app-${iid}" wm_class="antigravity-app-${iid}"
    local launcher="${LOCAL_BIN}/antigravity-app-${iid}" desktop="${LOCAL_APPS}/antigravity-app-${iid}.desktop"

    mkdir -p "${profile_dir}/.gemini/cache" "${profile_dir}/.local/share"
    touch "${profile_dir}/.gemini/cache/antigravity-keyring-unavailable"
    ln -sfn "$LOCAL_APPS" "${profile_dir}/.local/share/applications"
    ln -sfn "$LOCAL_ICONS" "${profile_dir}/.local/share/icons"

    if [ "$imode" = "shared" ]; then
        log_info "Configuring shared conversation history with master pool..."
        rm -rf "${profile_dir}/.gemini/antigravity" 2>/dev/null || true
        ln -sfn "$SHARED_CONV_DIR" "${profile_dir}/.gemini/antigravity"
        ln -sfn "$SHARED_CONFIG_DIR" "${profile_dir}/.gemini/config"
    else
        log_info "Configuring isolated private conversation history..."
        [ -L "${profile_dir}/.gemini/antigravity" ] && rm -f "${profile_dir}/.gemini/antigravity"
        mkdir -p "${profile_dir}/.gemini/antigravity/conversations" "${profile_dir}/.gemini/antigravity/brain"
    fi

    log_info "Generating dedicated icon for ${wm_class}..."
    local icon_args=(--custom-instance "$wm_class" --custom-theme "$itheme")
    [ -n "$ihue" ] && icon_args+=(--custom-hue "$ihue")
    python3 "${LOCAL_BIN}/antigravity-generate-icons.py" "${icon_args[@]}" >/dev/null 2>&1 || true
    write_dynamic_app_launcher \
        "$launcher" \
        "${profile_dir}" \
        "${profile_dir}/.config/Antigravity" \
        "$wm_class" \
        "${wm_class}.desktop" \
        "${LOCAL_ICONS}/${wm_class}.png" \
        "${LOCAL_ICONS}/${wm_class}-tray.png" \
        "--password-store=basic " \
        ""


    cat <<EOF > "$desktop"
[Desktop Entry]
Name=Antigravity App (${iid})
GenericName=AI Assistant
Comment=Google Antigravity AI Assistant - Instance ${iid}
Exec=${launcher} %U
Terminal=false
Type=Application
Icon=${LOCAL_ICONS}/${wm_class}.png
Categories=Development;Utility;
StartupWMClass=${wm_class}
MimeType=x-scheme-handler/antigravity;
StartupNotify=true
EOF
    chmod +x "$desktop"
    update-desktop-database "$LOCAL_APPS" 2>/dev/null || true
    setup_account_1
}
