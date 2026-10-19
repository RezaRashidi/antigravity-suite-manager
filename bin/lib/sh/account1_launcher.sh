#!/usr/bin/env bash
# Generates the Account 1 launcher script with restart and stale detection.

write_account1_launcher() {
    local desktop_name="$1" wm_class="$2" icon_name="$3" pass_store_flag="$4"
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

if [ "\$1" = "--restart" ] || [ "\$1" = "-r" ]; then
    shift
    echo "[INFO] Terminating active Antigravity (Account 1) instance..."
    pkill -f "user-data-dir=.*\.config/Antigravity" 2>/dev/null || pkill -f "class=${wm_class}" 2>/dev/null || true
    sleep 1.2
fi

# Detect stale instance running a deleted binary (updated while running)
for p in \$(pgrep -f "${APP_INSTALL_DIR}/antigravity" || true); do
    if [ -L "/proc/\$p/exe" ]; then
        exe_tgt=\$(readlink "/proc/\$p/exe" 2>/dev/null || true)
        if [[ "\$exe_tgt" == *"(deleted)"* ]]; then
            echo "[INFO] Stale binary in RAM detected (app was updated on disk). Restarting..."
            kill -TERM "\$p" 2>/dev/null || kill -9 "\$p" 2>/dev/null || true
            sleep 1.2
            break
        fi
    fi
done

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
}
