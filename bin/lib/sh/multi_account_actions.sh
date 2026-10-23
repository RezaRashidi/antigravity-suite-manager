#!/usr/bin/env bash
# Interactive binding and removal actions for multi-account menu

multi_account_menu_bind() {
    local -a runner=("$@")
    echo ""
    log_info "Configuring Conversation-to-Account Binding..."
    read -rp "Enter Cascade/Conversation ID: " cid
    if [ -z "$cid" ]; then
        log_warn "Conversation ID cannot be empty."
        return 0
    fi
    echo "Available Accounts:"
    local accounts=()
    while IFS= read -r line; do
        [ -n "$line" ] && accounts+=("$line")
    done < <("${runner[@]}" json | jq -r '.accounts[].email' 2>/dev/null || true)

    if [ ${#accounts[@]} -eq 0 ]; then
        log_warn "No accounts found in vault. Please add an account first (Option 2)."
        read -rp "Press Enter to continue..." _
        return 0
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
}

multi_account_menu_remove() {
    local -a runner=("$@")
    echo ""
    log_info "Select account to remove:"
    local accounts=()
    while IFS= read -r line; do
        [ -n "$line" ] && accounts+=("$line")
    done < <("${runner[@]}" json | jq -r '.accounts[].email' 2>/dev/null || true)

    if [ ${#accounts[@]} -eq 0 ]; then
        log_warn "No accounts found in vault."
        read -rp "Press Enter to continue..." _
        return 0
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
}
