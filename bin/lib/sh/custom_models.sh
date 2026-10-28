#!/usr/bin/env bash
# Antigravity Custom Models CLI dispatch and proxy manager

get_models_py() {
    local sdir
    sdir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
    local mpy="${sdir}/bin/antigravity-models.py"
    if [ ! -f "$mpy" ]; then
        mpy="${REAL_HOME:-$HOME}/.antigravity-suite-manager/bin/antigravity-models.py"
    fi
    echo "$mpy"
}

get_vendor_proxy_script() {
    local sdir
    sdir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
    local vscript="${sdir}/vendor/antigravity-model-proxy/scripts/desktop-service.mjs"
    if [ ! -f "$vscript" ]; then
        vscript="${REAL_HOME:-$HOME}/.antigravity-suite-manager/vendor/antigravity-model-proxy/scripts/desktop-service.mjs"
    fi
    echo "$vscript"
}

dispatch_custom_models() {
    local action="${1:-status}"
    shift || true
    local mpy
    mpy="$(get_models_py)"

    if [ "$action" = "menu" ] || [ "$action" = "interactive" ]; then
        custom_models_menu
        return $?
    fi

    if [ -f "$mpy" ] && command -v python3 >/dev/null 2>&1; then
        python3 "$mpy" "$action" "$@"
        return $?
    fi

    echo -e "\033[0;31m[ERROR]\033[0m Python 3 or antigravity-models.py not found."
    return 1
}

start_model_proxy_service() {
    local vscript
    vscript="$(get_vendor_proxy_script)"
    if [ -f "$vscript" ] && command -v node >/dev/null 2>&1; then
        node "$vscript" start
        return $?
    fi
    dispatch_custom_models proxy-start
}

stop_model_proxy_service() {
    local vscript
    vscript="$(get_vendor_proxy_script)"
    if [ -f "$vscript" ] && command -v node >/dev/null 2>&1; then
        node "$vscript" stop
        return $?
    fi
    dispatch_custom_models proxy-stop
}

model_proxy_service_status() {
    local vscript
    vscript="$(get_vendor_proxy_script)"
    if [ -f "$vscript" ] && command -v node >/dev/null 2>&1; then
        node "$vscript" status
        return $?
    fi
    dispatch_custom_models proxy-status
}
