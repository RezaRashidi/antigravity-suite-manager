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

dispatch_rtl() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app)
            patch_rtl_app
            patch_f5_reload
            ;;
        ide)
            patch_rtl_ide
            ;;
        all|*)
            patch_rtl_all
            ;;
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
