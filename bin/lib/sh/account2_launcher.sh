#!/usr/bin/env bash
# Generates the Account 2 launcher script with single-instance raising.

write_account2_launcher() {
    local pass_store_flag="$1"
    cat <<EOF > "${LOCAL_BIN}/antigravity-acc2"
#!/usr/bin/env bash
set -e

export REAL_HOME="${REAL_HOME}"
export PROFILE2="${PROFILE2_DIR}"
export HOME="\${PROFILE2}"
export XDG_CONFIG_HOME="\${PROFILE2}/.config"

export ANTIGRAVITY_DESKTOP_NAME="antigravity-2.desktop"
export ANTIGRAVITY_APP_NAME="antigravity-2"
export ANTIGRAVITY_ICON_PATH="${LOCAL_ICONS}/antigravity-acc2.png"
export ANTIGRAVITY_TRAY_ICON_PATH="${LOCAL_ICONS}/antigravity-acc2-tray.png"
export ANTIGRAVITY_WINDOW_TITLE="Account 2"
export ELECTRON_OZONE_PLATFORM_HINT="x11"

if [ "\$1" = "--restart" ] || [ "\$1" = "-r" ]; then
    shift
    echo "[INFO] Terminating existing Antigravity Account 2 instance..."
    pkill -f "user-data-dir=.*\.antigravity-profile2.*Antigravity" 2>/dev/null || true
    sleep 1.5
fi

running_pid=\$(pgrep -f "user-data-dir=.*\.antigravity-profile2.*Antigravity" | head -n 1 || true)
if [ -n "\$running_pid" ]; then
    echo "[INFO] Antigravity Account 2 is already running (PID: \${running_pid})."
    echo "[INFO] Bringing window to front... (Pass --restart to restart fresh)"
    python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --focus || true
    exit 0
fi

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

exec "${APP_INSTALL_DIR}/antigravity" \${SANDBOX_FLAG}${pass_store_flag}--ozone-platform=x11 --user-data-dir="\${PROFILE2}/.config/Antigravity" --class="antigravity-2" --name="antigravity-2" "\$@"
EOF
    chmod +x "${LOCAL_BIN}/antigravity-acc2"
}
