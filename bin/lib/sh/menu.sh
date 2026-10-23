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
        if [ "$code" -eq 10 ]; then run_wizard_flow; fi
        return 0
    fi
    show_classic_menu
}

show_classic_menu() {
    local has_acc2=false
    [ -d "$PROFILE2_DIR" ] && [ -f "${LOCAL_BIN}/antigravity-acc2" ] && has_acc2=true
    local app_opt="3) Install / Update Antigravity App"
    local acc2_opt="7) Create Secondary Account (Isolated Profile & Shared History)"
    if [ "$has_acc2" = true ]; then
        app_opt="3) Install / Update Antigravity App (Both Accounts)"
        acc2_opt="7) Configure / Repair Account 2 (Isolated Profile & Shared History)"
    fi
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${CYAN}   Antigravity & Antigravity IDE Suite Manager       ${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo "1) Install Antigravity Suite (App + IDE + RTL + F5)"
    echo "2) Smart Update All (Auto re-applies active patches) [Uses cache]"
    echo "$app_opt"
    echo "4) Install / Update Antigravity IDE"
    echo "5) Detect & Scan Installed Antigravity Instances"
    echo "6) Check Versions, Cache & Patch Statuses (Status Table)"
    echo "$acc2_opt"
    echo "8) Apply / Update RTL Patcher (mmnaderi/antigravity-rtl)"
    echo "9) Revert / Unpatch RTL Patcher"
    echo "10) Re-apply F5 Manual Sync Backend Reload Patch"
    echo "11) Revert / Unpatch F5 Manual Sync Backend Reload Patch"
    echo "12) Configure Icons & Appearance Themes"
    echo "13) Merge & Sync Conversation History (All Profiles & IDEs)"
    echo "14) Create New Instance (App or IDE with Shared/Isolated History)"
    echo "15) List All Instances & History Statuses"
    echo "16) Set / Toggle Instance History Mode (Shared vs Isolated)"
    echo "17) Configure / Switch Keyring Mode (GNOME Keyring vs Normal File Storage)"
    echo "18) Configure / Switch Antigravity Installation Paths & Targets"
    echo "19) Antigravity Control Center & Step-by-Step Setup Wizard"
    echo "20) Remove an Instance (Cloned Profile)"
    echo "21) Force Full Re-download & Reinstall Everything (--force)"
    echo "22) Clean Download Cache (/tmp/antigravity-cache)"
    echo "23) Export Suite or History Archive (Cross-System Migration)"
    echo "24) Import Suite or History Archive (Cross-System Restore/Merge)"
    echo "25) Manage Backups & Snapshots (App, IDE, History, All, Restore)"
    echo "26) Clean / Delete Antigravity Data (App, IDE, History, All)"
    echo "27) Uninstall Antigravity Apps (With or Without Data)"
    echo "28) Update Suite Manager Repository (git pull, build & deploy)"
    echo "29) Restart Background Services (Sync & Icon Daemon)"
    echo "30) Benchmark AI Response Speed, Network Latencies & Context Bloat"
    echo "31) Multi-Account Manager (Vault, Login, Bindings & Quotas)"
    echo "32) Apply Prompt-Bar Multi-Account Selector Patch"
    echo "33) Revert / Unpatch Prompt-Bar Multi-Account Selector Patch"
    echo "34) Apply Experimental Conversation Forking Patch (App & IDE)"
    echo "35) Revert / Unpatch Conversation Forking Patch"
    echo "36) Enable Native 'Open in IDE' Titlebar Button in App"
    echo "37) Revert / Unpatch Native 'Open in IDE' Button Patch"
    echo "38) Cloud Sync (Rclone Encrypted Cross-System Push/Pull)"
    echo "0) Exit"
    echo -e "${CYAN}-----------------------------------------------------${NC}"
    read -rp "Select an option [0-38]: " choice
    execute_menu_choice "$choice"
}
