#!/usr/bin/env bash
# Helper dispatchers for patch management commands

dispatch_rtl() {
    auto_detect_installations
    local target="${1:-${SUB_COMMAND:-all}}"
    [ $# -gt 0 ] && shift
    case "$target" in
        app) patch_rtl_app "$@" ;;
        ide) patch_rtl_ide "$@" ;;
        all|*) patch_rtl_all "$@" ;;
    esac
}

dispatch_unpatch_rtl() {
    auto_detect_installations
    local target="${1:-${SUB_COMMAND:-all}}"
    [ $# -gt 0 ] && shift
    case "$target" in
        app) unpatch_rtl_app "$@" ;;
        ide) unpatch_rtl_ide "$@" ;;
        all|*) unpatch_rtl_all "$@" ;;
    esac
}

dispatch_selector() {
    auto_detect_installations
    local target="${1:-${SUB_COMMAND:-all}}"
    [ $# -gt 0 ] && shift
    case "$target" in
        app) patch_selector_app "$@" ;;
        ide) patch_selector_ide "$@" ;;
        all|*) patch_selector "$@" ;;
    esac
}

dispatch_unpatch_selector() {
    auto_detect_installations
    local target="${1:-${SUB_COMMAND:-all}}"
    [ $# -gt 0 ] && shift
    case "$target" in
        app) unpatch_selector_app "$@" ;;
        ide) unpatch_selector_ide "$@" ;;
        all|*) unpatch_selector "$@" ;;
    esac
}

dispatch_experiments() {
    auto_detect_installations
    local target="${1:-${SUB_COMMAND:-all}}"
    [ $# -gt 0 ] && shift
    case "$target" in
        app) patch_experiments_app "$@" ;;
        ide) patch_experiments_ide "$@" ;;
        all|*) patch_experiments_all "$@" ;;
    esac
}

dispatch_unpatch_experiments() {
    auto_detect_installations
    local target="${1:-${SUB_COMMAND:-all}}"
    [ $# -gt 0 ] && shift
    case "$target" in
        app) unpatch_experiments_app "$@" ;;
        ide) unpatch_experiments_ide "$@" ;;
        all|*) unpatch_experiments_all "$@" ;;
    esac
}

dispatch_fork() { dispatch_experiments "$@"; }
dispatch_unpatch_fork() { dispatch_unpatch_experiments "$@"; }
dispatch_open_ide() { auto_detect_installations; patch_experiments_app "$@"; }
dispatch_unpatch_open_ide() { auto_detect_installations; unpatch_experiments_app "$@"; }

dispatch_window_bounds() {
    auto_detect_installations
    patch_window_bounds_app "$@"
}

dispatch_unpatch_window_bounds() {
    auto_detect_installations
    unpatch_window_bounds_app "$@"
}

dispatch_patch_models() {
    auto_detect_installations
    local target="${1:-${SUB_COMMAND:-all}}"
    [ $# -gt 0 ] && shift
    case "$target" in
        app) patch_models_app "$@" ;;
        ide) patch_models_ide "$@" ;;
        all|*) patch_models_all "$@" ;;
    esac
}

dispatch_unpatch_models() {
    auto_detect_installations
    local target="${1:-${SUB_COMMAND:-all}}"
    [ $# -gt 0 ] && shift
    case "$target" in
        app) unpatch_models_app "$@" ;;
        ide) unpatch_models_ide "$@" ;;
        all|*) unpatch_models_all "$@" ;;
    esac
}

dispatch_patch_all() {
    auto_detect_installations
    local target="${1:-${SUB_COMMAND:-all}}"
    [ $# -gt 0 ] && shift
    patch_all "$target" "$@"
}

