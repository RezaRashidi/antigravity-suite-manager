#!/usr/bin/env bash
# Routines to revert Experiment Flags & DevUI Context/Cost patch from App and IDE

unpatch_experiments_app() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --app-dir) APP_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_experiments_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    local p_js; p_js="$(get_experiments_patch_js)"

    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-experiments-patch.js not found."
        return 1
    fi

    log_info "Removing Experiment Flags patch from Antigravity App at ${APP_INSTALL_DIR}..."
    fix_permissions "$APP_INSTALL_DIR"

    local tmp; tmp=$(mktemp -d /tmp/asar_exp_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    if ! node "$p_js" --unpatch --app "$tmp/unpacked"; then
        log_err "Experiments unpatch script failed for App."
        rm -rf "$tmp"
        return 1
    fi

    if ! run_asar pack "$tmp/unpacked" "$tmp/app.asar.patched" --unpack "*.node"; then
        log_err "Failed to pack unpatched app.asar."
        rm -rf "$tmp"
        return 1
    fi

    cp "$tmp/app.asar.patched" "$asar"
    rm -rf "$tmp"
    log_success "Experiment Flags patch removed from Antigravity App (${APP_INSTALL_DIR})."
}

unpatch_experiments_ide() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --ide-dir) IDE_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_experiments_dirs
    local p_js; p_js="$(get_experiments_patch_js)"
    if [ -z "$IDE_INSTALL_DIR" ] || [ ! -d "${IDE_INSTALL_DIR}/resources/app/out" ]; then
        log_warn "IDE out directory not found at ${IDE_INSTALL_DIR:-'<undefined>'}."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-experiments-patch.js not found."
        return 1
    fi

    log_info "Removing Experiment Flags patch from Antigravity IDE at ${IDE_INSTALL_DIR}..."
    fix_permissions "$IDE_INSTALL_DIR"
    node "$p_js" --unpatch --ide "$IDE_INSTALL_DIR"
    if declare -f fix_ide_checksums >/dev/null 2>&1; then
        fix_ide_checksums "$IDE_INSTALL_DIR" 2>/dev/null || true
    fi
    log_success "Experiment Flags patch removed from Antigravity IDE (${IDE_INSTALL_DIR})."
}

unpatch_experiments_all() {
    log_info "Removing Experiment Flags patch from All Targets (App & IDE)..."
    unpatch_experiments_app "$@"
    unpatch_experiments_ide "$@"
}
