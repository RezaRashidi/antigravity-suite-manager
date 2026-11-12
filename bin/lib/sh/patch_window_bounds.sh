#!/usr/bin/env bash
# Antigravity App X11 BaseWindow / WebContentsView Bounds Patcher

get_window_bounds_patch_js() {
    local candidates=(
        "${SCRIPT_DIR}/bin/lib/patch/patch_window_bounds.js"
        "${SCRIPT_DIR}/lib/patch/patch_window_bounds.js"
        "${LOCAL_BIN}/patch_window_bounds.js"
    )
    for p in "${candidates[@]}"; do
        [ -f "$p" ] && { echo "$p"; return 0; }
    done
    return 1
}

_run_window_bounds_asar_op() {
    local mode="$1"; shift
    while [ $# -gt 0 ]; do
        case "$1" in
            --force|-f) FORCE_INSTALL=true; shift ;;
            --app-dir) APP_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_app_install_dir
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    local p_js; p_js="$(get_window_bounds_patch_js)"

    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}. Skipping Window Bounds patch."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "patch_window_bounds.js not found."
        return 1
    fi

    if [ "$mode" = "patch" ] && [ "$FORCE_INSTALL" != true ] && grep -qa "ANTIGRAVITY_SUITE_WINDOW_BOUNDS_PATCH_V1" "$asar"; then
        log_info "Window Bounds patch already applied in app.asar (${APP_INSTALL_DIR})."
        return 0
    fi
    fix_permissions "$APP_INSTALL_DIR"

    if [ "$mode" = "patch" ]; then
        log_info "Applying X11 Window Bounds fix to Antigravity App at ${APP_INSTALL_DIR}..."
        local orig="${asar}.orig"
        [ ! -f "$orig" ] && cp -p "$asar" "$orig"
    else
        log_info "Removing X11 Window Bounds patch from Antigravity App at ${APP_INSTALL_DIR}..."
    fi

    local tmp; tmp=$(mktemp -d /tmp/asar_win_bounds_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    local node_args=("$p_js")
    [ "$mode" = "unpatch" ] && node_args+=("--unpatch")
    node_args+=("$tmp/unpacked")
    if ! node "${node_args[@]}"; then
        log_err "Window Bounds ${mode} script failed."
        rm -rf "$tmp"
        return 1
    fi

    if ! run_asar pack "$tmp/unpacked" "$tmp/app.asar.patched" --unpack "*.node"; then
        log_err "Failed to pack app.asar."
        rm -rf "$tmp"
        return 1
    fi

    cp "$tmp/app.asar.patched" "$asar"
    rm -rf "$tmp"
    if [ "$mode" = "patch" ]; then
        log_success "X11 Window Bounds fix applied to Antigravity App."
    else
        log_success "X11 Window Bounds patch removed from Antigravity App."
    fi
}

patch_window_bounds_app() {
    _run_window_bounds_asar_op "patch" "$@"
}

unpatch_window_bounds_app() {
    _run_window_bounds_asar_op "unpatch" "$@"
}
