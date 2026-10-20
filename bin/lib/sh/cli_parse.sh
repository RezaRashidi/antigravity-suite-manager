#!/usr/bin/env bash
# CLI argument and flag parser

parse_cli_args() {
    COMMAND=""
    SUB_COMMAND=""
    CMD_ARGS=()

    while [ $# -gt 0 ]; do
        case "$1" in
            --app-url) APP_URL="$2"; shift 2 ;;
            --ide-url) IDE_URL="$2"; shift 2 ;;
            --app-dir) APP_INSTALL_DIR="$2"; CLI_APP_DIR_SPECIFIED=true; shift 2 ;;
            --ide-dir) IDE_INSTALL_DIR="$2"; CLI_IDE_DIR_SPECIFIED=true; shift 2 ;;
            --cache-dir) CACHE_DIR="$2"; shift 2 ;;
            --acc1-icon) ACC1_ICON_THEME="$2"; CLI_ICON_GIVEN=true; shift 2 ;;
            --acc2-icon) ACC2_ICON_THEME="$2"; CLI_ICON_GIVEN=true; shift 2 ;;
            --acc2-recolor) ACC2_RECOLOR="$2"; CLI_ICON_GIVEN=true; shift 2 ;;
            --ide-icon) IDE_ICON_THEME="$2"; CLI_ICON_GIVEN=true; shift 2 ;;
            --force|-f) FORCE_INSTALL=true; shift ;;
            --no-cache) USE_CACHE=false; shift ;;
            --skip-rtl) SKIP_RTL=true; shift ;;
            --skip-f5) SKIP_F5=true; shift ;;
            merge-history|merge) COMMAND="merge-history"; shift ;;
            export-history|export-chats) COMMAND="export-history"; shift; CMD_ARGS=("$@"); break ;;
            import-history|import-chats) COMMAND="import-history"; shift; CMD_ARGS=("$@"); break ;;
            export-suite|export-config) COMMAND="export-suite"; shift; CMD_ARGS=("$@"); break ;;
            import-suite|import-config) COMMAND="import-suite"; shift; CMD_ARGS=("$@"); break ;;
            export-all|export) COMMAND="export-all"; shift; CMD_ARGS=("$@"); break ;;
            import-all|import) COMMAND="import-all"; shift; CMD_ARGS=("$@"); break ;;
            backups|backup) COMMAND="backups"; shift; CMD_ARGS=("$@"); break ;;
            create-instance|add-instance|add-profile|create-profile|add)
                COMMAND="create-instance"; shift; CMD_ARGS=("$@"); break ;;
            list-instances|list-profiles|list) COMMAND="list-instances"; shift ;;
            set-history|toggle-history) COMMAND="set-history"; shift; CMD_ARGS=("$@"); break ;;
            remove-instance|delete-instance|remove)
                COMMAND="remove-instance"; shift; CMD_ARGS=("$@"); break ;;
            detect|scan|find|find-installations) COMMAND="detect"; shift ;;
            install)
                COMMAND="install"; shift
                if [ -n "$1" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            install-all) COMMAND="install"; SUB_COMMAND="all"; shift ;;
            install-app) COMMAND="install"; SUB_COMMAND="app"; shift ;;
            install-ide) COMMAND="install"; SUB_COMMAND="ide"; shift ;;
            set-keyring|keyring|switch-keyring|toggle-keyring)
                COMMAND="keyring"; shift; CMD_ARGS=("$@"); break ;;
            paths|set-paths) COMMAND="paths"; shift; CMD_ARGS=("$@"); break ;;
            wizard|setup|center|control-center) COMMAND="wizard"; shift; CMD_ARGS=("$@"); break ;;
            rtl|patch-rtl)
                COMMAND="rtl"; shift
                if [ -n "$1" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            f5|patch-f5) COMMAND="f5"; shift ;;
            set-icons|icons)
                COMMAND="set-icons"; shift
                if [ -n "$1" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            update)
                COMMAND="update"; shift
                if [ -n "$1" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            update-all) COMMAND="update"; SUB_COMMAND="all"; shift ;;
            update-app) COMMAND="update"; SUB_COMMAND="app"; shift ;;
            update-ide) COMMAND="update"; SUB_COMMAND="ide"; shift ;;
            update-f5) COMMAND="update"; SUB_COMMAND="f5"; shift ;;
            update-repo|self-update|update-self|24) COMMAND="update-repo"; shift ;;
            benchmark|bench|speed-test|26) COMMAND="benchmark"; shift; CMD_ARGS=("$@"); break ;;
            multi-account|multiaccount|accounts|27) COMMAND="multi-account"; shift; CMD_ARGS=("$@"); break ;;
            patch-accounts|patch-selector) COMMAND="patch-accounts"; shift ;;
            unpatch|restore|revert-patch) COMMAND="unpatch"; shift ;;
            restart-services|restart-service|restart-daemon|restart-daemons|25) COMMAND="restart-services"; shift ;;
            status|all|app|ide|app1|app2|ide-shortcuts|update-rtl|clean-cache|help)
                COMMAND="$1"; shift ;;
            -h|--help) show_help; exit 0 ;;
            *) log_err "Unknown argument: $1"; show_help; exit 1 ;;
        esac
    done
}
