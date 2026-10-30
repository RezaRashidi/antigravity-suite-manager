#!/usr/bin/env bash
# Antigravity Native "Open in IDE" Titlebar Button Patcher

ensure_open_ide_symlink() {
    local ide_target="${IDE_INSTALL_DIR:-/opt/antigravity-ide}"
    local link_path="${REAL_HOME:-$HOME}/.local/share/antigravity-ide"
    if [ -d "$ide_target" ] && [ ! -e "$link_path" ]; then
        mkdir -p "$(dirname "$link_path")" 2>/dev/null || true
        ln -sf "$ide_target" "$link_path" 2>/dev/null || true
    fi
}

get_open_ide_patch_js() {
    local candidates=(
        "${SCRIPT_DIR}/bin/lib/patch/patch_open_ide.js"
        "${SCRIPT_DIR}/lib/patch/patch_open_ide.js"
        "${LOCAL_BIN}/patch_open_ide.js"
    )
    for p in "${candidates[@]}"; do
        [ -f "$p" ] && { echo "$p"; return 0; }
    done
    return 1
}

patch_open_ide_app() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --force|-f) FORCE_INSTALL=true; shift ;;
            --app-dir) APP_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_app_install_dir
    ensure_open_ide_symlink
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    local p_js; p_js="$(get_open_ide_patch_js)"

    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}. Skipping Open IDE patch."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "patch_open_ide.js not found."
        return 1
    fi

    if [ "$FORCE_INSTALL" != true ] && grep -qa "ANTIGRAVITY_SUITE_OPEN_IDE_PATCH_V1" "$asar"; then
        log_info "Native Open in IDE button already enabled in app.asar (${APP_INSTALL_DIR})."
        return 0
    fi
    log_info "Enabling native 'Open in IDE' titlebar button at ${APP_INSTALL_DIR}..."
    fix_permissions "$APP_INSTALL_DIR"

    local orig="${asar}.orig"
    [ ! -f "$orig" ] && cp -p "$asar" "$orig"

    local tmp; tmp=$(mktemp -d /tmp/asar_open_ide_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    if ! node "$p_js" "$tmp/unpacked"; then
        log_err "Open IDE patch script failed."
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
    log_success "Native 'Open in IDE' titlebar button enabled in Antigravity App."
}
