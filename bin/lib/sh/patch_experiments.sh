#!/usr/bin/env bash
# Antigravity Unified Experiments, Conversation Forking, Cost & Open-IDE Patcher (App & IDE)

patch_experiments_app() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --force|-f) FORCE_INSTALL=true; shift ;;
            --app-dir) APP_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_experiments_dirs
    ensure_open_ide_symlink
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    local p_js; p_js="$(get_experiments_patch_js)"

    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}. Skipping App experiments patch."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-experiments-patch.js not found."
        return 1
    fi

    if [ "$FORCE_INSTALL" != true ] && grep -qa "ANTIGRAVITY_SUITE_EXPERIMENTS_PATCH_V1" "$asar"; then
        log_info "Unified Experiments/Fork/Open-IDE patch already applied to app.asar (${APP_INSTALL_DIR})."
        return 0
    fi
    log_info "Applying Unified Experiments, Forking, Cost & Open-IDE patch to App at ${APP_INSTALL_DIR}..."
    fix_permissions "$APP_INSTALL_DIR"

    local orig="${asar}.orig"
    [ ! -f "$orig" ] && cp -p "$asar" "$orig"

    local tmp; tmp=$(mktemp -d /tmp/asar_exp_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    if ! node "$p_js" --app "$tmp/unpacked"; then
        log_err "Experiments patch script failed for App."
        rm -rf "$tmp"
        return 1
    fi

    if ! run_asar pack "$tmp/unpacked" "$tmp/app.asar.patched" --unpack "*.node"; then
        log_err "Failed to pack patched app.asar."
        rm -rf "$tmp"
        return 1
    fi

    cp "$tmp/app.asar.patched" "$asar"
    rm -rf "$tmp"
    log_success "Experiment Flags & Context/Cost applied to Antigravity App (${APP_INSTALL_DIR})."
}

patch_experiments_ide() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --force|-f) FORCE_INSTALL=true; shift ;;
            --ide-dir) IDE_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_experiments_dirs
    check_ide_min_version "${IDE_INSTALL_DIR}" || return 1
    local p_js; p_js="$(get_experiments_patch_js)"
    if [ -z "$IDE_INSTALL_DIR" ] || [ ! -d "${IDE_INSTALL_DIR}/resources/app/out" ]; then
        log_warn "IDE out directory not found at ${IDE_INSTALL_DIR:-'<undefined>'}. Skipping IDE experiments patch."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-experiments-patch.js not found."
        return 1
    fi

    log_info "Applying Unified Experiments, Forking & Cost patch to IDE at ${IDE_INSTALL_DIR}..."
    fix_permissions "$IDE_INSTALL_DIR"
    node "$p_js" --ide "$IDE_INSTALL_DIR"
    if declare -f fix_ide_checksums >/dev/null 2>&1; then
        fix_ide_checksums "$IDE_INSTALL_DIR" 2>/dev/null || true
    fi
    log_success "Unified Experiments, Forking & Cost applied to Antigravity IDE (${IDE_INSTALL_DIR})."
}

patch_experiments_all() {
    log_info "Applying Unified Experiments, Forking, Cost & Open-IDE to All Targets (App & IDE)..."
    patch_experiments_app "$@"
    patch_experiments_ide "$@"
}
