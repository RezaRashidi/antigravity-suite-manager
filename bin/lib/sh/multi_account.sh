#!/usr/bin/env bash
# Multi-Account subsystem dispatcher and interactive menu

dispatch_multi_account() {
    local m_script
    m_script="$(get_multi_account_cli)"

    if [ $# -gt 0 ]; then
        local subcmd="$1"
        shift
        if [ "$subcmd" = "bookmarklet" ] || [ "$subcmd" = "remote" ] || [ "$subcmd" = "remote-control" ]; then
            generate_remote_control_bookmarklet "$@"
            return 0
        fi
        if [ -n "$m_script" ] && [ -f "$m_script" ]; then
            python3 "$m_script" "$subcmd" "$@"
            return $?
        fi
        python3 -m antigravity_suite.multi_account.cli "$subcmd" "$@"
        return $?
    fi

    interactive_multi_account_menu
}

interactive_multi_account_menu() {
    local m_script
    m_script="$(get_multi_account_cli)"
    local runner=(python3 -m antigravity_suite.multi_account.cli)
    if [ -n "$m_script" ] && [ -f "$m_script" ]; then
        runner=(python3 "$m_script")
    fi

    while true; do
        echo ""
        echo -e "${CYAN}=====================================================${NC}"
        echo -e "       ${GREEN}Antigravity Multi-Account Suite Manager${NC}"
        echo -e "${CYAN}=====================================================${NC}"
        echo "1) List Connected Accounts & Real-Time Quotas"
        echo "2) Add / Login New Google Account (Browser OAuth)"
        echo "3) Select & Bind Account for a Conversation (Cascade)"
        echo "4) View Active Conversation Bindings"
        echo "5) Remove / Sign Out an Account"
        echo "6) Check / Restart Multi-Account Proxy Service"
        echo "7) Remote Control Account Selector (Bookmarklet & Chat Commands)"
        echo "0) Return to Main Menu"
        echo -e "${CYAN}-----------------------------------------------------${NC}"
        read -rp "Select an option [0-7]: " choice

        case "$choice" in
            1)
                echo ""
                log_info "Fetching connected accounts and live quota telemetry..."
                "${runner[@]}" list
                read -rp "Press Enter to continue..." _
                ;;
            2)
                echo ""
                log_info "Launching Google OAuth sign-in flow..."
                "${runner[@]}" login
                read -rp "Press Enter to continue..." _
                ;;
            3)
                multi_account_menu_bind "${runner[@]}"
                ;;
            4)
                echo ""
                log_info "Current Active Conversation Bindings:"
                "${runner[@]}" json | jq -r '.bindings // {}' 2>/dev/null || echo "{}"
                read -rp "Press Enter to continue..." _
                ;;
            5)
                multi_account_menu_remove "${runner[@]}"
                ;;
            6)
                echo ""
                log_info "Checking Multi-Account Proxy Service status..."
                if curl -s -m 2 http://127.0.0.1:41999/healthz >/dev/null 2>&1; then
                    log_success "Multi-Account Proxy is RUNNING on http://127.0.0.1:41999"
                else
                    log_warn "Proxy not responding. Starting background proxy daemon..."
                    "${runner[@]}" serve --port 41999 &
                    sleep 1
                    if curl -s -m 2 http://127.0.0.1:41999/healthz >/dev/null 2>&1; then
                        log_success "Multi-Account Proxy successfully started on http://127.0.0.1:41999"
                    else
                        log_err "Failed to start proxy service."
                    fi
                fi
                read -rp "Press Enter to continue..." _
                ;;
            7)
                generate_remote_control_bookmarklet
                read -rp "Press Enter to continue..." _
                ;;
            0) break ;;
            *) log_err "Invalid selection." ;;
        esac
    done
}
