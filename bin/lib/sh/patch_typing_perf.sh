#!/usr/bin/env bash
# Antigravity App & IDE Prompt Input Typing Lag & Reflow Optimization Patcher

get_typing_perf_patch_js() {
    local candidates=(
        "${SCRIPT_DIR}/bin/lib/patch/patch_typing_perf.js"
        "${SCRIPT_DIR}/lib/patch/patch_typing_perf.js"
        "${LOCAL_BIN}/patch_typing_perf.js"
        "${LOCAL_BIN}/lib/patch/patch_typing_perf.js"
    )
    for p in "${candidates[@]}"; do
        [ -f "$p" ] && { echo "$p"; return 0; }
    done
    return 1
}

_run_typing_perf_asar_op() {
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
    local p_js; p_js="$(get_typing_perf_patch_js)"

    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}. Skipping Typing Perf patch."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "patch_typing_perf.js not found."
        return 1
    fi

    if [ "$mode" = "patch" ] && [ "$FORCE_INSTALL" != true ] && grep -qa "ANTIGRAVITY_SUITE_TYPING_PERF_PATCH_V1" "$asar"; then
        log_info "Typing Perf patch already applied in app.asar (${APP_INSTALL_DIR})."
        return 0
    fi
    fix_permissions "$APP_INSTALL_DIR"

    if [ "$mode" = "patch" ]; then
        log_info "Applying Typing Lag & Reflow fix to Antigravity App at ${APP_INSTALL_DIR}..."
        local orig="${asar}.orig"
        [ ! -f "$orig" ] && cp -p "$asar" "$orig"
    else
        log_info "Removing Typing Lag & Reflow patch from Antigravity App at ${APP_INSTALL_DIR}..."
    fi

    local tmp; tmp=$(mktemp -d /tmp/asar_typing_perf_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    local node_args=("$p_js")
    [ "$mode" = "unpatch" ] && node_args+=("--unpatch")
    node_args+=("$tmp/unpacked")
    if ! node "${node_args[@]}"; then
        log_err "Typing Perf ${mode} script failed."
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
        log_success "Typing Lag & Reflow fix applied to Antigravity App."
    else
        log_success "Typing Lag & Reflow patch removed from Antigravity App."
    fi
}

patch_typing_perf_app() {
    _run_typing_perf_asar_op "patch" "$@"
}

unpatch_typing_perf_app() {
    _run_typing_perf_asar_op "unpatch" "$@"
}

patch_typing_perf_ide() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --force|-f) FORCE_INSTALL=true; shift ;;
            --ide-dir) IDE_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_ide_install_dir 2>/dev/null || return 0
    [ ! -d "${IDE_INSTALL_DIR}/resources/app/out" ] && { log_warn "IDE dir not found. Skipping Typing Perf IDE patch."; return 0; }

    local p_js; p_js="$(get_typing_perf_patch_js)"
    [ -z "$p_js" ] && { log_err "patch_typing_perf.js not found."; return 1; }

    local marker="${IDE_INSTALL_DIR}/resources/app/out/antigravity_ide_typing_perf_patch.marker"
    if [ "$FORCE_INSTALL" != true ] && [ -f "$marker" ]; then
        log_info "Typing Perf patch already applied to Antigravity IDE (${IDE_INSTALL_DIR})."
        return 0
    fi

    fix_permissions "$IDE_INSTALL_DIR"
    log_info "Applying Typing Lag & Reflow fix to Antigravity IDE at ${IDE_INSTALL_DIR}..."
    node "$p_js" --ide "${IDE_INSTALL_DIR}"
    fix_ide_checksums "${IDE_INSTALL_DIR}" 2>/dev/null || true
    log_success "Typing Lag & Reflow fix applied to Antigravity IDE."
}

unpatch_typing_perf_ide() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --ide-dir) IDE_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_ide_install_dir 2>/dev/null || return 0
    [ ! -d "${IDE_INSTALL_DIR}/resources/app/out" ] && return 0

    local p_js; p_js="$(get_typing_perf_patch_js)"
    [ -z "$p_js" ] && return 1

    log_info "Removing Typing Lag & Reflow patch from Antigravity IDE at ${IDE_INSTALL_DIR}..."
    node "$p_js" --ide --unpatch "${IDE_INSTALL_DIR}"
    fix_ide_checksums "${IDE_INSTALL_DIR}" 2>/dev/null || true
    log_success "Typing Lag & Reflow patch removed from Antigravity IDE."
}

patch_typing_perf() {
    local err=0
    patch_typing_perf_app "$@" || err=1
    patch_typing_perf_ide "$@" || true
    return $err
}

unpatch_typing_perf() {
    local err=0
    unpatch_typing_perf_app "$@" || err=1
    unpatch_typing_perf_ide "$@" || true
    return $err
}
