#!/usr/bin/env bash
# CLI flag options and patch argument parser helpers

shift_sub_arg() {
    if [ -n "$1" ] && [[ "$1" != -* ]]; then
        SUB_COMMAND="$1"
        return 2
    fi
    return 1
}

parse_patch_arg() {
    case "$1" in
        rtl|patch-rtl) COMMAND="rtl"; shift_sub_arg "$2"; return $? ;;
        unpatch-rtl) COMMAND="unpatch-rtl"; shift_sub_arg "$2"; return $? ;;
        f5|patch-f5) COMMAND="f5"; shift_sub_arg "$2"; return $? ;;
        unpatch-f5) COMMAND="unpatch-f5"; shift_sub_arg "$2"; return $? ;;
        selector|patch-selector|patch-accounts) COMMAND="patch-selector"; shift_sub_arg "$2"; return $? ;;
        unpatch-selector|unpatch-accounts) COMMAND="unpatch-selector"; shift_sub_arg "$2"; return $? ;;
        fork|patch-fork) COMMAND="fork"; shift_sub_arg "$2"; return $? ;;
        unpatch-fork) COMMAND="unpatch-fork"; shift_sub_arg "$2"; return $? ;;
        open-ide|patch-open-ide) COMMAND="open-ide"; shift_sub_arg "$2"; return $? ;;
        unpatch-open-ide) COMMAND="unpatch-open-ide"; shift_sub_arg "$2"; return $? ;;
        *) return 0 ;;
    esac
}

parse_config_flag() {
    case "$1" in
        --step|-s) COMMAND="wizard_step"; START_STEP="$2"; return 2 ;;
        --only-step|-o) COMMAND="only_step"; ONLY_STEP="$2"; return 2 ;;
        --wizard|-w) COMMAND="wizard"; return 1 ;;
        --install-antigravity|-i) COMMAND="install"; SUB_COMMAND="all"; return 1 ;;
        -y|--yes) NON_INTERACTIVE=true; return 1 ;;
        -u) COMMAND="update"; SUB_COMMAND="all"; return 1 ;;
        --menu|--center|--control-center) COMMAND="center"; return 1 ;;
        --classic-menu) COMMAND="classic-menu"; return 1 ;;
        --app-url) APP_URL="$2"; return 2 ;;
        --ide-url) IDE_URL="$2"; return 2 ;;
        --app-dir) APP_INSTALL_DIR="$2"; CLI_APP_DIR_SPECIFIED=true; return 2 ;;
        --ide-dir) IDE_INSTALL_DIR="$2"; CLI_IDE_DIR_SPECIFIED=true; return 2 ;;
        --cache-dir) CACHE_DIR="$2"; return 2 ;;
        --acc1-icon) ACC1_ICON_THEME="$2"; CLI_ICON_GIVEN=true; return 2 ;;
        --acc2-icon) ACC2_ICON_THEME="$2"; CLI_ICON_GIVEN=true; return 2 ;;
        --acc2-recolor) ACC2_RECOLOR="$2"; CLI_ICON_GIVEN=true; return 2 ;;
        --ide-icon) IDE_ICON_THEME="$2"; CLI_ICON_GIVEN=true; return 2 ;;
        --force|-f) FORCE_INSTALL=true; return 1 ;;
        --no-cache) USE_CACHE=false; return 1 ;;
        --skip-rtl) SKIP_RTL=true; return 1 ;;
        --skip-f5) SKIP_F5=true; return 1 ;;
        *) return 0 ;;
    esac
}
