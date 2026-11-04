#!/usr/bin/env bash
# One-Shot Chat Migrator (v2.5.5 -> v2.6.0)

dispatch_migrate_chats() {
    local migrator=""
    for cand in "${LOCAL_BIN}/antigravity-migrate-chats.py" \
                "${SCRIPT_DIR}/bin/antigravity-migrate-chats.py" \
                "${ANTIGRAVITY_SUITE_DIR}/bin/antigravity-migrate-chats.py"; do
        if [ -n "$cand" ] && [ -f "$cand" ]; then
            migrator="$cand"
            break
        fi
    done

    if [ -n "$migrator" ]; then
        python3 "$migrator" "$@"
    else
        log_err "antigravity-migrate-chats.py not found."
        return 1
    fi
}

dispatch_merger() {
    dispatch_migrate_chats "$@"
}
