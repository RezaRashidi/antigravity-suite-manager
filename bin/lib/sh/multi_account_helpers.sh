#!/usr/bin/env bash
# Multi-Account CLI resolution and remote control bookmarklet generator

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

generate_remote_control_bookmarklet() {
    local host_ip
    host_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    [ -z "$host_ip" ] && host_ip="127.0.0.1"
    local router_url="http://${host_ip}:41999"
    echo ""
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "       ${GREEN}Antigravity Remote Control Account Selector${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo ""
    echo -e "${YELLOW}Method 1: Direct In-Chat Slash Commands (Zero-install, Universal):${NC}"
    echo "    /accounts          - Show all connected Google accounts & current binding"
    echo "    /switch <number>   - Switch this chat to account number (e.g. /switch 2)"
    echo "    /switch <email>    - Switch this chat to email (e.g. /switch user@gmail.com)"
    echo "    /whoami            - Check which account is handling this chat"
    echo ""
    echo -e "${YELLOW}Method 2: One-Click Browser Bookmarklet (Visual Selector Pill):${NC}"
    echo "javascript:(function(){var h=localStorage.getItem('agy_host')||prompt('Antigravity Host URL:','${router_url}');if(h){localStorage.setItem('agy_host',h);window.__AGY_ROUTER_HOST__=h;var s=document.createElement('script');s.src=h+'/ui_bundle.js?t='+Date.now();document.head.appendChild(s);}})();"
    echo ""
    echo -e "${CYAN}-----------------------------------------------------${NC}"
}
