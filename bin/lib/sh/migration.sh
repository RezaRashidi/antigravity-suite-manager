#!/usr/bin/env bash
# Cross-system export, import, and backup wrappers.

get_migration_script() {
    if [ -f "${LOCAL_BIN}/antigravity-migration.py" ]; then
        echo "${LOCAL_BIN}/antigravity-migration.py"
    elif [ -f "${SCRIPT_DIR}/bin/antigravity-migration.py" ]; then
        echo "${SCRIPT_DIR}/bin/antigravity-migration.py"
    elif [ -f "${SCRIPT_DIR}/antigravity-migration.py" ]; then
        echo "${SCRIPT_DIR}/antigravity-migration.py"
    fi
}

run_migration_action() {
    local action="$1"; shift
    local m_script
    m_script="$(get_migration_script)"
    [ -z "$m_script" ] && { log_err "antigravity-migration.py not found."; return 1; }
    python3 "$m_script" "$action" "$@"
}

export_history() { run_migration_action export-history "$@"; }
import_history() { run_migration_action import-history "$@"; }
export_suite()   { run_migration_action export-suite "$@"; }
import_suite()   { run_migration_action import-suite "$@"; }
export_all()     { run_migration_action export-all "$@"; }
import_all()     { run_migration_action import-all "$@"; }

manage_backups() {
    local m_script
    m_script="$(get_migration_script)"
    [ -z "$m_script" ] && { log_err "antigravity-migration.py not found."; return 1; }
    local act="${1:-list}"
    shift || true
    case "$act" in
        list)    python3 "$m_script" list-backups ;;
        create)  python3 "$m_script" create-backup "$@" ;;
        restore) python3 "$m_script" restore-backup "$@" ;;
        *)       echo "Usage: $(basename "$0") backups [list|create|restore <path>]" ;;
    esac
}
