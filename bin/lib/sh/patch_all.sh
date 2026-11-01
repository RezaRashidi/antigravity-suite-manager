#!/usr/bin/env bash
# Apply all patches to Antigravity App and/or IDE in dependency order

patch_all_app() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --force|-f) FORCE_INSTALL=true; shift ;;
            --app-dir) APP_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_rtl_dirs 2>/dev/null || auto_detect_installations 2>/dev/null || true
    log_info "Applying all patches to Antigravity App (${APP_INSTALL_DIR})..."

    # 1. Custom Models Settings UI
    if [ -f "$(get_models_deploy_script 2>/dev/null)" ]; then
        log_info "[1/6] In-App Custom Models UI patch..."
        FORCE_INSTALL=true patch_models_app || log_warn "Custom Models patch skipped or failed."
    fi

    # 2. RTL Typography
    log_info "[2/6] RTL Typography patch..."
    FORCE_INSTALL=true patch_rtl_app || log_warn "RTL patch skipped or failed."

    # 3. F5 Reload & isolation
    log_info "[3/6] F5 reload & isolation patch..."
    FORCE_INSTALL=true patch_f5_reload || log_warn "F5 reload patch skipped or failed."

    # 4. Multi-Account Selector
    log_info "[4/6] Prompt-bar Multi-Account Selector patch..."
    FORCE_INSTALL=true patch_selector_app || log_warn "Selector patch skipped or failed."

    # 5. Conversation Forking
    log_info "[5/6] Conversation Forking patch..."
    FORCE_INSTALL=true patch_fork_app || log_warn "Forking patch skipped or failed."

    # 6. Native Open in IDE button
    log_info "[6/6] Native Open in IDE titlebar button patch..."
    FORCE_INSTALL=true patch_open_ide_app || log_warn "Open in IDE patch skipped or failed."

    log_success "All patches applied to Antigravity App (${APP_INSTALL_DIR})."
}

patch_all_ide() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --force|-f) FORCE_INSTALL=true; shift ;;
            --ide-dir) IDE_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_rtl_dirs 2>/dev/null || auto_detect_installations 2>/dev/null || true
    log_info "Applying all patches to Antigravity IDE (${IDE_INSTALL_DIR})..."

    # 1. RTL Typography
    log_info "[1/4] RTL Typography patch..."
    FORCE_INSTALL=true patch_rtl_ide || log_warn "RTL patch skipped or failed."

    # 2. Multi-Account Selector
    log_info "[2/4] Multi-Account Selector patch..."
    FORCE_INSTALL=true patch_selector_ide || log_warn "Selector patch skipped or failed."

    # 3. Conversation Forking
    log_info "[3/4] Conversation Forking patch..."
    FORCE_INSTALL=true patch_fork_ide || log_warn "Forking patch skipped or failed."

    # 4. Checksums fix
    log_info "[4/4] Fixing IDE workbench checksums..."
    fix_ide_checksums "${IDE_INSTALL_DIR}" || true

    log_success "All patches applied to Antigravity IDE (${IDE_INSTALL_DIR})."
}

patch_all() {
    local target="all"
    local pass_args=()
    while [ $# -gt 0 ]; do
        case "$1" in
            app) target="app"; shift ;;
            ide) target="ide"; shift ;;
            all) target="all"; shift ;;
            *) pass_args+=("$1"); shift ;;
        esac
    done

    case "$target" in
        app) patch_all_app "${pass_args[@]}" ;;
        ide) patch_all_ide "${pass_args[@]}" ;;
        all|*)
            patch_all_app "${pass_args[@]}"
            patch_all_ide "${pass_args[@]}"
            ;;
    esac
}
