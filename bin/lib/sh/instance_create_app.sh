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

    cat <<EOF > "$launcher"
#!/usr/bin/env bash
set -e
export REAL_HOME="${REAL_HOME}"
export PROFILE="${profile_dir}"
export HOME="\${PROFILE}"
export XDG_CONFIG_HOME="\${PROFILE}/.config"
export ANTIGRAVITY_DESKTOP_NAME="${wm_class}.desktop"
export ANTIGRAVITY_APP_NAME="${wm_class}"
export ANTIGRAVITY_ICON_PATH="${LOCAL_ICONS}/${wm_class}.png"
export ELECTRON_OZONE_PLATFORM_HINT="x11"

if [ "\$1" = "--restart" ] || [ "\$1" = "-r" ]; then
    shift
    pkill -f "user-data-dir=.*${profile_dir##*/}.*Antigravity" 2>/dev/null || true
    sleep 1.5
fi

running_pid=\$(pgrep -f "user-data-dir=.*${profile_dir##*/}.*Antigravity" | head -n 1 || true)
if [ -n "\$running_pid" ]; then
    echo "[INFO] ${wm_class} is already running. Bringing to front..."
    python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --focus "${iid}" || true
    exit 0
fi

cd "\${REAL_HOME}" || cd /tmp
! pgrep -f "antigravity-apply-icon.py --daemon" >/dev/null 2>&1 && python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --daemon >/dev/null 2>&1 &
disown -a 2>/dev/null || true

SANDBOX_FLAG=""
if [ -f "${APP_INSTALL_DIR}/chrome-sandbox" ]; then
    sb_stat=\$(stat -c "%u:%a" "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null || true)
    if [ "\$sb_stat" != "0:4755" ] && ! (sudo -n chown root:root "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null && sudo -n chmod 4755 "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null); then
        SANDBOX_FLAG="--no-sandbox "
    fi
fi

exec "${APP_INSTALL_DIR}/antigravity" \${SANDBOX_FLAG}--password-store=basic --ozone-platform=x11 --user-data-dir="\${PROFILE}/.config/Antigravity" --class="${wm_class}" --name="${wm_class}" "\$@"
EOF
    chmod +x "$launcher"

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
