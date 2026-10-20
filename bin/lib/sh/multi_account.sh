#!/usr/bin/env bash
# Multi-Account subsystem dispatcher and interactive menu

get_multi_account_cli() {
    if [ -n "${LOCAL_BIN:-}" ] && [ -f "${LOCAL_BIN}/antigravity-multi-account.py" ]; then
        echo "${LOCAL_BIN}/antigravity-multi-account.py"
    elif command -v antigravity-multi-account.py >/dev/null 2>&1; then
        command -v antigravity-multi-account.py
    else
        local sdir
        sdir="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
        if [ -f "${sdir}/bin/antigravity-multi-account.py" ]; then
            echo "${sdir}/bin/antigravity-multi-account.py"
        fi
    fi
}

dispatch_multi_account() {
    local m_script
    m_script="$(get_multi_account_cli)"

    if [ $# -gt 0 ]; then
        local subcmd="$1"
        shift
        if [ -n "$m_script" ] && [ -f "$m_script" ]; then
            python3 "$m_script" "$subcmd" "$@"
            return $?
        fi
        python3 -m antigravity_suite.multi_account.cli "$subcmd" "$@"
        return $?
    fi

    # Interactive Submenu when triggered from main menu without arguments
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
        echo "0) Return to Main Menu"
        echo -e "${CYAN}-----------------------------------------------------${NC}"
        read -rp "Select an option [0-6]: " choice

        case "$choice" in
            1)
                echo ""
                log_info "Fetching connected accounts and live quota telemetry..."
                "${runner[@]}" list
                echo ""
                read -rp "Press Enter to continue..." _
                ;;
            2)
                echo ""
                log_info "Launching Google OAuth sign-in flow..."
                "${runner[@]}" login
                echo ""
                read -rp "Press Enter to continue..." _
                ;;
            3)
                echo ""
                log_info "Configuring Conversation-to-Account Binding..."
                read -rp "Enter Cascade/Conversation ID: " cid
                if [ -z "$cid" ]; then
                    log_warn "Conversation ID cannot be empty."
                    continue
                fi
                echo "Available Accounts:"
                local accounts=()
                while IFS= read -r line; do
                    [ -n "$line" ] && accounts+=("$line")
                done < <("${runner[@]}" json | jq -r '.accounts[].email' 2>/dev/null || true)

                if [ ${#accounts[@]} -eq 0 ]; then
                    log_warn "No accounts found in vault. Please add an account first (Option 2)."
                    read -rp "Press Enter to continue..." _
                    continue
                fi

                for i in "${!accounts[@]}"; do
                    echo "  $((i+1))) ${accounts[$i]}"
                done
                read -rp "Select account number [1-${#accounts[@]}]: " acc_idx
                if [[ "$acc_idx" =~ ^[0-9]+$ ]] && [ "$acc_idx" -ge 1 ] && [ "$acc_idx" -le "${#accounts[@]}" ]; then
                    local chosen_acc="${accounts[$((acc_idx-1))]}"
                    "${runner[@]}" bind "$cid" "$chosen_acc"
                    log_success "Bound conversation '$cid' to account '$chosen_acc'."
                else
                    log_err "Invalid selection."
                fi
                read -rp "Press Enter to continue..." _
                ;;
            4)
                echo ""
                log_info "Current Active Conversation Bindings:"
                "${runner[@]}" json | jq -r '.bindings // {}' 2>/dev/null || echo "{}"
                echo ""
                read -rp "Press Enter to continue..." _
                ;;
            5)
                echo ""
                log_info "Select account to remove:"
                local accounts=()
                while IFS= read -r line; do
                    [ -n "$line" ] && accounts+=("$line")
                done < <("${runner[@]}" json | jq -r '.accounts[].email' 2>/dev/null || true)

                if [ ${#accounts[@]} -eq 0 ]; then
                    log_warn "No accounts found in vault."
                    read -rp "Press Enter to continue..." _
                    continue
                fi

                for i in "${!accounts[@]}"; do
                    echo "  $((i+1))) ${accounts[$i]}"
                done
                read -rp "Select account number to remove [1-${#accounts[@]}]: " del_idx
                if [[ "$del_idx" =~ ^[0-9]+$ ]] && [ "$del_idx" -ge 1 ] && [ "$del_idx" -le "${#accounts[@]}" ]; then
                    local target_acc="${accounts[$((del_idx-1))]}"
                    read -rp "Are you sure you want to remove '$target_acc'? [y/N]: " confirm
                    if [[ "$confirm" =~ ^[Yy]$ ]]; then
                        "${runner[@]}" logout "$target_acc"
                        log_success "Account '$target_acc' removed."
                    fi
                else
                    log_err "Invalid selection."
                fi
                read -rp "Press Enter to continue..." _
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
            0)
                break
                ;;
            *)
                log_err "Invalid selection."
                ;;
        esac
    done
}
