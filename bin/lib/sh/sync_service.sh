#!/usr/bin/env bash
# Background history synchronization daemon and manual merge runner.

enable_sync_service() {
    log_info "Configuring real-time background history sync daemon..."
    local systemd_dir="${REAL_HOME}/.config/systemd/user"
    mkdir -p "$systemd_dir"

    cat <<EOF > "${systemd_dir}/antigravity-sync.service"
[Unit]
Description=Antigravity Real-Time History & Chat Synchronization Daemon
After=default.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 ${LOCAL_BIN}/antigravity-merge-history.py --watch
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user enable --now antigravity-sync.service 2>/dev/null || true
    log_success "Background history sync daemon enabled & active."
}

merge_history() {
    log_info "Synchronizing and backfilling conversation history across all profiles..."
    if [ -f "${LOCAL_BIN}/antigravity-merge-history.py" ]; then
        python3 "${LOCAL_BIN}/antigravity-merge-history.py" --master "$SHARED_CONV_DIR"
    elif [ -f "${SCRIPT_DIR}/antigravity-merge-history.py" ]; then
        python3 "${SCRIPT_DIR}/antigravity-merge-history.py" --master "$SHARED_CONV_DIR"
    elif [ -f "${SCRIPT_DIR}/bin/antigravity-merge-history.py" ]; then
        python3 "${SCRIPT_DIR}/bin/antigravity-merge-history.py" --master "$SHARED_CONV_DIR"
    else
        log_err "antigravity-merge-history.py not found."
        return 1
    fi
    log_success "History synchronization complete."
}

restart_suite_services() {
    log_info "Restarting Antigravity Suite background services..."
    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user daemon-reload 2>/dev/null || true
        if systemctl --user is-enabled antigravity-sync.service >/dev/null 2>&1 || \
           systemctl --user is-active antigravity-sync.service >/dev/null 2>&1; then
            systemctl --user restart --no-block antigravity-sync.service 2>/dev/null || true
            log_success "Systemd history sync daemon restarted."
        fi
    fi
    if pgrep -f "antigravity-apply-icon.py --daemon" >/dev/null 2>&1; then
        pkill -f "antigravity-apply-icon.py --daemon" 2>/dev/null || true
        sleep 0.5
    fi
    local icon_script="${LOCAL_BIN}/antigravity-apply-icon.py"
    [ ! -f "$icon_script" ] && icon_script="${SCRIPT_DIR}/antigravity-apply-icon.py"
    [ ! -f "$icon_script" ] && icon_script="${SCRIPT_DIR}/bin/antigravity-apply-icon.py"
    if [ -f "$icon_script" ]; then
        nohup python3 "$icon_script" --daemon </dev/null >/dev/null 2>&1 &
        log_success "X11 icon injector daemon restarted."
    fi
    log_success "All Antigravity Suite background services restarted."
}
