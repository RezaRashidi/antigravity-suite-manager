#!/usr/bin/env bash
# CLI argument and flag parser

parse_cli_args() {
    COMMAND=""; SUB_COMMAND=""; CMD_ARGS=(); START_STEP=1; ONLY_STEP=0; NON_INTERACTIVE=false

    while [ $# -gt 0 ]; do
        local flag_shift=0
        parse_config_flag "$1" "${2:-}" || flag_shift=$?
        if [ "$flag_shift" -gt 0 ]; then shift "$flag_shift"; continue; fi

        case "$1" in
            custom-models|models) COMMAND="models"; shift; CMD_ARGS=("$@"); break ;;
            cloud-sync|cloud) COMMAND="cloud-sync"; shift; CMD_ARGS=("$@"); break ;;
            merge-history|merge) COMMAND="merge-history"; shift ;;
            export-history|export-chats) COMMAND="export-history"; shift; CMD_ARGS=("$@"); break ;;
            import-history|import-chats) COMMAND="import-history"; shift; CMD_ARGS=("$@"); break ;;
            export-suite|export-config) COMMAND="export-suite"; shift; CMD_ARGS=("$@"); break ;;
            import-suite|import-config) COMMAND="import-suite"; shift; CMD_ARGS=("$@"); break ;;
            export-all|export) COMMAND="export-all"; shift; CMD_ARGS=("$@"); break ;;
            import-all|import) COMMAND="import-all"; shift; CMD_ARGS=("$@"); break ;;
            backups|backup) COMMAND="backups"; shift; CMD_ARGS=("$@"); break ;;
            create-instance|add-instance|add) COMMAND="create-instance"; shift; CMD_ARGS=("$@"); break ;;
            list-instances|list) COMMAND="list-instances"; shift ;;
            set-history|toggle-history) COMMAND="set-history"; shift; CMD_ARGS=("$@"); break ;;
            remove-instance|remove) COMMAND="remove-instance"; shift; CMD_ARGS=("$@"); break ;;
            detect|scan|find) COMMAND="detect"; shift ;;
            install) COMMAND="install"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            install-all) COMMAND="install"; SUB_COMMAND="all"; shift ;;
            install-app) COMMAND="install"; SUB_COMMAND="app"; shift ;;
            install-ide) COMMAND="install"; SUB_COMMAND="ide"; shift ;;
            set-keyring|keyring) COMMAND="keyring"; shift; CMD_ARGS=("$@"); break ;;
            paths|set-paths) COMMAND="paths"; shift; CMD_ARGS=("$@"); break ;;
            wizard|setup|center|control-center) COMMAND="wizard"; shift; CMD_ARGS=("$@"); break ;;
            rtl|patch-rtl) COMMAND="rtl"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            unpatch-rtl) COMMAND="unpatch-rtl"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi; CMD_ARGS=("$@"); break ;;
            f5|patch-f5) COMMAND="f5"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            unpatch-f5) COMMAND="unpatch-f5"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi; CMD_ARGS=("$@"); break ;;
            selector|patch-selector) COMMAND="patch-selector"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            unpatch-selector) COMMAND="unpatch-selector"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            fork|patch-fork) COMMAND="fork"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            unpatch-fork) COMMAND="unpatch-fork"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            open-ide|patch-open-ide) COMMAND="open-ide"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            unpatch-open-ide) COMMAND="unpatch-open-ide"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            clean-data|delete-data|purge-data) COMMAND="clean-data"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi; CMD_ARGS=("$@"); break ;;
            uninstall) COMMAND="uninstall"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi; CMD_ARGS=("$@"); break ;;
            set-icons|icons) COMMAND="set-icons"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            update) COMMAND="update"; shift; if [ -n "${1:-}" ] && [[ "$1" != -* ]]; then SUB_COMMAND="$1"; shift; fi ;;
            update-all) COMMAND="update"; SUB_COMMAND="all"; shift ;;
            update-app) COMMAND="update"; SUB_COMMAND="app"; shift ;;
            update-ide) COMMAND="update"; SUB_COMMAND="ide"; shift ;;
            update-f5) COMMAND="update"; SUB_COMMAND="f5"; shift ;;
            update-repo|self-update|update-self|24) COMMAND="update-repo"; shift ;;
            benchmark|bench|speed-test|26) COMMAND="benchmark"; shift; CMD_ARGS=("$@"); break ;;
            multi-account|multiaccount|accounts|27) COMMAND="multi-account"; shift; CMD_ARGS=("$@"); break ;;
            unpatch|restore|revert-patch|unpatch-all) COMMAND="unpatch"; shift ;;
            trace|monitor|traffic) COMMAND="traffic"; shift; break ;;
            restart-services|restart-service|restart-daemon|25) COMMAND="restart-services"; shift ;;
            status|all|app|ide|app1|app2|ide-shortcuts|update-rtl|clean-cache|help) COMMAND="$1"; shift ;;
            -h|--help) show_help; exit 0 ;;
            *) log_err "Unknown argument: $1"; show_help; exit 1 ;;
        esac
    done
}
