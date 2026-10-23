#!/usr/bin/env bash
# Helper dispatchers for complex CLI commands

dispatch_install() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app) install_antigravity_app ;;
        ide) install_antigravity_ide ;;
        all|*) install_antigravity_all ;;
    esac
}

dispatch_update() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app) update_app ;;
        ide) update_ide ;;
        rtl) update_rtl ;;
        f5) FORCE_INSTALL=true patch_f5_reload ;;
        checksums) fix_ide_checksums "${IDE_INSTALL_DIR:-/opt/antigravity}" ;;
        repo|self) update_suite_repo ;;
        services|service|daemons) restart_suite_services ;;
        all|*) update_all ;;
    esac
}

dispatch_clean_data() {
    if [ -z "$SUB_COMMAND" ] && [ ${#CMD_ARGS[@]} -eq 0 ]; then
        clean_data_interactive
        return 0
    fi
    case "${SUB_COMMAND:-all}" in
        app) clean_app_data "${CMD_ARGS[@]}" ;;
        ide) clean_ide_data "${CMD_ARGS[@]}" ;;
        history) clean_history_data "${CMD_ARGS[@]}" ;;
        all|*) clean_all_data "${CMD_ARGS[@]}" ;;
    esac
}

dispatch_uninstall() {
    if [ -z "$SUB_COMMAND" ] && [ ${#CMD_ARGS[@]} -eq 0 ]; then
        uninstall_menu_interactive
        return 0
    fi
    case "${SUB_COMMAND:-all}" in
        app) uninstall_app "${CMD_ARGS[@]}" ;;
        ide) uninstall_ide "${CMD_ARGS[@]}" ;;
        all|*) uninstall_all "${CMD_ARGS[@]}" ;;
    esac
}

dispatch_keyring() {
    if [ ${#CMD_ARGS[@]} -eq 0 ]; then
        configure_keyring_interactive
    else
        case "${CMD_ARGS[0]}" in
            status) keyring_status ;;
            purge|clean) keyring_purge ;;
            set) keyring_command "${CMD_ARGS[@]}" ;;
            *)
                if [ ${#CMD_ARGS[@]} -ge 2 ]; then
                    keyring_command set "${CMD_ARGS[0]}" "${CMD_ARGS[1]}"
                else
                    keyring_command "${CMD_ARGS[@]}"
                fi
                ;;
        esac
    fi
}

dispatch_traffic() {
    mkdir -p "${HOME}/.config/antigravity/accounts"
    touch "${HOME}/.config/antigravity/accounts/traffic.log"
    echo "Streaming real-time multi-account request traffic (Ctrl+C to exit)..."
    tail -f "${HOME}/.config/antigravity/accounts/traffic.log"
}
