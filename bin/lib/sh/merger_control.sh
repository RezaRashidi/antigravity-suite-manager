#!/usr/bin/env bash
# Antigravity History Merger Control Module (Automatic vs Manual Mode)

merger_status() {
    local disabled_flag="${REAL_HOME:-$HOME}/.config/antigravity/merger_disabled"
    echo -e "${CYAN}==========================================================${NC}"
    echo -e "${CYAN}          Antigravity History Merger Status               ${NC}"
    echo -e "${CYAN}==========================================================${NC}"
    if [ -f "$disabled_flag" ]; then
        echo -e "  Sync Mode   : ${YELLOW}MANUAL${NC} (Automated background daemon disabled)"
    else
        echo -e "  Sync Mode   : ${GREEN}AUTOMATIC${NC} (Background sync daemon enabled)"
    fi
    if command -v systemctl >/dev/null 2>&1 && systemctl --user is-active antigravity-sync.service >/dev/null 2>&1; then
        echo -e "  Systemd Unit: ${GREEN}ACTIVE${NC} (Running in background)"
    else
        echo -e "  Systemd Unit: ${RED}INACTIVE${NC} (Stopped)"
    fi
    local pcount
    pcount=$(pgrep -f "antigravity-merge-history.py.*watch" 2>/dev/null | wc -l)
    echo "  Live Tasks  : ${pcount} background watcher(s) active"
    echo -e "${CYAN}==========================================================${NC}"
}

enable_merger_auto() {
    log_info "Enabling automatic background history synchronization..."
    local disabled_flag="${REAL_HOME:-$HOME}/.config/antigravity/merger_disabled"
    rm -f "$disabled_flag"
    enable_sync_service
    log_success "Automatic history merger enabled. Background daemon is active."
}

disable_merger_auto() {
    log_info "Disabling automatic background history synchronization..."
    local disabled_flag="${REAL_HOME:-$HOME}/.config/antigravity/merger_disabled"
    mkdir -p "$(dirname "$disabled_flag")"
    touch "$disabled_flag"
    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user stop antigravity-sync.service 2>/dev/null || true
        systemctl --user disable antigravity-sync.service 2>/dev/null || true
    fi
    pkill -f "antigravity-merge-history.py" 2>/dev/null || true
    log_success "Automatic history merger disabled. History will only sync manually on demand."
}

dispatch_merger() {
    local action="${1:-}"
    case "$action" in
        status|info) merger_status ;;
        auto|enable|start) enable_merger_auto ;;
        manual|disable|stop) disable_merger_auto ;;
        run|sync|now) merge_history ;;
        *)
            merger_status
            echo ""
            echo "Options:"
            echo "  1) Enable Automatic Merger (Background daemon)"
            echo "  2) Disable Automatic Merger (Manual mode only)"
            echo "  3) Run One-Shot Manual Merge Now"
            echo "  4) Exit"
            echo ""
            read -rp "Select option [1-4]: " choice
            case "$choice" in
                1) enable_merger_auto ;;
                2) disable_merger_auto ;;
                3) merge_history ;;
                *) return 0 ;;
            esac
            ;;
    esac
}
