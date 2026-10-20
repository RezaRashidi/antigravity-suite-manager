#!/usr/bin/env bash
# Multi-Account subsystem dispatcher and management

dispatch_multi_account() {
    local m_script=""
    if [ -n "${LOCAL_BIN:-}" ] && [ -f "${LOCAL_BIN}/antigravity-multi-account.py" ]; then
        m_script="${LOCAL_BIN}/antigravity-multi-account.py"
    elif command -v antigravity-multi-account.py >/dev/null 2>&1; then
        m_script="$(command -v antigravity-multi-account.py)"
    else
        local sdir
        sdir="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
        [ -f "${sdir}/bin/antigravity-multi-account.py" ] && m_script="${sdir}/bin/antigravity-multi-account.py"
        [ -f "${sdir}/antigravity-multi-account.py" ] && m_script="${sdir}/antigravity-multi-account.py"
    fi

    local subcmd="${1:-list}"
    shift 2>/dev/null || true

    if [ -n "$m_script" ] && [ -f "$m_script" ]; then
        python3 "$m_script" "$subcmd" "$@"
        return $?
    fi

    if python3 -c "import antigravity_suite.multi_account" >/dev/null 2>&1; then
        python3 -m antigravity_suite.multi_account.cli "$subcmd" "$@"
        return $?
    fi

    log_err "antigravity-multi-account.py not found. Please run Option 24 (Update Suite Manager Repository) or git pull."
    return 1
}
