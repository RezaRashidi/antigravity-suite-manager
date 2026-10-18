#!/usr/bin/env bash
# Antigravity IDE shortcuts setup orchestrator.

setup_ide_shortcuts() {
    log_info "Configuring Antigravity IDE shortcuts..."

    auto_detect_installations
    if [ -z "$IDE_INSTALL_DIR" ] || [ ! -f "${IDE_INSTALL_DIR}/antigravity-ide" ]; then
        for cand in "$IDE_INSTALL_DIR" "/opt/antigravity-ide" "/opt/antigravity" "/opt/antigravity2"; do
            if [ -n "$cand" ] && [ -f "${cand}/antigravity-ide" ]; then
                IDE_INSTALL_DIR="$cand"
                break
            fi
        done
    fi
    IDE_INSTALL_DIR="${IDE_INSTALL_DIR:-/opt/antigravity-ide}"

    apply_icons_config || true

    local ide_pass_store=""
    mkdir -p "${REAL_HOME}/.gemide/cache"
    if [ "$KEYRING_MODE_IDE" = "normal" ]; then
        ide_pass_store="--password-store=basic "
        touch "${REAL_HOME}/.gemide/cache/antigravity-keyring-unavailable"
    else
        rm -f "${REAL_HOME}/.gemide/cache/antigravity-keyring-unavailable" 2>/dev/null || true
    fi

    write_ide_launcher_and_desktop "$ide_pass_store"
    setup_ide_sharing

    merge_history
    enable_sync_service

    log_success "Antigravity IDE shortcuts & 3-way shared history configured."
}
