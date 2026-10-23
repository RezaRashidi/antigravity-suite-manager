#!/usr/bin/env bash
# Antigravity IDE and unified Account Selector Patcher

patch_selector_ide() {
    ensure_selector_dirs
    ensure_keyring_decoupled
    local ide="${IDE_INSTALL_DIR}"
    local p_js; p_js="$(get_selector_patch_js)"

    if [ ! -d "$ide" ]; then
        log_warn "Antigravity IDE directory not found at ${ide:-'<undefined>'}. Skipping IDE selector patch."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-selector-patch.js not found."
        return 1
    fi

    local marker="${ide}/resources/app/out/antigravity_ide_selector_patch.marker"
    if [ "$FORCE_INSTALL" != true ] && [ -f "$marker" ]; then
        log_info "Account selector already applied to IDE (${ide})."
        return 0
    fi
    log_info "Applying account selector to Antigravity IDE at ${ide}..."
    fix_permissions "$ide"
    check_and_prep_ide_ls "$ide"
    if ! node "$p_js" --ide "$ide"; then
        log_err "Selector patch script failed for IDE."
        return 1
    fi
    sync_selector_skills
    fix_ide_checksums "$ide"
    log_success "Account selector applied to Antigravity IDE (${ide})."
}

unpatch_selector_ide() {
    ensure_selector_dirs
    local ide="${IDE_INSTALL_DIR}"
    local p_js; p_js="$(get_selector_patch_js)"

    if [ ! -d "$ide" ]; then
        log_warn "Antigravity IDE directory not found at ${ide:-'<undefined>'}."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-selector-patch.js not found."
        return 1
    fi

    log_info "Removing account selector from Antigravity IDE at ${ide}..."
    fix_permissions "$ide"
    check_and_prep_ide_ls "$ide"
    if ! node "$p_js" --ide --unpatch "$ide"; then
        log_err "Selector unpatch script failed for IDE."
        return 1
    fi
    fix_ide_checksums "$ide"
    log_success "Account selector removed from Antigravity IDE (${ide})."
}

patch_selector() {
    ensure_keyring_decoupled
    for arg in "$@"; do [ "$arg" = "--force" ] || [ "$arg" = "-f" ] && FORCE_INSTALL=true; done
    case "${SUB_COMMAND:-${1:-all}}" in
        app) patch_selector_app "$@" ;;
        ide) patch_selector_ide "$@" ;;
        all|*)
            local err=0
            patch_selector_app "$@" || err=1
            patch_selector_ide "$@" || err=1
            return $err
            ;;
    esac
}

unpatch_selector() {
    case "${SUB_COMMAND:-${1:-all}}" in
        app) unpatch_selector_app "$@" ;;
        ide) unpatch_selector_ide "$@" ;;
        all|*)
            local err=0
            unpatch_selector_app "$@" || err=1
            unpatch_selector_ide "$@" || err=1
            return $err
            ;;
    esac
}
