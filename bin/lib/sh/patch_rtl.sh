#!/usr/bin/env bash
# RTL integration for Antigravity App and IDE via mmnaderi/antigravity-rtl.

ensure_rtl_dirs() {
    auto_detect_installations 2>/dev/null || true
    if [ -z "$APP_INSTALL_DIR" ] || [ ! -f "${APP_INSTALL_DIR}/resources/app.asar" ]; then
        for c in "$APP_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_APP" "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity"; do
            [ -n "$c" ] && [ -f "${c}/resources/app.asar" ] && { APP_INSTALL_DIR="$c"; break; }
        done
    fi
    if [ -z "$IDE_INSTALL_DIR" ] || [ ! -d "${IDE_INSTALL_DIR}/resources/app/out" ]; then
        for c in "$IDE_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_IDE" "/opt/antigravity-ide" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity-ide"; do
            [ -n "$c" ] && [ -d "${c}/resources/app/out" ] && { IDE_INSTALL_DIR="$c"; break; }
        done
    fi
}

run_antigravity_rtl() {
    if command -v antigravity-rtl >/dev/null 2>&1; then
        antigravity-rtl "$@"
    elif [ -x "${REAL_HOME:-$HOME}/.local/bin/antigravity-rtl" ]; then
        "${REAL_HOME:-$HOME}/.local/bin/antigravity-rtl" "$@"
    elif [ -x "${REAL_HOME:-$HOME}/.local/node_modules/.bin/antigravity-rtl" ]; then
        "${REAL_HOME:-$HOME}/.local/node_modules/.bin/antigravity-rtl" "$@"
    elif command -v npx >/dev/null 2>&1; then
        npx --yes antigravity-rtl@latest "$@"
    else
        log_err "Neither 'antigravity-rtl' nor 'npx' is available."
        return 1
    fi
}

patch_rtl_app() {
    for arg in "$@"; do [ "$arg" = "--force" ] || [ "$arg" = "-f" ] && FORCE_INSTALL=true; done
    ensure_rtl_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    [ ! -f "$asar" ] && { log_warn "app.asar not found at ${asar}. Skipping RTL app patch."; return 0; }

    if [ "$FORCE_INSTALL" != true ] && grep -qa "ANTIGRAVITY RTL PATCH" "$asar"; then
        log_info "RTL patch is already applied to Antigravity App. Skipping."
        return 0
    elif [ "$FORCE_INSTALL" = true ] && grep -qa "ANTIGRAVITY RTL PATCH" "$asar"; then
        echo "y" | run_antigravity_rtl --restore --app --path "$asar" 2>/dev/null || true
    fi

    log_info "Ensuring permissions before RTL app patch..."
    fix_permissions "$APP_INSTALL_DIR"

    log_info "Applying RTL patch to Antigravity App (${asar})..."
    if ! echo "n" | run_antigravity_rtl --app --path "$asar"; then
        log_err "RTL app patch failed during execution."
        return 1
    fi

    if grep -qa "ANTIGRAVITY RTL PATCH" "$asar"; then
        log_success "RTL patch successfully applied and verified in ${asar}."
    else
        log_err "Verification failed: RTL patch marker not found in ${asar}!"
        return 1
    fi
}

patch_rtl_ide() {
    for arg in "$@"; do [ "$arg" = "--force" ] || [ "$arg" = "-f" ] && FORCE_INSTALL=true; done
    ensure_rtl_dirs
    [ ! -d "${IDE_INSTALL_DIR}" ] && { log_warn "IDE dir not found at ${IDE_INSTALL_DIR}. Skipping RTL IDE patch."; return 0; }

    local main_js="${IDE_INSTALL_DIR}/resources/app/out/main.js"
    if [ "$FORCE_INSTALL" != true ] && [ -f "$main_js" ]; then
        if grep -qa "antigravity-rtl-main.js" "$main_js" 2>/dev/null || [ -f "${main_js}.rtl-bak" ]; then
            log_info "RTL patch is already applied to Antigravity IDE. Skipping."
            return 0
        fi
    elif [ "$FORCE_INSTALL" = true ] && [ -f "${main_js}.rtl-bak" ]; then
        echo "y" | run_antigravity_rtl --restore --ide --path "${IDE_INSTALL_DIR}" 2>/dev/null || true
    fi

    log_info "Ensuring permissions before RTL IDE patch..."
    fix_permissions "$IDE_INSTALL_DIR"

    log_info "Applying RTL patch to Antigravity IDE (${IDE_INSTALL_DIR})..."
    if ! echo "n" | run_antigravity_rtl --ide --path "${IDE_INSTALL_DIR}"; then
        log_err "RTL IDE patch failed during execution."
        return 1
    fi

    log_success "RTL patch successfully applied to Antigravity IDE."
    fix_ide_checksums "${IDE_INSTALL_DIR}"
}

fix_ide_checksums() {
    local target_ide="${1:-$IDE_INSTALL_DIR}"
    [ ! -d "$target_ide" ] && return 0
    local cs_tool="${LOCAL_BIN}/antigravity-checksums.py"
    if [ ! -f "$cs_tool" ]; then
        local s_dir
        s_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
        [ -f "${s_dir}/bin/antigravity-checksums.py" ] && cs_tool="${s_dir}/bin/antigravity-checksums.py"
    fi
    if [ -f "$cs_tool" ]; then
        python3 "$cs_tool" "$target_ide" 2>/dev/null || true
    fi
}

patch_rtl_all() {
    patch_rtl_app "$@"
    patch_rtl_ide "$@"
    patch_f5_reload "$@"
}

update_rtl() {
    log_info "Updating antigravity-rtl package..."
    npm cache clean --force 2>/dev/null || true
    ensure_rtl_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    [ -f "$asar" ] && echo "y" | run_antigravity_rtl --restore --app --path "$asar" 2>/dev/null || true
    [ -d "${IDE_INSTALL_DIR}" ] && echo "y" | run_antigravity_rtl --restore --ide --path "${IDE_INSTALL_DIR}" 2>/dev/null || true
    FORCE_INSTALL=true patch_rtl_all
    [ -d "${IDE_INSTALL_DIR}" ] && fix_ide_checksums "${IDE_INSTALL_DIR}"
}
