#!/usr/bin/env bash
# Interactive menu loop and routing

interactive_menu() {
    local sdir
    sdir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
    local detect_py="${sdir}/bin/antigravity-detect.py"
    [ ! -f "$detect_py" ] && detect_py="${sdir}/antigravity-detect.py"
    [ ! -f "$detect_py" ] && detect_py="${REAL_HOME}/.local/bin/antigravity-detect.py"

    if [ -f "$detect_py" ] && command -v python3 >/dev/null 2>&1; then
        set +e
        python3 "$detect_py" --control-center
        local code=$?
        set -e
        if [ "$code" -eq 10 ]; then
            run_wizard_flow
        fi
        return 0
    fi

    show_classic_menu
}

show_classic_menu() {
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${CYAN}   Antigravity & Antigravity IDE Suite Manager       ${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo "1) Install Antigravity Suite (App + IDE + RTL + F5)"
    echo "2) Smart Update All (App 1, App 2, IDE, RTL, F5) [Uses /tmp cache]"
    echo "3) Install / Update Antigravity App (Both Accounts)"
    echo "4) Install / Update Antigravity IDE"
    echo "5) Detect & Scan Installed Antigravity Instances"
    echo "6) Check Versions, Cache & Patch Statuses (Status Table)"
    echo "7) Configure / Repair Account 2 (Isolated Profile & Shared History)"
    echo "8) Apply / Update RTL Patcher (mmnaderi/antigravity-rtl)"
    echo "9) Re-apply F5 Manual Sync Backend Reload Patch"
    echo "10) Configure Icons & Appearance Themes"
    echo "11) Merge & Sync Conversation History (All Profiles & IDEs)"
    echo "12) Create New Instance (App or IDE with Shared/Isolated History)"
    echo "13) List All Instances & History Statuses"
    echo "14) Set / Toggle Instance History Mode (Shared vs Isolated)"
    echo "15) Configure / Switch Keyring Mode (GNOME Keyring vs Normal File Storage)"
    echo "16) Configure / Switch Antigravity Installation Paths & Targets"
    echo "17) Antigravity Control Center & Step-by-Step Setup Wizard"
    echo "18) Remove an Instance"
    echo "19) Force Full Re-download & Reinstall Everything (--force)"
    echo "20) Clean Download Cache (/tmp/antigravity-cache)"
    echo "21) Export Suite or History Archive (Cross-System Migration)"
    echo "22) Import Suite or History Archive (Cross-System Restore/Merge)"
    echo "23) Manage Backups & Snapshots (List, Create, Restore)"
    echo "24) Update Suite Manager Repository (git pull, build & deploy)"
    echo "25) Restart Background Services (Sync & Icon Daemon)"
    echo "26) Benchmark AI Response Speed, Network Latencies & Context Bloat"
    echo "27) Multi-Account Manager (Vault, Login, Bindings & Quotas)"
    echo "28) Apply Prompt-Bar Multi-Account Selector Patch"
    echo "29) Revert / Unpatch Prompt-Bar Multi-Account Selector Patch"
    echo "30) Apply Experimental Conversation Forking Patch (App & IDE)"
    echo "31) Revert / Unpatch Conversation Forking Patch"
    echo "0) Exit"
    echo -e "${CYAN}-----------------------------------------------------${NC}"
    read -rp "Select an option [0-31]: " choice

    case "$choice" in
        1) install_antigravity_all ;;
        2) update_all ;;
        3) install_antigravity_app ;;
        4) install_antigravity_ide ;;
        5) detect_installations ;;
        6) resolve_dynamic_urls && check_status ;;
        7) setup_account_2 ;;
        8) update_rtl ;;
        9) FORCE_INSTALL=true patch_f5_reload ;;
        10) configure_icons_interactive ;;
        11) merge_history ;;
        12) create_instance ;;
        13) list_instances ;;
        14) menu_action_history_mode ;;
        15) configure_keyring_interactive ;;
        16) configure_paths ;;
        17) handle_wizard_command ;;
        18) menu_action_remove_instance ;;
        19) FORCE_INSTALL=true install_antigravity_all ;;
        20) clean_cache ;;
        21) menu_action_export ;;
        22) menu_action_import ;;
        23) menu_action_backups ;;
        24) update_suite_repo ;;
        25) restart_suite_services ;;
        26) dispatch_benchmark ;;
        27) dispatch_multi_account ;;
        28) FORCE_INSTALL=true patch_selector ;;
        29) unpatch_selector ;;
        30) FORCE_INSTALL=true patch_fork_all ;;
        31) unpatch_fork_all ;;
        0) exit 0 ;;
        *) log_err "Invalid selection."; exit 1 ;;
    esac
}
