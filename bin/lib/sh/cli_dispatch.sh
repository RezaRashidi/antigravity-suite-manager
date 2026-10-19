#!/usr/bin/env bash
# Command execution dispatcher

dispatch_command() {
    if [ -z "$COMMAND" ]; then
        interactive_menu
        return 0
    fi
    case "$COMMAND" in
        detect) auto_detect_installations; detect_installations ;;
        install) dispatch_install ;;
        keyring) dispatch_keyring ;;
        paths) handle_paths_command ;;
        wizard|setup|center|control-center) handle_wizard_command ;;
        status) resolve_dynamic_urls; check_status ;;
        all) install_antigravity_all ;;
        app) install_antigravity_app ;;
        ide) install_antigravity_ide ;;
        app1) setup_account_1 ;;
        app2) setup_account_2 ;;
        ide-shortcuts) setup_ide_shortcuts ;;
        set-icons|icons)
            if [ "$CLI_ICON_GIVEN" = true ]; then apply_icons_config
            else configure_icons_interactive "$SUB_COMMAND"; fi ;;
        merge-history) merge_history ;;
        export-history|export-chats) export_history "${CMD_ARGS[@]}" ;;
        import-history|import-chats) import_history "${CMD_ARGS[@]}" ;;
        export-suite|export-config) export_suite "${CMD_ARGS[@]}" ;;
        import-suite|import-config) import_suite "${CMD_ARGS[@]}" ;;
        export-all|export) export_all "${CMD_ARGS[@]}" ;;
        import-all|import) import_all "${CMD_ARGS[@]}" ;;
        backups|backup) manage_backups "${CMD_ARGS[@]}" ;;
        create-instance) create_instance "${CMD_ARGS[@]}" ;;
        list-instances) list_instances ;;
        set-history) set_history_mode "${CMD_ARGS[@]}" ;;
        remove-instance) remove_instance "${CMD_ARGS[@]}" ;;
        f5|patch-f5) FORCE_INSTALL=true patch_f5_reload ;;
        rtl|patch-rtl) FORCE_INSTALL=true dispatch_rtl ;;
        update-rtl) update_rtl ;;
        checksums|fix-checksums|patch-checksums) fix_ide_checksums "${IDE_INSTALL_DIR:-/opt/antigravity}" ;;
        update) dispatch_update ;;
        update-repo|self-update|update-self) update_suite_repo ;;
        restart-services|restart-service|restart-daemon|restart-daemons) restart_suite_services ;;
        clean-cache) clean_cache ;;
        help) show_help ;;
    esac
}
