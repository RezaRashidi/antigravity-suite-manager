#!/usr/bin/env bash
# ==============================================================================
# Antigravity & Antigravity IDE All-in-One Manager
# Supports:
#   - Dynamic Version & URL Discovery from Google Releases API
#   - Smart Version-Guard Pre-check (Skips redundant downloads if up-to-date)
#   - Persistent Archive Caching in /tmp/antigravity-cache (Zero repeat downloads)
#   - Two Isolated Antigravity App Profiles (Account 1 & Account 2)
#   - Single-Instance Raising & Focus for Account 2 Launcher (--restart support)
#   - Antigravity IDE (VS Code Edition) Setup & Shortcuts
#   - Automated F5 Backend Reload & Keybinding Patch
#   - Automated RTL Integration (mmnaderi/antigravity-rtl)
# ==============================================================================

set -eo pipefail

# ------------------------------------------------------------------------------
# Configurable Defaults & Paths
# ------------------------------------------------------------------------------
CACHE_DIR="${ANTIGRAVITY_CACHE_DIR:-/tmp/antigravity-cache}"
APP_INSTALL_DIR="${ANTIGRAVITY_APP_DIR:-/opt/antigravity2}"
IDE_INSTALL_DIR="${ANTIGRAVITY_IDE_DIR:-/opt/antigravity}"

if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    REAL_USER="$(whoami)"
    REAL_HOME="${REAL_HOME:-$HOME}"
fi

PROFILE2_DIR="${REAL_HOME}/.antigravity-profile2"
SHARED_GEMINI_DIR="${REAL_HOME}/.gemini"
SHARED_CONV_DIR="${SHARED_GEMINI_DIR}/antigravity"
SHARED_CONFIG_DIR="${SHARED_CONFIG_DIR:-${SHARED_GEMINI_DIR}/config}"

LOCAL_BIN="${REAL_HOME}/.local/bin"
LOCAL_APPS="${REAL_HOME}/.local/share/applications"
LOCAL_ICONS="${REAL_HOME}/.local/share/icons"

# Icon Configuration Defaults & Persistence
ICONS_CONF_DIR="${REAL_HOME}/.config/antigravity"
ICONS_CONF="${ICONS_CONF_DIR}/icons.conf"
ACC1_ICON_THEME="black"
ACC2_ICON_THEME="black"
ACC2_RECOLOR="true"
IDE_ICON_THEME="white"
CLI_ICON_GIVEN=false

if [ -f "$ICONS_CONF" ]; then
    # shellcheck source=/dev/null
    source "$ICONS_CONF"
fi

# CLI Behavior Flags
FORCE_INSTALL=false
USE_CACHE=true
SKIP_RTL=false
SKIP_F5=false
APP_URL=""
IDE_URL=""
TARGET_APP_VER=""
TARGET_IDE_VER=""

# Terminal Colors
GREEN="\033[1;32m"
BLUE="\033[1;34m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
CYAN="\033[1;36m"
NC="\033[0m"
BOLD="\033[1m"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err() { echo -e "${RED}[ERROR]${NC} $1"; }

mkdir -p "$LOCAL_BIN" "$LOCAL_APPS" "$LOCAL_ICONS" "$SHARED_CONV_DIR" "$SHARED_CONFIG_DIR" "$CACHE_DIR"

# ------------------------------------------------------------------------------
# 1. Dynamic Version & Release URL Discovery
# ------------------------------------------------------------------------------
resolve_dynamic_urls() {
    log_info "Discovering latest release versions from Google Antigravity endpoints..."
    
    local py_resolver
    py_resolver=$(python3 - << 'PYEOF'
import urllib.request, json, re, gzip

def get_app():
    try:
        req = urllib.request.Request(
            "https://antigravity-hub-auto-updater-974169037036.us-central1.run.app/releases",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list) and len(data) > 0:
                first = data[0]
                ver = first.get("version")
                exec_id = first.get("execution_id")
                return ver, f"https://storage.googleapis.com/antigravity-public/antigravity-hub/{ver}-{exec_id}/linux-x64/Antigravity.tar.gz"
    except Exception:
        pass
    return "2.23.1", "https://storage.googleapis.com/antigravity-public/antigravity-hub/2.23.1-6348059836284928/linux-x64/Antigravity.tar.gz"

def get_ide():
    try:
        req = urllib.request.Request(
            "https://antigravity.google/download",
            headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            html = gzip.decompress(raw).decode("utf-8", errors="ignore") if resp.info().get("Content-Encoding") == "gzip" else raw.decode("utf-8", errors="ignore")
            m = re.search(r'(https://edgedl\.me\.gvt1\.com/edgedl/release2/[^"\'\s]+/stable/([0-9]+\.[0-9]+\.[0-9]+[^/]*)/linux-x64/Antigravity%20IDE\.tar\.gz)', html)
            if m:
                return m.group(2).split('-')[0], m.group(1)
    except Exception:
        pass
    return "2.5.5", "https://edgedl.me.gvt1.com/edgedl/release2/j0qc3/antigravity/stable/2.5.5-4923483625488384/linux-x64/Antigravity%20IDE.tar.gz"

app_ver, app_url = get_app()
ide_ver, ide_url = get_ide()
print(f"{app_ver}|{app_url}|{ide_ver}|{ide_url}")
PYEOF
)

    IFS='|' read -r disc_app_ver disc_app_url disc_ide_ver disc_ide_url <<< "$py_resolver"

    if [ -z "$APP_URL" ]; then
        APP_URL="$disc_app_url"
        TARGET_APP_VER="$disc_app_ver"
    else
        TARGET_APP_VER=$(echo "$APP_URL" | grep -o -E '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1 || echo "Custom")
    fi

    if [ -z "$IDE_URL" ]; then
        IDE_URL="$disc_ide_url"
        TARGET_IDE_VER="$disc_ide_ver"
    else
        TARGET_IDE_VER=$(echo "$IDE_URL" | grep -o -E '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1 || echo "Custom")
    fi

    log_success "Discovered Latest: App v${TARGET_APP_VER} | IDE v${TARGET_IDE_VER}"
}

# ------------------------------------------------------------------------------
# 2. Status Inspection Table
# ------------------------------------------------------------------------------
check_status() {
    if [ -z "$TARGET_APP_VER" ] || [ -z "$TARGET_IDE_VER" ]; then
        resolve_dynamic_urls >/dev/null 2>&1 || true
    fi

    python3 - "$APP_INSTALL_DIR" "$IDE_INSTALL_DIR" "$PROFILE2_DIR" "$APP_URL" "$IDE_URL" "$TARGET_APP_VER" "$TARGET_IDE_VER" "$CACHE_DIR" "$REAL_USER" "$ACC1_ICON_THEME" "$ACC2_ICON_THEME" "$ACC2_RECOLOR" "$IDE_ICON_THEME" << 'EOF'
import struct, json, os, re, sys, glob

APP_DIR = sys.argv[1]
IDE_DIR = sys.argv[2]
PROFILE2_DIR = sys.argv[3]
APP_URL = sys.argv[4]
IDE_URL = sys.argv[5]
TARG_APP_VER = sys.argv[6]
TARG_IDE_VER = sys.argv[7]
CACHE_DIR = sys.argv[8]
REAL_USER = sys.argv[9]
ACC1_THEME = sys.argv[10]
ACC2_THEME = sys.argv[11]
ACC2_RECOLOR = sys.argv[12].lower() in ["true", "1", "yes"]
IDE_THEME = sys.argv[13]

G = '\033[1;32m'
Y = '\033[1;33m'
R = '\033[1;31m'
B = '\033[1;34m'
C = '\033[1;36m'
NC = '\033[0m'
BOLD = '\033[1m'

def get_app_version(app_dir):
    asar_path = os.path.join(app_dir, 'resources', 'app.asar')
    if not os.path.isfile(asar_path):
        return None
    try:
        with open(asar_path, 'rb') as f:
            magic, header_size, header_obj_size, json_len = struct.unpack('<IIII', f.read(16))
            header = json.loads(f.read(json_len).decode('utf-8'))
            curr = header.get('files', {}).get('package.json', {})
            if 'offset' in curr and 'size' in curr:
                f.seek(16 + json_len + int(curr['offset']))
                raw = f.read(min(curr['size'] + 50, 1024)).decode('utf-8', errors='ignore')
                m = re.search(r'"version"\s*:\s*"([^"]+)"', raw)
                if m: return m.group(1)
    except Exception:
        pass
    return 'Unknown'

def get_ide_version(ide_dir):
    prod_path = os.path.join(ide_dir, 'resources', 'app', 'product.json')
    if not os.path.isfile(prod_path):
        return None
    try:
        with open(prod_path, 'r', encoding='utf-8') as f:
            prod = json.load(f)
            return prod.get('ideVersion') or prod.get('version') or 'Unknown'
    except Exception:
        pass
    return 'Unknown'

def check_app_rtl(app_dir):
    asar_path = os.path.join(app_dir, 'resources', 'app.asar')
    if not os.path.isfile(asar_path):
        return f"{R}Missing{NC}"
    try:
        with open(asar_path, 'rb') as f:
            while True:
                chunk = f.read(10 * 1024 * 1024)
                if not chunk: break
                if b'/* ANTIGRAVITY RTL PATCH */' in chunk:
                    return f"{G}Applied{NC}"
    except Exception:
        pass
    return f"{Y}Not Applied{NC}"

def check_app_f5(app_dir):
    asar_path = os.path.join(app_dir, 'resources', 'app.asar')
    if not os.path.isfile(asar_path):
        return f"{R}Missing{NC}"
    try:
        with open(asar_path, 'rb') as f:
            while True:
                chunk = f.read(10 * 1024 * 1024)
                if not chunk: break
                if b'restartLanguageServer' in chunk:
                    return f"{G}Applied{NC}"
    except Exception:
        pass
    return f"{Y}Not Applied{NC}"

def check_ide_rtl(ide_dir):
    main_js = os.path.join(ide_dir, 'resources', 'app', 'out', 'main.js')
    if not os.path.isfile(main_js):
        return f"{R}Missing{NC}"
    try:
        with open(main_js, 'r', encoding='utf-8') as f:
            txt = f.read(1024)
            if 'antigravity-rtl-main.js' in txt or os.path.isfile(main_js + '.rtl-bak'):
                return f"{G}Applied{NC}"
    except Exception:
        pass
    return f"{Y}Not Applied{NC}"

def check_account2():
    keyring = os.path.isfile(os.path.join(PROFILE2_DIR, '.gemini', 'cache', 'antigravity-keyring-unavailable'))
    conv = os.path.islink(os.path.join(PROFILE2_DIR, '.gemini', 'antigravity'))
    conf = os.path.exists(os.path.join(PROFILE2_DIR, '.gemini', 'config'))
    if keyring and conv and conf:
        return f"{G}Configured (Isolated Keyring + Shared History){NC}"
    return f"{Y}Incomplete Setup{NC}"

def check_history_sharing():
    real_gemini = os.path.join(os.path.dirname(PROFILE2_DIR), '.gemini')
    ide_conv = os.path.join(real_gemini, 'antigravity-ide', 'conversations')
    p2_conv = os.path.join(PROFILE2_DIR, '.gemini', 'antigravity')
    ide_shared = os.path.islink(ide_conv)
    p2_shared = os.path.islink(p2_conv)
    if ide_shared and p2_shared:
        return f"{G}3-Way Unified (App 1, App 2, IDE){NC}"
    elif p2_shared:
        return f"{Y}2-Way (App 1 & App 2 only){NC}"
    return f"{R}Not Shared{NC}"

def check_write(d):
    if not os.path.isdir(d):
        return f"{R}Directory Missing{NC}"
    res = os.path.join(d, 'resources')
    w_d = os.access(d, os.W_OK)
    w_r = os.access(res, os.W_OK) if os.path.isdir(res) else False
    if w_d and w_r:
        return f"{G}Writable by {REAL_USER} (Ready){NC}"
    return f"{R}Read-Only for {REAL_USER} (Requires fix_permissions){NC}"

def check_cached(name, ver):
    pattern = os.path.join(CACHE_DIR, f"{name}-{ver}.tar.gz")
    if os.path.isfile(pattern) and os.path.getsize(pattern) > 10 * 1024 * 1024:
        size_mb = os.path.getsize(pattern) / (1024 * 1024)
        return f"{G}Cached ({size_mb:.1f} MB){NC}"
    return f"{Y}Not Cached (Download on demand){NC}"

app_ver = get_app_version(APP_DIR)
app_status = f"{G}Up-to-date{NC}" if (app_ver and app_ver == TARG_APP_VER) else (f"{Y}Update Available{NC}" if app_ver else f"{R}Not Installed{NC}")

ide_ver = get_ide_version(IDE_DIR)
ide_status = f"{G}Up-to-date{NC}" if (ide_ver and ide_ver == TARG_IDE_VER) else (f"{Y}Update Available{NC}" if ide_ver else f"{R}Not Installed{NC}")

app_rtl = check_app_rtl(APP_DIR)
app_f5 = check_app_f5(APP_DIR)
ide_rtl = check_ide_rtl(IDE_DIR)
acc2_st = check_account2()

app_cache = check_cached("Antigravity-App", TARG_APP_VER)
ide_cache = check_cached("Antigravity-IDE", TARG_IDE_VER)

print(f"{C}========================================================================================{NC}")
print(f"{BOLD}{C}                    Antigravity Suite Version & Patch Inspection                        {NC}")
print(f"{C}========================================================================================{NC}")
print(f"{BOLD}{B}Target                 Installed    Latest Available  Status          RTL Patch   F5 Patch{NC}")
print(f"----------------------------------------------------------------------------------------")
print(f"Antigravity (Acc 1&2)  {app_ver or 'N/A':<12} {TARG_APP_VER:<17} {app_status:<24} {app_rtl:<20} {app_f5}")
print(f"Antigravity IDE        {ide_ver or 'N/A':<12} {TARG_IDE_VER:<17} {ide_status:<24} {ide_rtl:<20} N/A")
print(f"----------------------------------------------------------------------------------------")
print(f"{BOLD}Package Cache Status in {CACHE_DIR}:{NC}")
print(f"  • Antigravity App:        {app_cache}")
print(f"  • Antigravity IDE:        {ide_cache}")
print(f"----------------------------------------------------------------------------------------")
print(f"{BOLD}Icon & Appearance Themes:{NC}")
print(f"  • Antigravity (Acc 1):    {ACC1_THEME.capitalize()} Icon Theme")
recolor_badge = f"{G}Violet/Magenta Glow (Recolored){NC}" if ACC2_RECOLOR else f"{Y}Original Colors (No Recolor){NC}"
print(f"  • Antigravity (Acc 2):    {ACC2_THEME.capitalize()} Icon Theme | {recolor_badge}")
print(f"  • Antigravity IDE:        {IDE_THEME.capitalize()} Icon Theme")
print(f"----------------------------------------------------------------------------------------")
print(f"{BOLD}Environment & Permissions:{NC}")
print(f"  • Account 2 Status:       {acc2_st}")
print(f"  • History Sharing:        {check_history_sharing()}")
print(f"  • App Dir Ownership:      {check_write(APP_DIR)}")
print(f"  • IDE Dir Ownership:      {check_write(IDE_DIR)}")
print(f"  • Discovered App URL:     {APP_URL}")
print(f"  • Discovered IDE URL:     {IDE_URL}")
print(f"{C}========================================================================================{NC}")
EOF
}

# ------------------------------------------------------------------------------
# 3. Helper: Permissions & Ownership
# ------------------------------------------------------------------------------
fix_permissions() {
    local target_dir="$1"
    if [ ! -d "$target_dir" ]; then
        return
    fi
    log_info "Ensuring permissions and executable flags for ${target_dir}..."

    if [ "$EUID" -eq 0 ]; then
        chown -R "$REAL_USER:$REAL_USER" "$target_dir"
        chmod -R u+rwX "$target_dir"
        if [ -f "$target_dir/chrome-sandbox" ]; then
            chown root:root "$target_dir/chrome-sandbox"
            chmod 4755 "$target_dir/chrome-sandbox"
        fi
    else
        if [ ! -w "$target_dir" ] || ([ -d "$target_dir/resources" ] && [ ! -w "$target_dir/resources" ]); then
            log_warn "${target_dir}/resources requires user write access."
            sudo chown -R "$REAL_USER:$REAL_USER" "$target_dir"
            sudo chmod -R u+rwX "$target_dir"
            if [ -f "$target_dir/chrome-sandbox" ]; then
                sudo chown root:root "$target_dir/chrome-sandbox" 2>/dev/null || true
                sudo chmod 4755 "$target_dir/chrome-sandbox" 2>/dev/null || true
            fi
        fi
    fi

    find "$target_dir" -maxdepth 2 -type f \( -name "antigravity*" -o -name "*.so*" -o -name "chrome_crashpad_handler" \) -exec chmod +x {} + 2>/dev/null || true
}

# ------------------------------------------------------------------------------
# 4. Helper: Package Caching & Retrieval
# ------------------------------------------------------------------------------
get_or_download_package() {
    local name="$1"
    local url="$2"
    local ver="$3"
    local cache_file="${CACHE_DIR}/${name}-${ver}.tar.gz"

    mkdir -p "$CACHE_DIR"

    if [ "$USE_CACHE" = true ] && [ -f "$cache_file" ]; then
        log_info "Verifying cached archive: ${cache_file}..."
        if tar -tzf "$cache_file" >/dev/null 2>&1; then
            log_success "Cached package valid. Skipping download!"
            echo "$cache_file"
            return 0
        else
            log_warn "Cached archive appears corrupt. Removing and re-downloading..."
            rm -f "$cache_file"
        fi
    fi

    log_info "Downloading ${name} (v${ver}) from: ${url}"
    local tmp_download="${cache_file}.part"
    rm -f "$tmp_download"
    curl -fL --progress-bar "$url" -o "$tmp_download"
    mv "$tmp_download" "$cache_file"

    log_success "Package downloaded and saved to cache: ${cache_file}"
    echo "$cache_file"
}

# ------------------------------------------------------------------------------
# 5. Core Binary Installer with Version-Check Guard
# ------------------------------------------------------------------------------
install_binary() {
    local name="$1"
    local url="$2"
    local ver="$3"
    local target_dir="$4"

    # Query currently installed version
    local current_installed="None"
    if [ "$name" = "Antigravity-App" ]; then
        current_installed=$(python3 -c "
import struct, json, os, re
asar = os.path.join('${target_dir}', 'resources', 'app.asar')
if os.path.isfile(asar):
    try:
        with open(asar, 'rb') as f:
            magic, h_s, h_o, j_len = struct.unpack('<IIII', f.read(16))
            hdr = json.loads(f.read(j_len).decode('utf-8'))
            curr = hdr.get('files', {}).get('package.json', {})
            f.seek(16 + j_len + int(curr['offset']))
            m = re.search(r'\"version\"\s*:\s*\"([^\"]+)\"', f.read(min(curr['size']+50, 1024)).decode('utf-8', errors='ignore'))
            if m: print(m.group(1))
    except Exception: pass
" 2>/dev/null || true)
    elif [ "$name" = "Antigravity-IDE" ]; then
        current_installed=$(python3 -c "
import json, os
p = os.path.join('${target_dir}', 'resources', 'app', 'product.json')
if os.path.isfile(p):
    try:
        with open(p, 'r') as f:
            d = json.load(f)
            print(d.get('ideVersion') or d.get('version') or '')
    except Exception: pass
" 2>/dev/null || true)
    fi

    # Version comparison check: Skip if up-to-date and not forced
    if [ "$FORCE_INSTALL" != true ] && [ -n "$current_installed" ] && [ "$current_installed" != "None" ] && [ "$current_installed" = "$ver" ]; then
        log_success "${name} is already at latest version (v${current_installed}). Skipping binary extraction."
        log_info "(Use --force to force re-download and re-installation)"
        return 0
    fi

    log_info "Installing / Updating ${name} to v${ver}..."
    local archive_path
    archive_path=$(get_or_download_package "$name" "$url" "$ver")

    if [ "$EUID" -ne 0 ] && [ ! -w "$(dirname "$target_dir")" ] && [ ! -d "$target_dir" ]; then
        sudo mkdir -p "$target_dir"
        sudo chown -R "$REAL_USER:$REAL_USER" "$target_dir"
    else
        mkdir -p "$target_dir" 2>/dev/null || sudo mkdir -p "$target_dir"
    fi

    # Backup existing app.asar if present
    if [ -f "$target_dir/resources/app.asar" ]; then
        cp "$target_dir/resources/app.asar" "${REAL_HOME}/.antigravity-${name}-app.asar.bak" 2>/dev/null || sudo cp "$target_dir/resources/app.asar" "${REAL_HOME}/.antigravity-${name}-app.asar.bak" || true
    fi

    log_info "Extracting ${name} into ${target_dir}..."
    if [ "$EUID" -eq 0 ]; then
        tar -zxf "$archive_path" --no-same-owner --strip-components=1 -C "$target_dir"
    else
        if [ -w "$target_dir" ]; then
            tar -zxf "$archive_path" --no-same-owner --strip-components=1 -C "$target_dir"
        else
            sudo tar -zxf "$archive_path" --no-same-owner --strip-components=1 -C "$target_dir"
        fi
    fi

    fix_permissions "$target_dir"
    log_success "${name} v${ver} extracted successfully in ${target_dir}"
}

# ------------------------------------------------------------------------------
# 6. Antigravity App Installation & Updates
# ------------------------------------------------------------------------------
install_antigravity_app() {
    resolve_dynamic_urls
    check_status

    install_binary "Antigravity-App" "$APP_URL" "$TARGET_APP_VER" "$APP_INSTALL_DIR"
    setup_account_1
    setup_account_2

    if [ "$SKIP_RTL" != true ]; then
        patch_rtl_app
    fi
    if [ "$SKIP_F5" != true ]; then
        patch_f5_reload
    fi

    log_info "Verifying post-install status..."
    check_status
}

# ------------------------------------------------------------------------------
# 7. Antigravity IDE Installation & Updates
# ------------------------------------------------------------------------------
install_antigravity_ide() {
    resolve_dynamic_urls
    check_status

    install_binary "Antigravity-IDE" "$IDE_URL" "$TARGET_IDE_VER" "$IDE_INSTALL_DIR"
    setup_ide_shortcuts

    if [ "$SKIP_RTL" != true ]; then
        patch_rtl_ide
    fi

    log_info "Verifying post-install status..."
    check_status
}

# ------------------------------------------------------------------------------
# 8. Setup Account 1 (Primary)
# ------------------------------------------------------------------------------
setup_account_1() {
    log_info "Configuring Account 1 (Primary)..."

    # Generate and deploy icons according to configuration
    apply_icons_config

    cat <<EOF > "${LOCAL_BIN}/antigravity-1"
#!/usr/bin/env bash
set -e
export REAL_HOME="${REAL_HOME}"
export HOME="\${REAL_HOME}"
export ANTIGRAVITY_DESKTOP_NAME="antigravity-1.desktop"
export ANTIGRAVITY_APP_NAME="antigravity-1"
export ANTIGRAVITY_ICON_PATH="${LOCAL_ICONS}/antigravity-1.png"

cd "\${REAL_HOME}" || cd /tmp
python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --daemon >/dev/null 2>&1 &
disown
exec "${APP_INSTALL_DIR}/antigravity" --class="antigravity-1" --name="antigravity-1" "\$@"
EOF
    chmod +x "${LOCAL_BIN}/antigravity-1"
    ln -sfn "${LOCAL_BIN}/antigravity-1" "${LOCAL_BIN}/antigravity"

    cat <<EOF > "${LOCAL_APPS}/antigravity-1.desktop"
[Desktop Entry]
Name=Antigravity (Account 1)
GenericName=AI Pair Programmer
Comment=Antigravity AI Platform - Account 1
Exec=${LOCAL_BIN}/antigravity-1 %U
Terminal=false
Type=Application
Icon=${LOCAL_ICONS}/antigravity-1.png
Categories=Development;IDE;
StartupWMClass=antigravity-1
MimeType=x-scheme-handler/antigravity;
StartupNotify=true
EOF
    chmod +x "${LOCAL_APPS}/antigravity-1.desktop"
    ln -sfn "${LOCAL_APPS}/antigravity-1.desktop" "${LOCAL_APPS}/antigravity.desktop"
    update-desktop-database "${LOCAL_APPS}" 2>/dev/null || true
    log_success "Account 1 configured with icons and launcher."
}

# ------------------------------------------------------------------------------
# 9. Setup Account 2 (Secondary Isolated Profile)
# ------------------------------------------------------------------------------
setup_account_2() {
    log_info "Configuring Account 2 (Secondary isolated profile)..."

    mkdir -p "$PROFILE2_DIR/.gemini/cache"
    touch "$PROFILE2_DIR/.gemini/cache/antigravity-keyring-unavailable"

    # Symlink shared history and configs
    ln -sfn "$SHARED_CONV_DIR" "$PROFILE2_DIR/.gemini/antigravity"
    ln -sfn "$SHARED_CONFIG_DIR" "$PROFILE2_DIR/.gemini/config"

    mkdir -p "$PROFILE2_DIR/.local/share"
    ln -sfn "$LOCAL_APPS" "$PROFILE2_DIR/.local/share/applications"
    ln -sfn "$LOCAL_ICONS" "$PROFILE2_DIR/.local/share/icons"

    # Generate and deploy icons according to configuration
    apply_icons_config

    # Launcher script for Account 2 with single-instance raising & --restart
    cat <<EOF > "${LOCAL_BIN}/antigravity-acc2"
#!/usr/bin/env bash
# ==============================================================================
# Antigravity Account 2 Launcher
# ==============================================================================
set -e

export REAL_HOME="${REAL_HOME}"
export PROFILE2="${PROFILE2_DIR}"
export HOME="\${PROFILE2}"

mkdir -p "\${PROFILE2}/.gemini/cache"
touch "\${PROFILE2}/.gemini/cache/antigravity-keyring-unavailable"

export ANTIGRAVITY_DESKTOP_NAME="antigravity-2.desktop"
export ANTIGRAVITY_APP_NAME="antigravity-2-account2"
export ANTIGRAVITY_ICON_PATH="${LOCAL_ICONS}/antigravity-acc2.png"
export ANTIGRAVITY_TRAY_ICON_PATH="${LOCAL_ICONS}/antigravity-acc2-tray.png"
export ANTIGRAVITY_WINDOW_TITLE="Account 2"

# 1. Handle restart request
if [ "\$1" = "--restart" ] || [ "\$1" = "-r" ]; then
    shift
    echo "[INFO] Terminating existing Antigravity Account 2 instance..."
    pkill -f "user-data-dir=.*\.antigravity-profile2.*Antigravity" 2>/dev/null || true
    sleep 1.5
fi

# 2. Check if already running
running_pid=\$(pgrep -f "user-data-dir=.*\.antigravity-profile2.*Antigravity" | head -n 1 || true)
if [ -n "\$running_pid" ]; then
    echo "[INFO] Antigravity Account 2 is already running (PID: \${running_pid})."
    echo "[INFO] Bringing window to front... (Pass --restart to restart fresh)"
    python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --focus || true
    exit 0
fi

cd "\${REAL_HOME}" || cd /tmp

# 3. Start background icon & tray cache updater
python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --daemon >/dev/null 2>&1 &
disown

# 4. Launch isolated Account 2 instance
exec "${APP_INSTALL_DIR}/antigravity" --class="antigravity-2" --name="antigravity-2" "\$@"
EOF
    chmod +x "${LOCAL_BIN}/antigravity-acc2"

    # Desktop entry for Account 2
    cat <<EOF > "${LOCAL_APPS}/antigravity-2.desktop"
[Desktop Entry]
Name=Antigravity (Account 2)
GenericName=AI Pair Programmer
Comment=Antigravity AI Platform - Account 2
Exec=${LOCAL_BIN}/antigravity-acc2 %U
Terminal=false
Type=Application
Icon=${LOCAL_ICONS}/antigravity-acc2.png
Categories=Development;IDE;
StartupWMClass=antigravity-2
StartupNotify=true
Actions=Restart;

[Desktop Action Restart]
Name=Restart Account 2
Exec=${LOCAL_BIN}/antigravity-acc2 --restart
EOF
    chmod +x "${LOCAL_APPS}/antigravity-2.desktop"
    update-desktop-database "${LOCAL_APPS}" 2>/dev/null || true

    log_success "Account 2 configured with distinct icons and single-instance management."
}

# ------------------------------------------------------------------------------
# 10. Setup Antigravity IDE Shortcuts
# ------------------------------------------------------------------------------
setup_ide_shortcuts() {
    log_info "Configuring Antigravity IDE shortcuts..."

    # Generate and deploy icons according to configuration
    apply_icons_config

    cat <<EOF > "${LOCAL_BIN}/antigravity-ide"
#!/usr/bin/env bash
python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --daemon >/dev/null 2>&1 &
disown
exec "${IDE_INSTALL_DIR}/antigravity-ide" --class="antigravity-ide" --name="antigravity-ide" "\$@"
EOF
    chmod +x "${LOCAL_BIN}/antigravity-ide"

    cat <<EOF > "${LOCAL_APPS}/antigravity-ide.desktop"
[Desktop Entry]
Name=Antigravity IDE
GenericName=Code Editor
Comment=Google Antigravity AI IDE
Exec=${LOCAL_BIN}/antigravity-ide %U
Terminal=false
Type=Application
Icon=${LOCAL_ICONS}/antigravity-ide.png
Categories=TextEditor;Development;IDE;
StartupWMClass=antigravity-ide
MimeType=x-scheme-handler/antigravity-ide;
StartupNotify=true
EOF
    chmod +x "${LOCAL_APPS}/antigravity-ide.desktop"
    update-desktop-database "${LOCAL_APPS}" 2>/dev/null || true

    # 3-Way Conversation History & Brain Artifact Sharing (App 1, App 2, IDE)
    local ide_gemini="${SHARED_GEMINI_DIR}/antigravity-ide"
    mkdir -p "$ide_gemini" "$SHARED_CONV_DIR/conversations" "$SHARED_CONV_DIR/brain"

    # Merge existing IDE conversations non-destructively if real directory
    if [ -d "$ide_gemini/conversations" ] && [ ! -L "$ide_gemini/conversations" ]; then
        log_info "Merging existing IDE conversations into shared history..."
        cp -a --update=none "$ide_gemini/conversations/"* "$SHARED_CONV_DIR/conversations/" 2>/dev/null || true
        mv "$ide_gemini/conversations" "$ide_gemini/conversations.bak"
    fi
    ln -sfn "$SHARED_CONV_DIR/conversations" "$ide_gemini/conversations"

    # Merge existing IDE brain artifacts non-destructively if real directory
    if [ -d "$ide_gemini/brain" ] && [ ! -L "$ide_gemini/brain" ]; then
        log_info "Merging existing IDE brain artifacts into shared brain..."
        cp -a --update=none "$ide_gemini/brain/"* "$SHARED_CONV_DIR/brain/" 2>/dev/null || true
        mv "$ide_gemini/brain" "$ide_gemini/brain.bak"
    fi
    ln -sfn "$SHARED_CONV_DIR/brain" "$ide_gemini/brain"

    # Symlink conversation_summaries.db
    if [ -f "$ide_gemini/conversation_summaries.db" ] && [ ! -L "$ide_gemini/conversation_summaries.db" ]; then
        mv "$ide_gemini/conversation_summaries.db" "$ide_gemini/conversation_summaries.db.bak"
    fi
    if [ -f "$SHARED_CONV_DIR/conversation_summaries.db" ]; then
        ln -sfn "$SHARED_CONV_DIR/conversation_summaries.db" "$ide_gemini/conversation_summaries.db"
        [ -f "$SHARED_CONV_DIR/conversation_summaries.db-wal" ] && ln -sfn "$SHARED_CONV_DIR/conversation_summaries.db-wal" "$ide_gemini/conversation_summaries.db-wal"
        [ -f "$SHARED_CONV_DIR/conversation_summaries.db-shm" ] && ln -sfn "$SHARED_CONV_DIR/conversation_summaries.db-shm" "$ide_gemini/conversation_summaries.db-shm"
    fi

    log_success "Antigravity IDE shortcuts & 3-way shared history configured."
}

# ------------------------------------------------------------------------------
# 11. Patch RTL for App & IDE (mmnaderi/antigravity-rtl)
# ------------------------------------------------------------------------------
patch_rtl_app() {
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar}. Skipping RTL app patch."
        return 0
    fi

    # Check if already applied
    if [ "$FORCE_INSTALL" != true ] && grep -qa "ANTIGRAVITY RTL PATCH" "$asar"; then
        log_info "RTL patch is already applied to Antigravity App. Skipping."
        return 0
    fi

    log_info "Ensuring permissions before RTL app patch..."
    fix_permissions "$APP_INSTALL_DIR"

    log_info "Applying RTL patch to Antigravity App (${asar})..."
    if ! echo "n" | npx --yes antigravity-rtl@latest --app --path "$asar"; then
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
    if [ ! -d "${IDE_INSTALL_DIR}" ]; then
        log_warn "Antigravity IDE directory not found at ${IDE_INSTALL_DIR}. Skipping RTL IDE patch."
        return 0
    fi

    local main_js="${IDE_INSTALL_DIR}/resources/app/out/main.js"
    if [ "$FORCE_INSTALL" != true ] && [ -f "$main_js" ]; then
        if grep -qa "antigravity-rtl-main.js" "$main_js" 2>/dev/null || [ -f "${main_js}.rtl-bak" ]; then
            log_info "RTL patch is already applied to Antigravity IDE. Skipping."
            return 0
        fi
    fi

    log_info "Ensuring permissions before RTL IDE patch..."
    fix_permissions "$IDE_INSTALL_DIR"

    log_info "Applying RTL patch to Antigravity IDE (${IDE_INSTALL_DIR})..."
    if ! echo "n" | npx --yes antigravity-rtl@latest --ide --path "${IDE_INSTALL_DIR}"; then
        log_err "RTL IDE patch failed during execution."
        return 1
    fi

    log_success "RTL patch successfully applied to Antigravity IDE."
}

# ------------------------------------------------------------------------------
# 12. Patch F5 Manual Sync Backend Reload
# ------------------------------------------------------------------------------
patch_f5_reload() {
    local asar_file="${APP_INSTALL_DIR}/resources/app.asar"
    if [ ! -f "$asar_file" ]; then
        log_warn "app.asar not found at ${asar_file}. Skipping F5 sync patch."
        return 0
    fi

    # Check if already applied
    if [ "$FORCE_INSTALL" != true ] && grep -qa "restartLanguageServer" "$asar_file" && grep -qa "ANTIGRAVITY_TRAY_ICON_PATH" "$asar_file"; then
        log_info "F5 reload & profile isolation patch is already applied to app.asar. Skipping."
        return 0
    fi

    log_info "Ensuring permissions before F5 sync patch..."
    fix_permissions "$APP_INSTALL_DIR"

    log_info "Applying manual F5 backend reload and window/tray isolation patch..."
    local tmp_dir
    tmp_dir=$(mktemp -d /tmp/asar_patch_XXXXXX)

    npx --yes asar extract "$asar_file" "$tmp_dir/unpacked"
    node "${LOCAL_BIN}/antigravity-f5-patch.js" "$tmp_dir/unpacked"
    npx --yes asar pack "$tmp_dir/unpacked" "$tmp_dir/app.asar.patched"
    cp "$tmp_dir/app.asar.patched" "$asar_file"
    rm -rf "$tmp_dir"

    if grep -qa "restartLanguageServer" "$asar_file"; then
        log_success "F5 manual sync patch applied and verified successfully."
    else
        log_err "Verification failed: F5 patch marker not found in ${asar_file}!"
        return 1
    fi
}

patch_rtl_all() {
    patch_rtl_app
    patch_rtl_ide
    patch_f5_reload
}

update_rtl() {
    log_info "Updating antigravity-rtl package..."
    npm cache clean --force 2>/dev/null || true
    npx --yes antigravity-rtl@latest --restore || true
    FORCE_INSTALL=true patch_rtl_all
}

# ------------------------------------------------------------------------------
# 13. Smart Full Suite Update
# ------------------------------------------------------------------------------
update_all() {
    resolve_dynamic_urls
    log_info "Inspecting pre-update status & patches..."
    check_status

    log_info "Starting full suite update..."
    log_info "User configurations, databases, keys, and history will be fully preserved."

    if [ -d "$APP_INSTALL_DIR" ]; then
        install_binary "Antigravity-App" "$APP_URL" "$TARGET_APP_VER" "$APP_INSTALL_DIR"
        setup_account_1
        setup_account_2
    fi

    if [ -d "$IDE_INSTALL_DIR" ]; then
        install_binary "Antigravity-IDE" "$IDE_URL" "$TARGET_IDE_VER" "$IDE_INSTALL_DIR"
        setup_ide_shortcuts
    fi

    # Apply patches if needed
    if [ "$SKIP_RTL" != true ]; then
        patch_rtl_all
    elif [ "$SKIP_F5" != true ]; then
        patch_f5_reload
    fi

    log_info "Verifying post-update status & patches..."
    check_status
    log_success "Full suite update routine complete!"
}

# ------------------------------------------------------------------------------
# 14. Cache Cleaner
# ------------------------------------------------------------------------------
clean_cache() {
    log_info "Cleaning archive cache directory (${CACHE_DIR})..."
    rm -rf "${CACHE_DIR}"/*
    log_success "Archive cache cleared."
}

# ------------------------------------------------------------------------------
# 15. Icon & Theme Management
# ------------------------------------------------------------------------------
save_icons_config() {
    mkdir -p "$ICONS_CONF_DIR"
    cat <<EOF > "$ICONS_CONF"
# Antigravity Suite Icon Configuration
# Options for themes: "black" or "white"
# Options for recolor: "true" or "false"
ACC1_ICON_THEME="${ACC1_ICON_THEME}"
ACC2_ICON_THEME="${ACC2_ICON_THEME}"
ACC2_RECOLOR="${ACC2_RECOLOR}"
IDE_ICON_THEME="${IDE_ICON_THEME}"
EOF
}

apply_icons_config() {
    log_info "Configuring Suite Icons: App1=${ACC1_ICON_THEME}, App2=${ACC2_ICON_THEME} (Recolor: ${ACC2_RECOLOR}), IDE=${IDE_ICON_THEME}..."
    save_icons_config
    if [ -f "${LOCAL_BIN}/antigravity-generate-icons.py" ]; then
        python3 "${LOCAL_BIN}/antigravity-generate-icons.py" \
            --acc1 "${ACC1_ICON_THEME}" \
            --acc2 "${ACC2_ICON_THEME}" \
            --acc2-recolor "${ACC2_RECOLOR}" \
            --ide "${IDE_ICON_THEME}" \
            --save-config
    fi
}

configure_icons_interactive() {
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${CYAN}        Configure Antigravity Suite Icons            ${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "Current Configuration:"
    echo -e "  • Antigravity 1 Base Theme:     ${BOLD}${ACC1_ICON_THEME}${NC}"
    echo -e "  • Antigravity 2 Base Theme:     ${BOLD}${ACC2_ICON_THEME}${NC}"
    echo -e "  • Antigravity 2 Recolor Glow:  ${BOLD}${ACC2_RECOLOR}${NC} (Violet/Magenta)"
    echo -e "  • Antigravity IDE Theme:        ${BOLD}${IDE_ICON_THEME}${NC}"
    echo -e "${CYAN}-----------------------------------------------------${NC}"

    read -rp "1) Select Antigravity 1 icon [1: Black (default), 2: White]: " c1
    case "$c1" in
        2|white) ACC1_ICON_THEME="white" ;;
        *) ACC1_ICON_THEME="black" ;;
    esac

    read -rp "2) Select Antigravity 2 icon [1: Black (default), 2: White]: " c2
    case "$c2" in
        2|white) ACC2_ICON_THEME="white" ;;
        *) ACC2_ICON_THEME="black" ;;
    esac

    read -rp "3) Enable color recolor for Antigravity 2? [1: Yes (Violet Glow, default), 2: No (Keep original)]: " cr
    case "$cr" in
        2|no|false) ACC2_RECOLOR="false" ;;
        *) ACC2_RECOLOR="true" ;;
    esac

    read -rp "4) Select Antigravity IDE icon [1: White (default), 2: Black]: " ci
    case "$ci" in
        2|black) IDE_ICON_THEME="black" ;;
        *) IDE_ICON_THEME="white" ;;
    esac

    apply_icons_config
}

# ------------------------------------------------------------------------------
# CLI Help & Usage
# ------------------------------------------------------------------------------
show_help() {
    cat <<EOF
Antigravity & Antigravity IDE Suite Manager

Usage:
  $(basename "$0") [command] [options]

Commands:
  status        Check installed vs target versions, patch statuses, and cache
  all           Install / update both Antigravity Apps (Account 1 & 2), IDE, F5 patch, and RTL
  app           Install / update Antigravity App (Both Accounts, RTL, and F5)
  ide           Install / update Antigravity IDE and RTL patch
  app1          Configure Account 1 launcher and desktop shortcut
  app2          Configure Account 2 isolated profile, shared history, and shortcuts
  ide-shortcuts Configure Antigravity IDE launcher and desktop shortcut
  set-icons     Configure or re-apply icons (Black/White and Acc 2 Recolor)
  f5            Re-apply manual F5 backend reload sync patch
  rtl           Apply / re-apply antigravity-rtl to App and IDE
  update-rtl    Update antigravity-rtl to latest and re-apply
  update        Smart update: checks versions, downloads to /tmp/antigravity-cache, skips if up-to-date
  clean-cache   Remove cached tarballs in /tmp/antigravity-cache
  help          Show this help message

Options:
  --force, -f                 Force re-download and re-installation even if already at latest version
  --no-cache                  Bypass /tmp archive cache and force fresh download
  --cache-dir <dir>           Override cache directory (default: /tmp/antigravity-cache)
  --app-url <url>             Override Antigravity App download URL (skips auto-discovery)
  --ide-url <url>             Override Antigravity IDE download URL (skips auto-discovery)
  --app-dir <path>            Override Antigravity App install directory (default: /opt/antigravity2)
  --ide-dir <path>            Override Antigravity IDE install directory (default: /opt/antigravity)
  --acc1-icon <black|white>   Set Antigravity 1 icon theme (black or white)
  --acc2-icon <black|white>   Set Antigravity 2 icon theme (black or white)
  --acc2-recolor <true|false> Toggle color recoloring for Antigravity 2 (true=Violet, false=original)
  --ide-icon <white|black>    Set Antigravity IDE icon theme (white or black)
  --skip-rtl                  Skip RTL patching step
  --skip-f5                   Skip F5 reload patching step

Examples:
  $(basename "$0") status
  $(basename "$0") update
  $(basename "$0") set-icons --ide-icon white --acc1-icon black --acc2-recolor true
  $(basename "$0") set-icons
EOF
}

# ------------------------------------------------------------------------------
# Interactive Menu Mode
# ------------------------------------------------------------------------------
interactive_menu() {
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${CYAN}   Antigravity & Antigravity IDE Suite Manager       ${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo "1) Smart Update All (App 1, App 2, IDE, RTL, F5) [Uses /tmp cache]"
    echo "2) Install / Update Antigravity App (Both Accounts)"
    echo "3) Install / Update Antigravity IDE"
    echo "4) Configure / Repair Account 2 (Isolated Profile & Shared History)"
    echo "5) Apply / Update RTL Patcher (mmnaderi/antigravity-rtl)"
    echo "6) Re-apply F5 Manual Sync Backend Reload Patch"
    echo "7) Check Versions, Cache & Patch Statuses (Status Table)"
    echo "8) Force Full Re-download & Reinstall Everything (--force)"
    echo "9) Clean Download Cache (/tmp/antigravity-cache)"
    echo "10) Configure Icons (Black/White Themes & Account 2 Recolor)"
    echo "0) Exit"
    echo -e "${CYAN}-----------------------------------------------------${NC}"
    read -rp "Select an option [0-10]: " choice

    case "$choice" in
        1) update_all ;;
        2) install_antigravity_app ;;
        3) install_antigravity_ide ;;
        4) setup_account_2 ;;
        5) update_rtl ;;
        6) patch_f5_reload ;;
        7) resolve_dynamic_urls && check_status ;;
        8) FORCE_INSTALL=true update_all ;;
        9) clean_cache ;;
        10) configure_icons_interactive ;;
        0) exit 0 ;;
        *)
            log_err "Invalid selection."
            exit 1
            ;;
    esac
}

# ------------------------------------------------------------------------------
# Main Argument Parsing
# ------------------------------------------------------------------------------
COMMAND=""

while [ $# -gt 0 ]; do
    case "$1" in
        --app-url)
            APP_URL="$2"
            shift 2
            ;;
        --ide-url)
            IDE_URL="$2"
            shift 2
            ;;
        --app-dir)
            APP_INSTALL_DIR="$2"
            shift 2
            ;;
        --ide-dir)
            IDE_INSTALL_DIR="$2"
            shift 2
            ;;
        --cache-dir)
            CACHE_DIR="$2"
            shift 2
            ;;
        --acc1-icon)
            ACC1_ICON_THEME="$2"
            CLI_ICON_GIVEN=true
            shift 2
            ;;
        --acc2-icon)
            ACC2_ICON_THEME="$2"
            CLI_ICON_GIVEN=true
            shift 2
            ;;
        --acc2-recolor)
            ACC2_RECOLOR="$2"
            CLI_ICON_GIVEN=true
            shift 2
            ;;
        --ide-icon)
            IDE_ICON_THEME="$2"
            CLI_ICON_GIVEN=true
            shift 2
            ;;
        --force|-f)
            FORCE_INSTALL=true
            shift
            ;;
        --no-cache)
            USE_CACHE=false
            shift
            ;;
        --skip-rtl)
            SKIP_RTL=true
            shift
            ;;
        --skip-f5)
            SKIP_F5=true
            shift
            ;;
        status|all|app|ide|app1|app2|ide-shortcuts|f5|rtl|update-rtl|update|clean-cache|set-icons|icons|help)
            COMMAND="$1"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_err "Unknown argument: $1"
            show_help
            exit 1
            ;;
    esac
done

if [ -z "$COMMAND" ]; then
    interactive_menu
else
    case "$COMMAND" in
        status)
            resolve_dynamic_urls
            check_status
            ;;
        all)
            install_antigravity_app
            install_antigravity_ide
            ;;
        app)
            install_antigravity_app
            ;;
        ide)
            install_antigravity_ide
            ;;
        app1)
            setup_account_1
            ;;
        app2)
            setup_account_2
            ;;
        ide-shortcuts)
            setup_ide_shortcuts
            ;;
        set-icons|icons)
            if [ "$CLI_ICON_GIVEN" = true ]; then
                apply_icons_config
            else
                configure_icons_interactive
            fi
            ;;
        f5)
            patch_f5_reload
            ;;
        rtl)
            patch_rtl_all
            ;;
        update-rtl)
            update_rtl
            ;;
        update)
            update_all
            ;;
        clean-cache)
            clean_cache
            ;;
        help)
            show_help
            ;;
    esac
fi
