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

dispatch_selector() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app) patch_selector_app "$@" ;;
        ide) patch_selector_ide "$@" ;;
        all|*) patch_selector "$@" ;;
    esac
}

dispatch_unpatch_selector() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app) unpatch_selector_app "$@" ;;
        ide) unpatch_selector_ide "$@" ;;
        all|*) unpatch_selector "$@" ;;
    esac
}

dispatch_f5() {
    auto_detect_installations
    FORCE_INSTALL=true patch_f5_reload "$@"
}

dispatch_unpatch_f5() {
    auto_detect_installations
    unpatch_f5 "$@"
}

dispatch_fork() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app) patch_fork_app "$@" ;;
        ide) patch_fork_ide "$@" ;;
        all|*) patch_fork_all "$@" ;;
    esac
}

dispatch_unpatch_fork() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app) unpatch_fork_app "$@" ;;
        ide) unpatch_fork_ide "$@" ;;
        all|*) unpatch_fork_all "$@" ;;
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
