#!/usr/bin/env bash
# Classic menu dispatch handler

execute_menu_choice() {
    local choice="$1"
    case "$choice" in
        1) install_antigravity_all ;;
        2) update_all ;;
        3) install_antigravity_app ;;
        4) install_antigravity_ide ;;
        5) detect_installations ;;
        6) resolve_dynamic_urls && check_status ;;
        7) setup_account_2 ;;
        8) update_rtl ;;
        9) unpatch_rtl_all ;;
        10) FORCE_INSTALL=true patch_f5_reload ;;
        11) unpatch_f5 ;;
        12) configure_icons_interactive ;;
        13) merge_history ;;
        14) create_instance ;;
        15) list_instances ;;
        16) menu_action_history_mode ;;
        17) configure_keyring_interactive ;;
        18) configure_paths ;;
        19) handle_wizard_command ;;
        20) menu_action_remove_instance ;;
        21) FORCE_INSTALL=true install_antigravity_all ;;
        22) clean_cache ;;
        23) menu_action_export ;;
        24) menu_action_import ;;
        25) menu_action_backups ;;
        26) menu_action_clean_data ;;
        27) menu_action_uninstall ;;
        28) update_suite_repo ;;
        29) restart_suite_services ;;
        30) dispatch_benchmark ;;
        31) dispatch_multi_account ;;
        32) FORCE_INSTALL=true patch_selector ;;
        33) unpatch_selector ;;
        34) FORCE_INSTALL=true patch_fork_all ;;
        35) unpatch_fork_all ;;
        36) FORCE_INSTALL=true patch_open_ide_app ;;
        37) unpatch_open_ide_app ;;
        38) dispatch_cloud_sync ;;
        39) dispatch_custom_models menu ;;
        0) exit 0 ;;
        *) log_err "Invalid selection."; exit 1 ;;
    esac
}
