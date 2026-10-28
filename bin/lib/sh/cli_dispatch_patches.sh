#!/usr/bin/env bash
# Helper dispatchers for patch management commands

dispatch_rtl() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app) patch_rtl_app; patch_f5_reload ;;
        ide) patch_rtl_ide ;;
        all|*) patch_rtl_all ;;
    esac
}

dispatch_unpatch_rtl() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app) unpatch_rtl_app "$@" ;;
        ide) unpatch_rtl_ide "$@" ;;
        all|*) unpatch_rtl_all "$@" ;;
    esac
}

dispatch_selector() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app) patch_selector_app "$@" ;;
        ide) patch_selector_ide "$@" ;;
        all|*) patch_selector "$@" ;;
    esac
}

dispatch_unpatch_selector() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app) unpatch_selector_app "$@" ;;
        ide) unpatch_selector_ide "$@" ;;
        all|*) unpatch_selector "$@" ;;
    esac
}

dispatch_f5() {
    auto_detect_installations
    FORCE_INSTALL=true patch_f5_reload "$@"
}

dispatch_unpatch_f5() {
    auto_detect_installations
    unpatch_f5 "$@"
}

dispatch_fork() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app) patch_fork_app "$@" ;;
        ide) patch_fork_ide "$@" ;;
        all|*) patch_fork_all "$@" ;;
    esac
}

dispatch_unpatch_fork() {
    auto_detect_installations
    case "${SUB_COMMAND:-all}" in
        app) unpatch_fork_app "$@" ;;
        ide) unpatch_fork_ide "$@" ;;
        all|*) unpatch_fork_all "$@" ;;
    esac
}

dispatch_open_ide() {
    auto_detect_installations
    patch_open_ide_app "$@"
}

dispatch_unpatch_open_ide() {
    auto_detect_installations
    unpatch_open_ide_app "$@"
}

dispatch_patch_models() {
    auto_detect_installations
    patch_models_app "$@"
}

dispatch_unpatch_models() {
    auto_detect_installations
    unpatch_models_app "$@"
}
