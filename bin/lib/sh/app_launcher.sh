#!/usr/bin/env bash
# Unified dynamic App launcher and desktop entry generator for all instances.

write_dynamic_app_launcher() {
    local target="$1" prof="$2" udata="$3" wm="$4" desk="$5" icon="$6" tray="$7" pstore="$8" symlink="$9"

    cat <<EOF > "$target"
#!/usr/bin/env bash
set -e
export REAL_HOME="${REAL_HOME}"
export PROFILE="${prof}"
export HOME="\${PROFILE}"
export XDG_CONFIG_HOME="\${PROFILE}/.config"
export ANTIGRAVITY_DESKTOP_NAME="${desk}"
export ANTIGRAVITY_APP_NAME="${wm}"
export ANTIGRAVITY_ICON_PATH="${icon}"
export ANTIGRAVITY_TRAY_ICON_PATH="${tray}"
export ANTIGRAVITY_ACCOUNTS_DIR="${REAL_HOME}/.config/antigravity/accounts"
export ELECTRON_OZONE_PLATFORM_HINT="x11"

if [ "\$1" = "--restart" ] || [ "\$1" = "-r" ]; then
    shift
    echo "[INFO] Terminating active instance (${wm})..."
    pkill -f "user-data-dir=.*${udata##*/}" 2>/dev/null || pkill -f "class=${wm}" 2>/dev/null || true
    sleep 1.2
fi

# Detect stale instance running a deleted binary (updated on disk while running)
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

if [ \$# -eq 0 ]; then
    running_pid=\$(pgrep -f "user-data-dir=.*${udata##*/}" | head -n 1 || pgrep -f "class=${wm}" | head -n 1 || true)
    if [ -n "\$running_pid" ] && [ "\$running_pid" != "\$\$" ]; then
        echo "[INFO] ${wm} is already running (PID: \${running_pid}). Bringing to front..."
        python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --focus 2>/dev/null || true
        exit 0
    fi
fi

cd "\${REAL_HOME}" || cd /tmp
! pgrep -f "antigravity-apply-icon.py --daemon" >/dev/null 2>&1 && python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --daemon >/dev/null 2>&1 &
! systemctl --user is-active antigravity-sync.service >/dev/null 2>&1 && ! pgrep -f "antigravity-merge-history.py" >/dev/null 2>&1 && python3 "${LOCAL_BIN}/antigravity-merge-history.py" --quiet >/dev/null 2>&1 &
disown -a 2>/dev/null || true

SANDBOX_FLAG=""
if [ -f "${APP_INSTALL_DIR}/chrome-sandbox" ]; then
    sb_stat=\$(stat -c "%u:%a" "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null || true)
    if [ "\$sb_stat" != "0:4755" ] && ! (sudo -n chown root:root "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null && sudo -n chmod 4755 "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null); then
        SANDBOX_FLAG="--no-sandbox "
    fi
fi

exec "${APP_INSTALL_DIR}/antigravity" \${SANDBOX_FLAG}${pstore}--ozone-platform=x11 --user-data-dir="${udata}" --class="${wm}" --name="${wm}" "\$@"
EOF
    chmod +x "$target"
    [ -n "$symlink" ] && ln -sfn "$target" "$symlink" || true
}

write_app_desktop_entry() {
    local target="$1" name="$2" comm="$3" exec_cmd="$4" icon="$5" wm="$6" restart_cmd="$7"
    cat <<EOF > "$target"
[Desktop Entry]
Name=${name}
GenericName=AI Pair Programmer
Comment=${comm}
Exec=${exec_cmd}
Terminal=false
Type=Application
Icon=${icon}
Categories=Development;IDE;
StartupWMClass=${wm}
MimeType=x-scheme-handler/antigravity;
StartupNotify=true
EOF
    if [ -n "$restart_cmd" ]; then
        cat <<EOF >> "$target"
Actions=Restart;

[Desktop Action Restart]
Name=Restart ${name}
Exec=${restart_cmd}
EOF
    fi
    chmod +x "$target"
}
