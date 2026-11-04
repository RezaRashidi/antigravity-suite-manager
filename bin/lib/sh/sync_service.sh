#!/usr/bin/env bash
# Legacy background sync daemon retirement and migration helper.

merge_history() {
    log_info "Migrating legacy conversation history (v2.5.5 -> v2.6.0)..."
    if [ -f "${LOCAL_BIN}/antigravity-migrate-chats.py" ]; then
        python3 "${LOCAL_BIN}/antigravity-migrate-chats.py"
    elif [ -f "${SCRIPT_DIR}/bin/antigravity-migrate-chats.py" ]; then
        python3 "${SCRIPT_DIR}/bin/antigravity-migrate-chats.py"
    elif [ -f "${LOCAL_BIN}/antigravity-merge-history.py" ]; then
        python3 "${LOCAL_BIN}/antigravity-merge-history.py" --master "$SHARED_CONV_DIR"
    else
        log_err "Migrator script not found."
        return 1
    fi
    log_success "Chat migration complete."
}

restart_suite_services() {
    log_info "Restarting Antigravity Suite background services..."
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl --user is-active antigravity-sync.service >/dev/null 2>&1; then
            systemctl --user stop antigravity-sync.service 2>/dev/null || true
            systemctl --user disable antigravity-sync.service 2>/dev/null || true
        fi
        rm -f "${REAL_HOME}/.config/systemd/user/antigravity-sync.service" 2>/dev/null || true
        systemctl --user daemon-reload 2>/dev/null || true
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
    log_success "All Antigravity Suite background services restarted (Sync daemon retired in v2.6.0)."
}
