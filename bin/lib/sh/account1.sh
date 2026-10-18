#!/usr/bin/env bash
# Primary account 1 launcher and desktop shortcut generator.

setup_account_1() {
    log_info "Configuring Account 1 (Primary)..."
    auto_detect_installations
    if [ -z "$APP_INSTALL_DIR" ] || [ ! -f "${APP_INSTALL_DIR}/antigravity" ]; then
        for cand in "$APP_INSTALL_DIR" "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity"; do
            [ -n "$cand" ] && [ -f "${cand}/antigravity" ] && { APP_INSTALL_DIR="$cand"; break; }
        done
    fi
    APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/Antigravity-x64}"
    apply_icons_config || true

    local pass_store_flag=""
    if [ "$KEYRING_MODE_APP1" = "normal" ]; then
        pass_store_flag="--password-store=basic "
        mkdir -p "${REAL_HOME}/.gemini/cache" && touch "${REAL_HOME}/.gemini/cache/antigravity-keyring-unavailable"
    else
        rm -f "${REAL_HOME}/.gemini/cache/antigravity-keyring-unavailable" 2>/dev/null || true
    fi

    local has_other_accounts=false
    if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
        has_other_accounts=true
    else
        for p in "${REAL_HOME}"/.antigravity-profile-app-*; do [ -d "$p" ] && { has_other_accounts=true; break; }; done
    fi

    local wm_class="antigravity" desktop_name="antigravity.desktop" app_title="Antigravity" app_comment="Antigravity AI Platform" icon_name="antigravity"
    if [ "$has_other_accounts" = true ]; then
        wm_class="antigravity-1"; desktop_name="antigravity-1.desktop"; app_title="Antigravity (Account 1)"; app_comment="Antigravity AI Platform - Account 1"; icon_name="antigravity-1"
    fi
    log_info "Configuring ${app_title} (${desktop_name})..."

cat <<EOF > "${LOCAL_BIN}/antigravity-1"
#!/usr/bin/env bash
set -e
export REAL_HOME="${REAL_HOME}"
export HOME="\${REAL_HOME}"
export XDG_CONFIG_HOME="\${REAL_HOME}/.config"
export ANTIGRAVITY_DESKTOP_NAME="${desktop_name}"
export ANTIGRAVITY_APP_NAME="${wm_class}"
export ANTIGRAVITY_ICON_PATH="${LOCAL_ICONS}/${icon_name}.png"
export ANTIGRAVITY_TRAY_ICON_PATH="${LOCAL_ICONS}/${icon_name}-tray.png"
export ELECTRON_OZONE_PLATFORM_HINT="x11"

cd "\${REAL_HOME}" || cd /tmp
! pgrep -f "antigravity-apply-icon.py --daemon" >/dev/null 2>&1 && python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --daemon >/dev/null 2>&1 &
! pgrep -f "antigravity-merge-history.py" >/dev/null 2>&1 && python3 "${LOCAL_BIN}/antigravity-merge-history.py" --quiet >/dev/null 2>&1 &
disown -a 2>/dev/null || true

SANDBOX_FLAG=""
if [ -f "${APP_INSTALL_DIR}/chrome-sandbox" ]; then
    sb_stat=\$(stat -c "%u:%a" "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null || true)
    if [ "\$sb_stat" != "0:4755" ] && ! (sudo -n chown root:root "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null && sudo -n chmod 4755 "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null); then
        SANDBOX_FLAG="--no-sandbox "
    fi
fi

exec "${APP_INSTALL_DIR}/antigravity" \${SANDBOX_FLAG}${pass_store_flag}--ozone-platform=x11 --user-data-dir="\${REAL_HOME}/.config/Antigravity" --class="${wm_class}" --name="${wm_class}" "\$@"
EOF
    chmod +x "${LOCAL_BIN}/antigravity-1"
    ln -sfn "${LOCAL_BIN}/antigravity-1" "${LOCAL_BIN}/antigravity"

    cat <<EOF > "${LOCAL_APPS}/${desktop_name}"
[Desktop Entry]
Name=${app_title}
GenericName=AI Pair Programmer
Comment=${app_comment}
Exec=${LOCAL_BIN}/antigravity %U
Terminal=false
Type=Application
Icon=${icon_name}
Categories=Development;IDE;
StartupWMClass=${wm_class}
MimeType=x-scheme-handler/antigravity;
StartupNotify=true
EOF
    chmod +x "${LOCAL_APPS}/${desktop_name}"
    [ "$has_other_accounts" = true ] && rm -f "${LOCAL_APPS}/antigravity.desktop" 2>/dev/null || rm -f "${LOCAL_APPS}/antigravity-1.desktop" 2>/dev/null || true

    ensure_account1_icons "$icon_name"
    update-desktop-database "${LOCAL_APPS}" 2>/dev/null || true
    xdg-mime default "${desktop_name}" x-scheme-handler/antigravity 2>/dev/null || true
    log_success "${app_title} configured with launcher and icons."
}
