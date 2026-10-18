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
