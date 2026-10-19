#!/usr/bin/env bash
# Installer CLI options parsing and help documentation

show_installer_help() {
    cat <<EOF
Antigravity Suite Manager Installer & Step-by-Step Setup Wizard

Usage: ./install.sh [options]

Options:
  -s, --step <N|name>       Start execution from step N (1-8 or alias e.g. paths, icons)
  -o, --only-step <N|name>  Execute only step N and exit (1-8 or alias e.g. paths, icons)
  -w, --wizard              Enable interactive step-by-step wizard (prompts after each step)
  --app-dir <path>          Specify custom Antigravity App install directory
  --ide-dir <path>          Specify custom Antigravity IDE install directory
  -u, --update              Perform smart update of installed binaries & patches
  --update-repo             Update Suite Manager repository (git pull, build & deploy)
  --restart-services        Restart background systemd sync and X11 icon daemons
  -i, --install-antigravity Force downloading and installing Antigravity binaries
  -y, --yes                 Run non-interactively with defaults
  -h, --help                Show this help message

Steps:
  1) Check System & Dependencies (aliases: prereqs, dep)
  2) Configure Installation Paths & Engines (aliases: paths, engines, detect)
  3) Prepare Directories & Compile Catmull-Rom Bicubic Resampler (aliases: resampler, scale)
  4) Install Management Tools & Master Icon Assets (aliases: deploy, tools, bin)
  5) Configure Visual Icon Themes & Recolor (aliases: icons, themes, recolor)
  6) Configure Credential Keyring Mode (aliases: keyring, creds)
  7) Download & Install Google Antigravity Binaries (aliases: install, download, binary)
  8) Setup Multi-Account Launchers & Unified Chat History Sync (aliases: sync, launchers, chat)
EOF
    exit 0
}

parse_installer_cli() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --step|-s) START_STEP="$(get_step_num "$2")"; shift 2 ;;
            --only-step|-o) ONLY_STEP="$(get_step_num "$2")"; shift 2 ;;
            --wizard|-w) STEP_BY_STEP=true; shift ;;
            --update|-u) RUN_UPDATE=true; shift ;;
            --update-repo|--self-update) RUN_UPDATE_REPO=true; shift ;;
            --restart-services) RUN_RESTART_SERVICES=true; shift ;;
            --app-dir) CLI_APP_DIR="$2"; shift 2 ;;
            --ide-dir) CLI_IDE_DIR="$2"; shift 2 ;;
            --install-antigravity|-i) INSTALL_ANTIGRAVITY=true; shift ;;
            -y|--yes) NON_INTERACTIVE=true; shift ;;
            -h|--help) show_installer_help ;;
            *) shift ;;
        esac
    done

    if [ -n "$CLI_APP_DIR" ] || [ -n "$CLI_IDE_DIR" ]; then
        mkdir -p "$TARGET_CONF"
        APP_INSTALL_DIR="${CLI_APP_DIR:-$APP_INSTALL_DIR}"
        IDE_INSTALL_DIR="${CLI_IDE_DIR:-$IDE_INSTALL_DIR}"
        local local_custom="${CUSTOM_ANTIGRAVITY_PATHS:-}"
        if [ -f "$PATHS_CONF" ] && [ -z "$local_custom" ]; then
            local_custom=$(grep -E '^(CUSTOM_ANTIGRAVITY_PATHS|CUSTOM_PATHS)=' "$PATHS_CONF" | head -n 1 | cut -d'=' -f2- | tr -d '"' | tr -d "'")
        fi
        cat <<EOF > "$PATHS_CONF"
# Antigravity Suite Installation Paths Configuration
APP_INSTALL_DIR="${APP_INSTALL_DIR}"
IDE_INSTALL_DIR="${IDE_INSTALL_DIR}"
EOF
        if [ -n "$local_custom" ]; then
            echo "CUSTOM_ANTIGRAVITY_PATHS=\"${local_custom}\"" >> "$PATHS_CONF"
        fi
    fi
}
