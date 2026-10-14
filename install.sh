#!/usr/bin/env bash
# ==============================================================================
# Antigravity Suite Manager - Step-by-Step Automated Installer & Wizard
# Supports starting from any step, custom installation paths, and target switching.
# ==============================================================================
set -eo pipefail

GREEN="\033[1;32m"
BLUE="\033[1;38;5;75m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
CYAN="\033[1;36m"
NC="\033[0m"
BOLD="\033[1m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_BIN="${HOME}/.local/bin"
TARGET_ICONS="${HOME}/.local/share/icons"
TARGET_CONF="${HOME}/.config/antigravity"
PATHS_CONF="${TARGET_CONF}/paths.conf"
ICONS_CONF="${TARGET_CONF}/icons.conf"
KEYRING_CONF="${TARGET_CONF}/keyring.conf"

START_STEP=1
ONLY_STEP=0
STEP_BY_STEP=false
NON_INTERACTIVE=false
INSTALL_ANTIGRAVITY=false
CLI_APP_DIR=""
CLI_IDE_DIR=""

# Load existing paths if available
if [ -f "$PATHS_CONF" ]; then
    # shellcheck source=/dev/null
    source "$PATHS_CONF"
fi
APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/antigravity2}"
IDE_INSTALL_DIR="${IDE_INSTALL_DIR:-/opt/antigravity}"

# Parse CLI options
while [ $# -gt 0 ]; do
    case "$1" in
        --step|-s)
            START_STEP="$2"
            shift 2
            ;;
        --only-step|-o)
            ONLY_STEP="$2"
            shift 2
            ;;
        --wizard|-w)
            STEP_BY_STEP=true
            shift
            ;;
        --app-dir)
            CLI_APP_DIR="$2"
            shift 2
            ;;
        --ide-dir)
            CLI_IDE_DIR="$2"
            shift 2
            ;;
        --install-antigravity|-i)
            INSTALL_ANTIGRAVITY=true
            shift
            ;;
        -y|--yes)
            NON_INTERACTIVE=true
            shift
            ;;
        -h|--help)
            echo "Antigravity Suite Manager Installer & Step-by-Step Setup Wizard"
            echo ""
            echo "Usage: ./install.sh [options]"
            echo ""
            echo "Options:"
            echo "  -s, --step <N>        Start execution from step N (1-8)"
            echo "  -o, --only-step <N>   Execute only step N and exit (1-8)"
            echo "  -w, --wizard          Enable interactive step-by-step wizard (prompts after each step)"
            echo "  --app-dir <path>      Specify custom Antigravity App install directory"
            echo "  --ide-dir <path>      Specify custom Antigravity IDE install directory"
            echo "  -i, --install-antigravity  Force downloading and installing Antigravity binaries"
            echo "  -y, --yes             Run non-interactively with defaults"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Steps:"
            echo "  1) Check System & Dependencies"
            echo "  2) Configure / Change Installation Paths (App & IDE)"
            echo "  3) Prepare Directories & Compile Catmull-Rom Bicubic Resampler (C)"
            echo "  4) Install Management Tools & Master Icon Assets"
            echo "  5) Configure Visual Icon Themes & Recolor"
            echo "  6) Configure Credential Keyring Mode (Normal vs GNOME)"
            echo "  7) Download & Install Google Antigravity Binaries"
            echo "  8) Setup Multi-Account Launchers & Unified Chat History Sync"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# If CLI paths were provided, persist them
if [ -n "$CLI_APP_DIR" ] || [ -n "$CLI_IDE_DIR" ]; then
    mkdir -p "$TARGET_CONF"
    APP_INSTALL_DIR="${CLI_APP_DIR:-$APP_INSTALL_DIR}"
    IDE_INSTALL_DIR="${CLI_IDE_DIR:-$IDE_INSTALL_DIR}"
    cat <<EOF > "$PATHS_CONF"
# Antigravity Suite Installation Paths Configuration
APP_INSTALL_DIR="${APP_INSTALL_DIR}"
IDE_INSTALL_DIR="${IDE_INSTALL_DIR}"
EOF
fi

# Interactive mode step selection if no flags were given
if [ "$NON_INTERACTIVE" != true ] && [ -t 0 ] && [ "$START_STEP" -eq 1 ] && [ "$ONLY_STEP" -eq 0 ] && [ "$STEP_BY_STEP" != true ]; then
    echo -e "${CYAN}======================================================================${NC}"
    echo -e "${BOLD}${CYAN}            Antigravity Suite Manager - Step-by-Step Setup           ${NC}"
    echo -e "${CYAN}======================================================================${NC}"
    echo -e "Current Configured Paths:"
    echo -e "  • Antigravity App: ${GREEN}${APP_INSTALL_DIR}${NC}"
    echo -e "  • Antigravity IDE: ${GREEN}${IDE_INSTALL_DIR}${NC}"
    echo -e "----------------------------------------------------------------------"
    echo -e "Available Setup Steps:"
    echo -e "  [1] Check Dependencies & Prerequisites"
    echo -e "  [2] Configure / Change Installation Paths (App & IDE)"
    echo -e "  [3] Prepare Directories & Compile Bicubic Resampler (C)"
    echo -e "  [4] Deploy Management Tools & Master Icon Assets"
    echo -e "  [5] Configure Visual Icon Themes & Recolor"
    echo -e "  [6] Configure Credential Keyring Mode (Normal vs GNOME)"
    echo -e "  [7] Download & Install Google Antigravity Binaries"
    echo -e "  [8] Setup Multi-Account Launchers & 3-Way Chat Sync"
    echo -e "----------------------------------------------------------------------"
    echo -e "Options:"
    echo -e "  • [A] All Steps (Start from Step 1 sequentially) [Default]"
    echo -e "  • [W] Guided Step-by-Step Wizard (Prompt & confirm after each step)"
    echo -e "  • [1-8] Start from step N and proceed (e.g. '2' to configure paths)"
    echo -e "  • [O <N>] Run ONLY step N (e.g. 'O 2' to only change paths and exit)"
    echo -e "  • [Q] Quit"
    echo -e "----------------------------------------------------------------------"
    read -rp "Select an option [A / W / 1-8 / O <N> / Q, Default: A]: " mode_choice
    mode_choice="${mode_choice:-A}"

    case "$mode_choice" in
        [Qq]*)
            echo "Exiting setup."
            exit 0
            ;;
        [Ww]*)
            STEP_BY_STEP=true
            START_STEP=1
            ;;
        [Oo]*|[Oo]\ *)
            num=$(echo "$mode_choice" | awk '{print $2}')
            if [ -n "$num" ] && [ "$num" -ge 1 ] && [ "$num" -le 8 ] 2>/dev/null; then
                ONLY_STEP="$num"
            else
                read -rp "Enter step number to run [1-8]: " num
                ONLY_STEP="${num:-1}"
            fi
            ;;
        [1-8])
            START_STEP="$mode_choice"
            ;;
        *)
            START_STEP=1
            ;;
    esac
fi

# ==============================================================================
# Step 1: Check Platform & Prerequisites
# ==============================================================================
step_1_prerequisites() {
    echo -e "\n${BLUE}[Step 1/8] Checking build and runtime dependencies...${NC}"
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ "$ID" != "ubuntu" ]; then
            echo -e "${YELLOW}[WARNING] This suite is designed exclusively for Ubuntu Linux. Detected: ${NAME:-Unknown}${NC}"
        elif [ "$VERSION_ID" != "24.04" ]; then
            echo -e "${YELLOW}[WARNING] This suite is strictly tested on Ubuntu 24.04 LTS. Detected version: ${VERSION_ID}${NC}"
        fi
    fi

    local MISSING=()
    for cmd in python3 gcc tar curl; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            MISSING+=("$cmd")
        fi
    done

    if [ ${#MISSING[@]} -gt 0 ]; then
        echo -e "${RED}[ERROR] Missing required packages: ${MISSING[*]}${NC}"
        echo -e "${YELLOW}Please install them first (e.g. sudo apt install ${MISSING[*]})${NC}"
        return 1
    fi
    echo -e "${GREEN}[OK] Core dependencies verified.${NC}"
}

# ==============================================================================
# Step 2: Configure / Change Installation Paths & Targets
# ==============================================================================
step_2_configure_paths() {
    echo -e "\n${BLUE}[Step 2/8] Detecting installations & configuring target paths...${NC}"
    local DETECT_SCRIPT="${SCRIPT_DIR}/bin/antigravity-detect.py"
    if [ ! -f "$DETECT_SCRIPT" ]; then
        DETECT_SCRIPT="${TARGET_BIN}/antigravity-detect.py"
    fi

    if [ -n "$CLI_APP_DIR" ] || [ -n "$CLI_IDE_DIR" ]; then
        python3 "$DETECT_SCRIPT" --set-app-dir "${CLI_APP_DIR:-$APP_INSTALL_DIR}" --set-ide-dir "${CLI_IDE_DIR:-$IDE_INSTALL_DIR}"
    elif [ "$NON_INTERACTIVE" = true ]; then
        python3 "$DETECT_SCRIPT" --set-defaults-if-missing
    else
        python3 "$DETECT_SCRIPT" --configure-paths
    fi

    if [ -f "$PATHS_CONF" ]; then
        source "$PATHS_CONF"
    fi
    echo -e "${GREEN}[OK] Configured App: ${APP_INSTALL_DIR:-/opt/antigravity2} | IDE: ${IDE_INSTALL_DIR:-/opt/antigravity}${NC}"
}

# ==============================================================================
# Step 3: Prepare Directories & Compile C Bicubic Resampler
# ==============================================================================
step_3_compile_resampler() {
    echo -e "\n${BLUE}[Step 3/8] Preparing directories & compiling C bicubic image resampler...${NC}"
    mkdir -p "$TARGET_BIN" "$TARGET_ICONS" "$TARGET_CONF" "/tmp/antigravity-cache"
    if [ -f "${SCRIPT_DIR}/src/scale_icon.c" ]; then
        gcc -O3 -Wall "${SCRIPT_DIR}/src/scale_icon.c" -lm -o "${TARGET_BIN}/scale_icon"
        chmod +x "${TARGET_BIN}/scale_icon"
        echo -e "${GREEN}[OK] Resampler compiled to ${TARGET_BIN}/scale_icon${NC}"
    elif [ -f "${TARGET_BIN}/scale_icon" ]; then
        echo -e "${GREEN}[OK] Existing resampler found at ${TARGET_BIN}/scale_icon${NC}"
    else
        echo -e "${YELLOW}[WARN] src/scale_icon.c not found, skipping compilation.${NC}"
    fi
}

# ==============================================================================
# Step 4: Install Scripts, Master Icons & Symlink
# ==============================================================================
step_4_deploy_scripts() {
    echo -e "\n${BLUE}[Step 4/8] Installing management scripts & master icon assets...${NC}"
    mkdir -p "$TARGET_BIN" "$TARGET_ICONS" "$TARGET_CONF"
    for s in manage-antigravity.sh antigravity-generate-icons.py antigravity-apply-icon.py antigravity-merge-history.py antigravity-detect.py antigravity-keyring.py; do
        if [ -f "${SCRIPT_DIR}/bin/${s}" ]; then
            cp -f "${SCRIPT_DIR}/bin/${s}" "${TARGET_BIN}/"
            chmod +x "${TARGET_BIN}/${s}"
        fi
    done

    if [ -d "${SCRIPT_DIR}/assets" ]; then
        cp -f "${SCRIPT_DIR}/assets"/antigravity-master-*.png "${TARGET_ICONS}/" 2>/dev/null || true
    fi

    ln -sfn "${TARGET_BIN}/manage-antigravity.sh" "${HOME}/manage-antigravity.sh"
    echo -e "${GREEN}[OK] Installed management tools to ${TARGET_BIN} and symlinked ~/manage-antigravity.sh${NC}"
}

# ==============================================================================
# Step 5: Configure Visual Icon Themes & Recolor
# ==============================================================================
step_5_configure_icons() {
    echo -e "\n${BLUE}[Step 5/8] Configuring icon themes & initializing icon cache...${NC}"
    if [ ! -f "${TARGET_CONF}/icons.conf" ]; then
        cat <<EOF > "${TARGET_CONF}/icons.conf"
# Antigravity Suite Icon Configuration
ACC1_ICON_THEME="black"
ACC2_ICON_THEME="black"
ACC2_RECOLOR="true"
IDE_ICON_THEME="white"
EOF
    fi

    if [ "$NON_INTERACTIVE" != true ] && [ -t 0 ] && [ "$STEP_BY_STEP" = true ]; then
        read -rp "Would you like to customize Icon Themes now? [y/N] " ico_ans
        if [[ "$ico_ans" =~ ^[Yy]$ ]]; then
            "${TARGET_BIN}/manage-antigravity.sh" set-icons
        fi
    fi

    python3 "${TARGET_BIN}/antigravity-generate-icons.py" >/dev/null 2>&1 || true
    echo -e "${GREEN}[OK] Icon cache generated.${NC}"
}

# ==============================================================================
# Step 6: Configure Keyring / Credential Storage Mode
# ==============================================================================
step_6_configure_keyring() {
    echo -e "\n${BLUE}[Step 6/8] Configuring credential storage / keyring mode...${NC}"
    if [ ! -f "${TARGET_CONF}/keyring.conf" ]; then
        cat <<EOF > "${TARGET_CONF}/keyring.conf"
# Antigravity Keyring Storage Configuration
# Values: 'normal' (Basic file storage, no GNOME Keyring) or 'gnome' (GNOME Keyring)
KEYRING_MODE_APP1="normal"
KEYRING_MODE_APP2="normal"
KEYRING_MODE_IDE="normal"
EOF
    fi

    if [ "$NON_INTERACTIVE" != true ] && [ -t 0 ] && [ "$STEP_BY_STEP" = true ]; then
        echo -e "Storage options:"
        echo -e "  [1] Normal File Storage (Bypasses GNOME Keyring - Recommended)"
        echo -e "  [2] GNOME Keyring (Secret Service)"
        read -rp "Select credential storage mode [Default: 1]: " k_ans
        k_ans="${k_ans:-1}"
        if [ "$k_ans" = "2" ]; then
            python3 "${TARGET_BIN}/antigravity-keyring.py" set all gnome >/dev/null 2>&1 || true
            echo -e "${GREEN}[OK] Set storage mode to GNOME Keyring.${NC}"
        else
            python3 "${TARGET_BIN}/antigravity-keyring.py" set all normal >/dev/null 2>&1 || true
            echo -e "${GREEN}[OK] Set storage mode to Normal File Storage.${NC}"
        fi
    else
        source "${TARGET_CONF}/keyring.conf" 2>/dev/null || true
        python3 "${TARGET_BIN}/antigravity-keyring.py" set all "${KEYRING_MODE_APP1:-normal}" >/dev/null 2>&1 || true
        echo -e "${GREEN}[OK] Credential storage configured (${KEYRING_MODE_APP1:-normal}).${NC}"
    fi
}

# ==============================================================================
# Step 7: Download & Install Google Antigravity Binaries
# ==============================================================================
step_7_install_antigravity() {
    echo -e "\n${BLUE}[Step 7/8] Installing / Updating Google Antigravity Binaries...${NC}"
    if [ -f "$PATHS_CONF" ]; then
        source "$PATHS_CONF"
    fi

    local app_target="${APP_INSTALL_DIR:-/opt/antigravity2}"
    local ide_target="${IDE_INSTALL_DIR:-/opt/antigravity}"

    local app_exists=false
    local ide_exists=false
    if [ -f "${app_target}/resources/app.asar" ]; then app_exists=true; fi
    if [ -f "${ide_target}/resources/app/product.json" ] || [ -f "${ide_target}/resources/app/package.json" ]; then ide_exists=true; fi

    local do_install=false
    if [ "$INSTALL_ANTIGRAVITY" = true ]; then
        do_install=true
    elif [ "$app_exists" = false ] || [ "$ide_exists" = false ]; then
        if [ "$NON_INTERACTIVE" = true ]; then
            do_install=true
        elif [ -t 0 ]; then
            echo -e "${YELLOW}Antigravity binaries not fully installed in target directories:${NC}"
            echo -e "  • App (${app_target}): $([ "$app_exists" = true ] && echo -e "${GREEN}Present${NC}" || echo -e "${RED}Missing${NC}")"
            echo -e "  • IDE (${ide_target}): $([ "$ide_exists" = true ] && echo -e "${GREEN}Present${NC}" || echo -e "${RED}Missing${NC}")"
            read -rp "Would you like to download and install Google Antigravity now? [Y/n] " inst_ans
            inst_ans="${inst_ans:-Y}"
            if [[ "$inst_ans" =~ ^[Yy]$ ]]; then
                do_install=true
            fi
        fi
    else
        echo -e "${GREEN}[OK] Antigravity App already present in ${app_target}${NC}"
        echo -e "${GREEN}[OK] Antigravity IDE already present in ${ide_target}${NC}"
        if [ "$NON_INTERACTIVE" != true ] && [ -t 0 ] && [ "$STEP_BY_STEP" = true ]; then
            read -rp "Reinstall/Update binaries from upstream now? [y/N] " re_ans
            if [[ "$re_ans" =~ ^[Yy]$ ]]; then
                do_install=true
            fi
        fi
    fi

    if [ "$do_install" = true ]; then
        echo -e "${GREEN}Installing Google Antigravity Suite into configured paths...${NC}"
        "${TARGET_BIN}/manage-antigravity.sh" install all --app-dir "$app_target" --ide-dir "$ide_target"
    fi
}

# ==============================================================================
# Step 8: Multi-Account Launchers, Unified Chat Sync & Status Check
# ==============================================================================
step_8_setup_launchers_and_sync() {
    echo -e "\n${BLUE}[Step 8/8] Setting up multi-account launchers, desktop entries & unified chat sync...${NC}"
    if [ -f "$PATHS_CONF" ]; then
        source "$PATHS_CONF"
    fi

    "${TARGET_BIN}/manage-antigravity.sh" app1 >/dev/null 2>&1 || true
    "${TARGET_BIN}/manage-antigravity.sh" app2 >/dev/null 2>&1 || true
    "${TARGET_BIN}/manage-antigravity.sh" ide-shortcuts >/dev/null 2>&1 || true
    "${TARGET_BIN}/manage-antigravity.sh" merge-history >/dev/null 2>&1 || true

    echo -e "${GREEN}[OK] Launchers configured: antigravity-1, antigravity-acc2, antigravity-ide.${NC}"
    echo -e "${GREEN}[OK] 3-Way Unified Chat History synchronized.${NC}"

    echo -e "\n${CYAN}======================================================================${NC}"
    echo -e "${GREEN}${BOLD}Verification & System Status:${NC}"
    "${TARGET_BIN}/manage-antigravity.sh" status
    echo -e "${CYAN}======================================================================${NC}"
    echo -e "${GREEN}${BOLD}Setup Complete!${NC}"
    echo -e "You can manage your suite anytime using:"
    echo -e "  ${BOLD}~/manage-antigravity.sh [status | paths | keyring | update | set-icons | help]${NC}"
    echo -e "${CYAN}======================================================================${NC}"
}

# ==============================================================================
# Step Runner Engine
# ==============================================================================
run_step() {
    local s="$1"
    case "$s" in
        1) step_1_prerequisites ;;
        2) step_2_configure_paths ;;
        3) step_3_compile_resampler ;;
        4) step_4_deploy_scripts ;;
        5) step_5_configure_icons ;;
        6) step_6_configure_keyring ;;
        7) step_7_install_antigravity ;;
        8) step_8_setup_launchers_and_sync ;;
        *) return 0 ;;
    esac
}

# Single Step Execution
if [ "$ONLY_STEP" -ge 1 ] && [ "$ONLY_STEP" -le 8 ]; then
    echo -e "${CYAN}Executing ONLY Step ${ONLY_STEP}...${NC}"
    run_step "$ONLY_STEP"
    echo -e "${GREEN}[SUCCESS] Step ${ONLY_STEP} execution complete.${NC}"
    exit 0
fi

# Sequential / Guided Step Runner
curr="$START_STEP"
while [ "$curr" -le 8 ]; do
    run_step "$curr"
    if [ "$STEP_BY_STEP" = true ] && [ "$curr" -lt 8 ] && [ "$NON_INTERACTIVE" != true ] && [ -t 0 ]; then
        echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
        read -rp "Step ${curr} completed. [Enter] Next Step $((curr + 1)) | [s]kip next | [j <1-8>] jump | [q]uit: " next_action
        case "$next_action" in
            [Qq]*)
                echo "Exiting setup wizard."
                exit 0
                ;;
            [Ss]*)
                curr=$((curr + 1))
                ;;
            [Jj]*)
                target_j=$(echo "$next_action" | awk '{print $2}')
                if [ -n "$target_j" ] && [ "$target_j" -ge 1 ] && [ "$target_j" -le 8 ] 2>/dev/null; then
                    curr="$target_j"
                    continue
                fi
                ;;
        esac
    fi
    curr=$((curr + 1))
done
