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
APP_INSTALL_DIR="${ANTIGRAVITY_APP_DIR:-}"
IDE_INSTALL_DIR="${ANTIGRAVITY_IDE_DIR:-}"

if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    REAL_USER="$SUDO_USER"
else
    REAL_USER="${USER:-$(whoami)}"
fi
REAL_HOME=$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6)
REAL_HOME="${REAL_HOME:-$HOME}"

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
ACC1_EMBLEM_COLOR="original"
ACC2_ICON_THEME="black"
ACC2_EMBLEM_COLOR="violet"
ACC2_RECOLOR="true"
IDE_ICON_THEME="white"
IDE_EMBLEM_COLOR="original"
CLI_ICON_GIVEN=false

if [ -f "$ICONS_CONF" ]; then
    # shellcheck source=/dev/null
    source "$ICONS_CONF"
fi

# Keyring Configuration Defaults & Persistence
KEYRING_CONF="${ICONS_CONF_DIR}/keyring.conf"
KEYRING_MODE_APP1="normal"
KEYRING_MODE_APP2="normal"
KEYRING_MODE_IDE="normal"

if [ -f "$KEYRING_CONF" ]; then
    # shellcheck source=/dev/null
    source "$KEYRING_CONF"
fi

# Installation Paths Configuration Defaults & Persistence
PATHS_CONF="${ICONS_CONF_DIR}/paths.conf"
if [ -f "$PATHS_CONF" ]; then
    # shellcheck source=/dev/null
    source "$PATHS_CONF"
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
BLUE="\033[1;38;5;75m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
CYAN="\033[1;36m"
NC="\033[0m"
BOLD="\033[1m"

log_info() { echo -e "${BLUE}[INFO]${NC} $1" >&2; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1" >&2; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" >&2; }
log_err() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

mkdir -p "$LOCAL_BIN" "$LOCAL_APPS" "$LOCAL_ICONS" "$SHARED_CONV_DIR" "$SHARED_CONFIG_DIR" "$CACHE_DIR"

# ------------------------------------------------------------------------------
# 0. System Installation Auto-Detection
# ------------------------------------------------------------------------------
auto_detect_installations() {
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local DETECT_SCRIPT=""
    if [ -f "${SCRIPT_DIR}/antigravity-detect.py" ]; then
        DETECT_SCRIPT="${SCRIPT_DIR}/antigravity-detect.py"
    elif [ -f "${LOCAL_BIN}/antigravity-detect.py" ]; then
        DETECT_SCRIPT="${LOCAL_BIN}/antigravity-detect.py"
    fi

    if [ -n "$DETECT_SCRIPT" ]; then
        local env_vars
        env_vars=$(python3 "$DETECT_SCRIPT" --env 2>/dev/null || true)
        if [ -n "$env_vars" ]; then
            eval "$env_vars"
        fi
    fi

    if [ -z "$APP_INSTALL_DIR" ] || [ ! -f "${APP_INSTALL_DIR}/antigravity" ]; then
        if [ -n "$ANTIGRAVITY_DETECTED_APP" ] && [ -f "${ANTIGRAVITY_DETECTED_APP}/antigravity" ]; then
            APP_INSTALL_DIR="$ANTIGRAVITY_DETECTED_APP"
        else
            for cand in "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity"; do
                if [ -f "${cand}/antigravity" ]; then
                    APP_INSTALL_DIR="$cand"
                    break
                fi
            done
            APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/Antigravity-x64}"
        fi
    fi

    if [ -z "$IDE_INSTALL_DIR" ] || [ ! -f "${IDE_INSTALL_DIR}/antigravity-ide" ]; then
        if [ -n "$ANTIGRAVITY_DETECTED_IDE" ] && [ -f "${ANTIGRAVITY_DETECTED_IDE}/antigravity-ide" ]; then
            IDE_INSTALL_DIR="$ANTIGRAVITY_DETECTED_IDE"
        else
            for cand in "/opt/antigravity-ide" "/opt/antigravity" "/opt/antigravity2"; do
                if [ -f "${cand}/antigravity-ide" ]; then
                    IDE_INSTALL_DIR="$cand"
                    break
                fi
            done
            IDE_INSTALL_DIR="${IDE_INSTALL_DIR:-/opt/antigravity-ide}"
        fi
    fi
}
auto_detect_installations

detect_installations() {
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local DETECT_SCRIPT=""
    if [ -f "${SCRIPT_DIR}/antigravity-detect.py" ]; then
        DETECT_SCRIPT="${SCRIPT_DIR}/antigravity-detect.py"
    elif [ -f "${LOCAL_BIN}/antigravity-detect.py" ]; then
        DETECT_SCRIPT="${LOCAL_BIN}/antigravity-detect.py"
    fi

    if [ -n "$DETECT_SCRIPT" ]; then
        python3 "$DETECT_SCRIPT"
    else
        log_err "antigravity-detect.py not found in ${SCRIPT_DIR} or ${LOCAL_BIN}."
    fi
}

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
    auto_detect_installations
    if [ -z "$TARGET_APP_VER" ] || [ -z "$TARGET_IDE_VER" ]; then
        resolve_dynamic_urls >/dev/null 2>&1 || true
    fi

    python3 - "$APP_INSTALL_DIR" "$IDE_INSTALL_DIR" "$PROFILE2_DIR" "$APP_URL" "$IDE_URL" "$TARGET_APP_VER" "$TARGET_IDE_VER" "$CACHE_DIR" "$REAL_USER" "$ACC1_ICON_THEME" "$ACC2_ICON_THEME" "$ACC2_RECOLOR" "$IDE_ICON_THEME" "$REAL_HOME" "$LOCAL_BIN" << 'EOF'
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
REAL_HOME = sys.argv[14] if len(sys.argv) > 14 else os.path.expanduser('~')
LOCAL_BIN = sys.argv[15] if len(sys.argv) > 15 else os.path.join(REAL_HOME, '.local', 'bin')

G = '\033[1;32m'
Y = '\033[1;33m'
R = '\033[1;31m'
B = '\033[1;38;5;75m'
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

def check_keyring_storage():
    app1_cache = os.path.isfile(os.path.join(REAL_HOME, ".gemini", "cache", "antigravity-keyring-unavailable"))
    app1_l = os.path.join(LOCAL_BIN, "antigravity-1")
    app1_flag = False
    if os.path.isfile(app1_l):
        try:
            with open(app1_l, "r", errors="ignore") as f:
                app1_flag = "--password-store=basic" in f.read()
        except Exception:
            pass
    app1_norm = (app1_cache or app1_flag)

    app2_cache = os.path.isfile(os.path.join(PROFILE2_DIR, ".gemini", "cache", "antigravity-keyring-unavailable"))
    app2_norm = app2_cache

    if app1_norm and app2_norm:
        return f"{G}Normal File Storage (Decoupled from GNOME Keyring){NC}"
    elif app1_norm or app2_norm:
        return f"{Y}Partial (Mixed File / Keyring){NC}"
    return f"{Y}GNOME Keyring (Secret Service){NC}"

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

def check_customization_sharing():
    real_gemini = os.path.join(os.path.dirname(PROFILE2_DIR), '.gemini')
    gemide = os.path.join(os.path.dirname(PROFILE2_DIR), '.gemide')
    gemide_rule = os.path.islink(os.path.join(gemide, 'GEMINI.md'))
    gemide_cfg = os.path.islink(os.path.join(gemide, 'config'))
    p2_rule = os.path.islink(os.path.join(PROFILE2_DIR, '.gemini', 'GEMINI.md'))
    if gemide_rule and gemide_cfg and p2_rule:
        return f"{G}Unified (Rules, Skills, MCP across all instances){NC}"
    elif gemide_rule or p2_rule:
        return f"{Y}Partially Shared{NC}"
    return f"{Y}Standalone{NC}"

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

def scan_all_installations():
    candidates = set()
    roots = ['/opt', '/usr/share', '/usr/lib', '/usr/local/share',
             os.path.expanduser('~/.local/share'), os.path.expanduser('~/.local/lib'), os.path.expanduser('~/opt'), os.path.expanduser('~/.antigravity')]
    for r in roots:
        if os.path.isdir(r):
            for pat in ['*antigravity*', '*Antigravity*']:
                for m in glob.glob(os.path.join(r, pat)):
                    if os.path.isdir(m):
                        candidates.add(os.path.realpath(m))
    for p in os.environ.get('PATH', '').split(':'):
        for cmd in ['antigravity', 'antigravity-ide', 'antigravity-1', 'antigravity-acc2']:
            fp = os.path.join(p, cmd)
            if os.path.isfile(fp):
                rp = os.path.realpath(fp)
                d = os.path.dirname(rp)
                if 'manager' not in d.lower():
                    candidates.add(d)
                if os.path.basename(d) in ['bin', 'MacOS']:
                    candidates.add(os.path.dirname(d))
    results = []
    seen = set()
    for c in sorted(candidates):
        rc = os.path.realpath(c)
        if rc in seen or 'manager' in rc.lower(): continue
        iv = get_ide_version(rc)
        if iv:
            results.append(('Antigravity IDE', iv, rc))
            seen.add(rc)
            continue
        av = get_app_version(rc)
        if av:
            results.append(('Antigravity App', av, rc))
            seen.add(rc)
    return results

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
print(f"{BOLD}Detected System Installations:{NC}")
installs = scan_all_installations()
if installs:
    for itype, iver, ipath in installs:
        tag = ""
        if APP_DIR and os.path.realpath(ipath) == os.path.realpath(APP_DIR): tag = f" {G}[Primary App]{NC}"
        elif IDE_DIR and os.path.realpath(ipath) == os.path.realpath(IDE_DIR): tag = f" {G}[Primary IDE]{NC}"
        print(f"  • {itype:<20} v{iver:<10} in {ipath}{tag}")
else:
    print(f"  {Y}None detected outside default locations.{NC}")
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
print(f"  • Keyring Storage Mode:   {check_keyring_storage()}")
print(f"  • History Sharing:        {check_history_sharing()}")
print(f"  • Customizations Sharing: {check_customization_sharing()}")
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
        fi
        if [ -f "$target_dir/chrome-sandbox" ]; then
            local sb_stat
            sb_stat=$(stat -c "%u:%a" "$target_dir/chrome-sandbox" 2>/dev/null || true)
            if [ "$sb_stat" != "0:4755" ]; then
                log_info "Configuring SUID root permissions (4755) for ${target_dir}/chrome-sandbox..."
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
    if [ ! -f "$tmp_download" ] || [ ! -s "$tmp_download" ]; then
        log_err "Download failed or package is empty for ${name} from ${url}"
        rm -f "$tmp_download"
        return 1
    fi
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
    archive_path=$(get_or_download_package "$name" "$url" "$ver" | tail -n1 | tr -d '\r\n')

    if [ -z "$archive_path" ] || [ ! -f "$archive_path" ]; then
        log_err "Failed to obtain package archive for ${name} v${ver} (archive: '$archive_path')."
        return 1
    fi

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
    if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
        setup_account_2
    fi

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

    auto_detect_installations
    if [ -z "$APP_INSTALL_DIR" ] || [ ! -f "${APP_INSTALL_DIR}/antigravity" ]; then
        for cand in "$APP_INSTALL_DIR" "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity"; do
            if [ -n "$cand" ] && [ -f "${cand}/antigravity" ]; then
                APP_INSTALL_DIR="$cand"
                break
            fi
        done
    fi
    APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/Antigravity-x64}"

    # Generate and deploy icons according to configuration
    apply_icons_config || true

    local pass_store_flag=""
    if [ "$KEYRING_MODE_APP1" = "normal" ]; then
        pass_store_flag="--password-store=basic "
        mkdir -p "${REAL_HOME}/.gemini/cache"
        touch "${REAL_HOME}/.gemini/cache/antigravity-keyring-unavailable"
    else
        rm -f "${REAL_HOME}/.gemini/cache/antigravity-keyring-unavailable" 2>/dev/null || true
    fi

    local has_other_accounts=false
    if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
        has_other_accounts=true
    else
        for p in "${REAL_HOME}"/.antigravity-profile-app-*; do
            if [ -d "$p" ]; then
                has_other_accounts=true
                break
            fi
        done
    fi

    local wm_class="antigravity"
    local desktop_name="antigravity.desktop"
    local app_title="Antigravity"
    local app_comment="Antigravity AI Platform"
    local icon_name="antigravity"

    if [ "$has_other_accounts" = true ]; then
        wm_class="antigravity-1"
        desktop_name="antigravity-1.desktop"
        app_title="Antigravity (Account 1)"
        app_comment="Antigravity AI Platform - Account 1"
        icon_name="antigravity-1"
    fi

    log_info "Configuring ${app_title} (${desktop_name})..."

    cat <<EOF > "${LOCAL_BIN}/antigravity-1"
#!/usr/bin/env bash
set -e
export REAL_HOME="${REAL_HOME}"
export HOME="\${REAL_HOME}"
export ANTIGRAVITY_DESKTOP_NAME="${desktop_name}"
export ANTIGRAVITY_APP_NAME="${wm_class}"
export ANTIGRAVITY_ICON_PATH="${LOCAL_ICONS}/${icon_name}.png"

cd "\${REAL_HOME}" || cd /tmp
python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --daemon >/dev/null 2>&1 &
python3 "${LOCAL_BIN}/antigravity-merge-history.py" --quiet >/dev/null 2>&1 &
disown

# SUID sandbox verification guard: prevent fatal crash if chrome-sandbox lacks 4755 root permissions
SANDBOX_FLAG=""
if [ -f "${APP_INSTALL_DIR}/chrome-sandbox" ]; then
    sb_stat=\$(stat -c "%u:%a" "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null || true)
    if [ "\$sb_stat" != "0:4755" ]; then
        if sudo -n chown root:root "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null && sudo -n chmod 4755 "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null; then
            :
        else
            SANDBOX_FLAG="--no-sandbox "
        fi
    fi
fi

exec "${APP_INSTALL_DIR}/antigravity" \${SANDBOX_FLAG}${pass_store_flag}--class="${wm_class}" --name="${wm_class}" "\$@"
EOF
    chmod +x "${LOCAL_BIN}/antigravity-1"
    ln -sfn "${LOCAL_BIN}/antigravity-1" "${LOCAL_BIN}/antigravity"

    cat <<EOF > "${LOCAL_APPS}/${desktop_name}"
[Desktop Entry]
Name=${app_title}
GenericName=AI Pair Programmer
Comment=${app_comment}
Exec=${LOCAL_BIN}/antigravity %U
Terminal=false
Type=Application
Icon=${icon_name}
Categories=Development;IDE;
StartupWMClass=${wm_class}
MimeType=x-scheme-handler/antigravity;
StartupNotify=true
EOF
    chmod +x "${LOCAL_APPS}/${desktop_name}"

    if [ "$has_other_accounts" = true ]; then
        rm -f "${LOCAL_APPS}/antigravity.desktop" 2>/dev/null || true
    else
        rm -f "${LOCAL_APPS}/antigravity-1.desktop" 2>/dev/null || true
    fi

    # Guarantee icon exists on disk for both antigravity and antigravity-1
    if [ ! -f "${LOCAL_ICONS}/${icon_name}.png" ]; then
        if [ -f "${LOCAL_ICONS}/antigravity-master-black.png" ]; then
            cp -f "${LOCAL_ICONS}/antigravity-master-black.png" "${LOCAL_ICONS}/${icon_name}.png" 2>/dev/null || true
        elif [ -f "${APP_INSTALL_DIR}/resources/icon.png" ]; then
            cp -f "${APP_INSTALL_DIR}/resources/icon.png" "${LOCAL_ICONS}/${icon_name}.png" 2>/dev/null || true
        fi
    fi
    if [ -f "${LOCAL_ICONS}/antigravity-1.png" ] && [ ! -f "${LOCAL_ICONS}/antigravity.png" ]; then
        cp -f "${LOCAL_ICONS}/antigravity-1.png" "${LOCAL_ICONS}/antigravity.png" 2>/dev/null || true
    elif [ -f "${LOCAL_ICONS}/antigravity.png" ] && [ ! -f "${LOCAL_ICONS}/antigravity-1.png" ]; then
        cp -f "${LOCAL_ICONS}/antigravity.png" "${LOCAL_ICONS}/antigravity-1.png" 2>/dev/null || true
    fi

    update-desktop-database "${LOCAL_APPS}" 2>/dev/null || true
    xdg-mime default "${desktop_name}" x-scheme-handler/antigravity 2>/dev/null || true
    log_success "${app_title} configured with launcher and icons."
}

# ------------------------------------------------------------------------------
# 9. Setup Account 2 (Secondary Isolated Profile)
# ------------------------------------------------------------------------------
setup_account_2() {
    log_info "Configuring Account 2 (Secondary isolated profile)..."

    auto_detect_installations
    if [ -z "$APP_INSTALL_DIR" ] || [ ! -f "${APP_INSTALL_DIR}/antigravity" ]; then
        for cand in "$APP_INSTALL_DIR" "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity"; do
            if [ -n "$cand" ] && [ -f "${cand}/antigravity" ]; then
                APP_INSTALL_DIR="$cand"
                break
            fi
        done
    fi
    APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/Antigravity-x64}"

    local pass_store_flag=""
    if [ "$KEYRING_MODE_APP2" = "normal" ]; then
        pass_store_flag="--password-store=basic "
        mkdir -p "$PROFILE2_DIR/.gemini/cache"
        touch "$PROFILE2_DIR/.gemini/cache/antigravity-keyring-unavailable"
    else
        rm -f "$PROFILE2_DIR/.gemini/cache/antigravity-keyring-unavailable" 2>/dev/null || true
    fi

    # Symlink shared history, configs, and master GEMINI.md
    ln -sfn "$SHARED_CONV_DIR" "$PROFILE2_DIR/.gemini/antigravity"
    ln -sfn "$SHARED_CONFIG_DIR" "$PROFILE2_DIR/.gemini/config"
    [ -f "$SHARED_GEMINI_DIR/GEMINI.md" ] && ln -sfn "$SHARED_GEMINI_DIR/GEMINI.md" "$PROFILE2_DIR/.gemini/GEMINI.md"
    for shared_json in projects.json settings.json .env state.json trustedFolders.json; do
        [ -f "$SHARED_GEMINI_DIR/$shared_json" ] && ln -sfn "$SHARED_GEMINI_DIR/$shared_json" "$PROFILE2_DIR/.gemini/$shared_json"
    done

    mkdir -p "$PROFILE2_DIR/.local/share"
    ln -sfn "$LOCAL_APPS" "$PROFILE2_DIR/.local/share/applications"
    ln -sfn "$LOCAL_ICONS" "$PROFILE2_DIR/.local/share/icons"

    # Generate and deploy icons according to configuration
    apply_icons_config || true

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
python3 "${LOCAL_BIN}/antigravity-merge-history.py" --quiet >/dev/null 2>&1 &
disown

# SUID sandbox verification guard: prevent fatal crash if chrome-sandbox lacks 4755 root permissions
SANDBOX_FLAG=""
if [ -f "${APP_INSTALL_DIR}/chrome-sandbox" ]; then
    sb_stat=\$(stat -c "%u:%a" "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null || true)
    if [ "\$sb_stat" != "0:4755" ]; then
        if sudo -n chown root:root "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null && sudo -n chmod 4755 "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null; then
            :
        else
            SANDBOX_FLAG="--no-sandbox "
        fi
    fi
fi

# 4. Launch isolated Account 2 instance
exec "${APP_INSTALL_DIR}/antigravity" \${SANDBOX_FLAG}${pass_store_flag}--class="antigravity-2" --name="antigravity-2" "\$@"
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

    # Synchronize Account 1 to ensure distinct naming (antigravity-1.desktop)
    setup_account_1

    log_success "Account 2 configured with distinct icons and single-instance management."
}

# ------------------------------------------------------------------------------
# 10. Setup Antigravity IDE Shortcuts
# ------------------------------------------------------------------------------
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

    # Generate and deploy icons according to configuration
    apply_icons_config || true

    local ide_pass_store=""
    if [ "$KEYRING_MODE_IDE" = "normal" ]; then
        ide_pass_store="--password-store=basic "
    fi

    cat <<EOF > "${LOCAL_BIN}/antigravity-ide"
#!/usr/bin/env bash
export DBUS_SESSION_BUS_ADDRESS=""
export GNOME_KEYRING_CONTROL=""
export SSH_AUTH_SOCK=""
python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --daemon >/dev/null 2>&1 &
python3 "${LOCAL_BIN}/antigravity-merge-history.py" --quiet >/dev/null 2>&1 &
disown

# SUID sandbox verification guard: prevent fatal crash if chrome-sandbox lacks 4755 root permissions
SANDBOX_FLAG=""
if [ -f "${IDE_INSTALL_DIR}/chrome-sandbox" ]; then
    sb_stat=\$(stat -c "%u:%a" "${IDE_INSTALL_DIR}/chrome-sandbox" 2>/dev/null || true)
    if [ "\$sb_stat" != "0:4755" ]; then
        if sudo -n chown root:root "${IDE_INSTALL_DIR}/chrome-sandbox" 2>/dev/null && sudo -n chmod 4755 "${IDE_INSTALL_DIR}/chrome-sandbox" 2>/dev/null; then
            :
        else
            SANDBOX_FLAG="--no-sandbox "
        fi
    fi
fi

exec "${IDE_INSTALL_DIR}/antigravity-ide" \${SANDBOX_FLAG}${ide_pass_store}--class="antigravity-ide" --name="antigravity-ide" "\$@"
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
Icon=antigravity-ide
Categories=TextEditor;Development;IDE;
StartupWMClass=antigravity-ide
MimeType=x-scheme-handler/antigravity-ide;
StartupNotify=true
EOF
    chmod +x "${LOCAL_APPS}/antigravity-ide.desktop"

    if [ ! -f "${LOCAL_ICONS}/antigravity-ide.png" ]; then
        if [ -f "${LOCAL_ICONS}/antigravity-master-white.png" ]; then
            cp -f "${LOCAL_ICONS}/antigravity-master-white.png" "${LOCAL_ICONS}/antigravity-ide.png" 2>/dev/null || true
        elif [ -f "${LOCAL_ICONS}/antigravity-master-black.png" ]; then
            cp -f "${LOCAL_ICONS}/antigravity-master-black.png" "${LOCAL_ICONS}/antigravity-ide.png" 2>/dev/null || true
        fi
    fi

    update-desktop-database "${LOCAL_APPS}" 2>/dev/null || true
    xdg-mime default antigravity-ide.desktop x-scheme-handler/antigravity-ide 2>/dev/null || true

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

    # Symlink protobuf index summaries across App and IDE
    for sym_proto in "agyhub_summaries_proto.pb" "jetbox_summaries_proto.pb" "jetbox_summaries.pb"; do
        if [ -f "$SHARED_CONV_DIR/agyhub_summaries_proto.pb" ]; then
            ln -sfn "$SHARED_CONV_DIR/agyhub_summaries_proto.pb" "$ide_gemini/$sym_proto"
        fi
    done

    # Symlink master GEMINI.md, MCP tool schemas, custom skills, rules, and plugins across IDE instances
    for ide_root in "${REAL_HOME}/.gemide" "${REAL_HOME}/.gemini-ide"; do
        if [ -d "$ide_root" ]; then
            # Link root GEMINI.md and shared global configs
            [ -f "${SHARED_GEMINI_DIR}/GEMINI.md" ] && ln -sfn "${SHARED_GEMINI_DIR}/GEMINI.md" "$ide_root/GEMINI.md"
            for shared_json in projects.json settings.json .env state.json trustedFolders.json; do
                [ -f "${SHARED_GEMINI_DIR}/$shared_json" ] && ln -sfn "${SHARED_GEMINI_DIR}/$shared_json" "$ide_root/$shared_json"
            done

            # Link config directory (skills, rules, plugins, mcp_config.json)
            if [ -d "$ide_root/config" ] && [ ! -L "$ide_root/config" ]; then
                mv "$ide_root/config" "$ide_root/config.bak_$(date +%s)"
            fi
            ln -sfn "$SHARED_CONFIG_DIR" "$ide_root/config"

            # Link mcp schemas and plugin data under antigravity-ide
            local target_ide_app="$ide_root/antigravity-ide"
            mkdir -p "$target_ide_app"
            ln -sfn "$SHARED_CONV_DIR/mcp" "$target_ide_app/mcp"
            ln -sfn "$SHARED_CONV_DIR/plugin_data" "$target_ide_app/plugin_data"

            # Clean up redundant legacy GEMINI.md symlinks to prevent duplicate rule registration
            rm -f "$target_ide_app/GEMINI.md" "$ide_root/config/GEMINI.md"
        fi
    done

    # Run history merger & index synchronization
    merge_history
    enable_sync_service

    log_success "Antigravity IDE shortcuts & 3-way shared history configured."
}

# ------------------------------------------------------------------------------
# 10. Background History Sync Daemon (systemd user unit)
# ------------------------------------------------------------------------------
enable_sync_service() {
    log_info "Configuring real-time background history sync daemon..."
    local systemd_dir="${REAL_HOME}/.config/systemd/user"
    mkdir -p "$systemd_dir"

    cat <<EOF > "${systemd_dir}/antigravity-sync.service"
[Unit]
Description=Antigravity Real-Time History & Chat Synchronization Daemon
After=default.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 ${LOCAL_BIN}/antigravity-merge-history.py --watch
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user enable --now antigravity-sync.service 2>/dev/null || true
    log_success "Background history sync daemon enabled & active."
}

# ------------------------------------------------------------------------------
# 11. Multi-Instance Management & History Synchronization
# ------------------------------------------------------------------------------
merge_history() {
    log_info "Synchronizing and backfilling conversation history across all profiles..."
    if [ -f "${LOCAL_BIN}/antigravity-merge-history.py" ]; then
        python3 "${LOCAL_BIN}/antigravity-merge-history.py" --master "$SHARED_CONV_DIR"
    elif [ -f "${SCRIPT_DIR}/bin/antigravity-merge-history.py" ]; then
        python3 "${SCRIPT_DIR}/bin/antigravity-merge-history.py" --master "$SHARED_CONV_DIR"
    else
        log_err "antigravity-merge-history.py not found."
        return 1
    fi
    log_success "History synchronization complete."
}

create_instance() {
    local itype="$1"
    local iid="$2"
    local imode="$3"
    local itheme="${4:-black}"
    local ihue="$5"

    auto_detect_installations
    APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/Antigravity-x64}"
    IDE_INSTALL_DIR="${IDE_INSTALL_DIR:-/opt/antigravity-ide}"

    if [ -z "$itype" ]; then
        echo -e "${CYAN}=====================================================${NC}"
        echo -e "${CYAN}         Create Antigravity Instance / Profile       ${NC}"
        echo -e "${CYAN}=====================================================${NC}"
        echo "Select Instance Type:"
        echo "  1) Antigravity App (Desktop App)"
        echo "  2) Antigravity IDE (VS Code Edition)"
        read -rp "Enter choice [1-2]: " t_choice
        case "$t_choice" in
            2|ide|IDE) itype="ide" ;;
            *) itype="app" ;;
        esac
    fi

    itype=$(echo "$itype" | tr '[:upper:]' '[:lower:]')
    if [ "$itype" != "app" ] && [ "$itype" != "ide" ]; then
        log_err "Invalid instance type '${itype}'. Must be 'app' or 'ide'."
        return 1
    fi

    if [ -z "$iid" ]; then
        read -rp "Enter instance name or number (e.g. 3, 4, client, work, dev): " iid
    fi
    iid=$(echo "$iid" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9_-]+/-/g; s/^-+|-+$//g')
    if [ -z "$iid" ]; then
        log_err "Instance name cannot be empty."
        return 1
    fi

    if [ -z "$imode" ]; then
        echo -e "\nSelect History Mode:"
        echo "  1) Shared (Unified conversations & artifacts across instances) [Default]"
        echo "  2) Isolated (Dedicated private conversations & artifacts)"
        read -rp "Enter choice [1-2]: " m_choice
        case "$m_choice" in
            2|isolated|private) imode="isolated" ;;
            *) imode="shared" ;;
        esac
    fi
    imode=$(echo "$imode" | tr '[:upper:]' '[:lower:]')

    # Accent color selection if not given
    if [ -z "$ihue" ]; then
        echo -e "\nSelect Icon Accent Color / Recolor Glow:"
        echo "  1) Violet / Magenta (0.52)"
        echo "  2) Emerald Green (0.33)"
        echo "  3) Amber Orange (0.12)"
        echo "  4) Royal Sapphire Blue (0.60)"
        echo "  5) Ruby Rose (0.85)"
        echo "  6) Cyan / Teal (0.45)"
        echo "  7) Original Colors (No shift)"
        read -rp "Enter choice [1-7, default: 1]: " h_choice
        case "$h_choice" in
            2) ihue="0.33" ;;
            3) ihue="0.12" ;;
            4) ihue="0.60" ;;
            5) ihue="0.85" ;;
            6) ihue="0.45" ;;
            7) ihue="" ;;
            *) ihue="0.52" ;;
        esac
    fi

    log_info "Creating ${itype^^} instance '${iid}' [History: ${imode^^}, Theme: ${itheme}, Hue: ${ihue:-None}]..."

    local profile_dir
    local wm_class
    local launcher
    local desktop

    if [ "$itype" = "app" ]; then
        if [[ "$iid" =~ ^[0-9]+$ ]] && [ "$iid" -eq 2 ]; then
            profile_dir="${REAL_HOME}/.antigravity-profile2"
            wm_class="antigravity-2"
            launcher="${LOCAL_BIN}/antigravity-acc2"
            desktop="${LOCAL_APPS}/antigravity-2.desktop"
        else
            profile_dir="${REAL_HOME}/.antigravity-profile-app-${iid}"
            wm_class="antigravity-app-${iid}"
            launcher="${LOCAL_BIN}/antigravity-app-${iid}"
            desktop="${LOCAL_APPS}/antigravity-app-${iid}.desktop"
        fi

        mkdir -p "${profile_dir}/.gemini/cache"
        touch "${profile_dir}/.gemini/cache/antigravity-keyring-unavailable"

        mkdir -p "${profile_dir}/.local/share"
        ln -sfn "$LOCAL_APPS" "${profile_dir}/.local/share/applications"
        ln -sfn "$LOCAL_ICONS" "${profile_dir}/.local/share/icons"

        if [ "$imode" = "shared" ]; then
            log_info "Configuring shared conversation history with master pool..."
            rm -rf "${profile_dir}/.gemini/antigravity"
            ln -sfn "$SHARED_CONV_DIR" "${profile_dir}/.gemini/antigravity"
            ln -sfn "$SHARED_CONFIG_DIR" "${profile_dir}/.gemini/config"
        else
            log_info "Configuring isolated private conversation history..."
            if [ -L "${profile_dir}/.gemini/antigravity" ]; then
                rm -f "${profile_dir}/.gemini/antigravity"
            fi
            mkdir -p "${profile_dir}/.gemini/antigravity/conversations"
            mkdir -p "${profile_dir}/.gemini/antigravity/brain"
        fi

        # Generate custom icon
        log_info "Generating dedicated icon for ${wm_class}..."
        local icon_args=(--custom-instance "$wm_class" --custom-theme "$itheme")
        if [ -n "$ihue" ]; then
            icon_args+=(--custom-hue "$ihue")
        fi
        python3 "${LOCAL_BIN}/antigravity-generate-icons.py" "${icon_args[@]}" >/dev/null 2>&1 || true

        # Write launcher
        cat <<EOF > "$launcher"
#!/usr/bin/env bash
set -e
export REAL_HOME="${REAL_HOME}"
export PROFILE="${profile_dir}"
export HOME="\${PROFILE}"

mkdir -p "\${PROFILE}/.gemini/cache"
touch "\${PROFILE}/.gemini/cache/antigravity-keyring-unavailable"

export ANTIGRAVITY_DESKTOP_NAME="${wm_class}.desktop"
export ANTIGRAVITY_APP_NAME="${wm_class}"
export ANTIGRAVITY_ICON_PATH="${LOCAL_ICONS}/${wm_class}.png"

# Handle restart
if [ "\$1" = "--restart" ] || [ "\$1" = "-r" ]; then
    shift
    echo "[INFO] Terminating existing ${wm_class} instance..."
    pkill -f "user-data-dir=.*${profile_dir##*/}.*Antigravity" 2>/dev/null || true
    sleep 1.5
fi

# Single instance check
running_pid=\$(pgrep -f "user-data-dir=.*${profile_dir##*/}.*Antigravity" | head -n 1 || true)
if [ -n "\$running_pid" ]; then
    echo "[INFO] ${wm_class} is already running (PID: \${running_pid}). Bringing to front..."
    python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --focus "${iid}" || true
    exit 0
fi

cd "\${REAL_HOME}" || cd /tmp
python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --daemon >/dev/null 2>&1 &
disown

# SUID sandbox verification guard: prevent fatal crash if chrome-sandbox lacks 4755 root permissions
SANDBOX_FLAG=""
if [ -f "${APP_INSTALL_DIR}/chrome-sandbox" ]; then
    sb_stat=\$(stat -c "%u:%a" "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null || true)
    if [ "\$sb_stat" != "0:4755" ]; then
        if sudo -n chown root:root "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null && sudo -n chmod 4755 "${APP_INSTALL_DIR}/chrome-sandbox" 2>/dev/null; then
            :
        else
            SANDBOX_FLAG="--no-sandbox "
        fi
    fi
fi

exec "${APP_INSTALL_DIR}/antigravity" \${SANDBOX_FLAG}--password-store=basic --class="${wm_class}" --name="${wm_class}" "\$@"
EOF
        chmod +x "$launcher"

        # Write desktop shortcut
        cat <<EOF > "$desktop"
[Desktop Entry]
Name=Antigravity App (${iid})
GenericName=AI Assistant
Comment=Google Antigravity AI Assistant - Instance ${iid}
Exec=${launcher} %U
Terminal=false
Type=Application
Icon=${LOCAL_ICONS}/${wm_class}.png
Categories=Development;Utility;
StartupWMClass=${wm_class}
MimeType=x-scheme-handler/antigravity;
StartupNotify=true
EOF
        chmod +x "$desktop"

    elif [ "$itype" = "ide" ]; then
        profile_dir="${REAL_HOME}/.antigravity-ide-profile-${iid}"
        wm_class="antigravity-ide-${iid}"
        launcher="${LOCAL_BIN}/antigravity-ide-${iid}"
        desktop="${LOCAL_APPS}/antigravity-ide-${iid}.desktop"

        mkdir -p "${profile_dir}/.gemini"
        mkdir -p "${profile_dir}/.local/share"
        ln -sfn "$LOCAL_APPS" "${profile_dir}/.local/share/applications"
        ln -sfn "$LOCAL_ICONS" "${profile_dir}/.local/share/icons"

        if [ "$imode" = "shared" ]; then
            log_info "Configuring shared conversation history with master pool..."
            rm -rf "${profile_dir}/.gemini/antigravity-ide"
            ln -sfn "$SHARED_CONV_DIR" "${profile_dir}/.gemini/antigravity-ide"
        else
            log_info "Configuring isolated private conversation history..."
            if [ -L "${profile_dir}/.gemini/antigravity-ide" ]; then
                rm -f "${profile_dir}/.gemini/antigravity-ide"
            fi
            mkdir -p "${profile_dir}/.gemini/antigravity-ide/conversations"
            mkdir -p "${profile_dir}/.gemini/antigravity-ide/brain"
        fi

        # Generate custom icon
        log_info "Generating dedicated icon for ${wm_class}..."
        local icon_args=(--custom-instance "$wm_class" --custom-theme "$itheme")
        if [ -n "$ihue" ]; then
            icon_args+=(--custom-hue "$ihue")
        fi
        python3 "${LOCAL_BIN}/antigravity-generate-icons.py" "${icon_args[@]}" >/dev/null 2>&1 || true

        # Write launcher
        cat <<EOF > "$launcher"
#!/usr/bin/env bash
set -e
export REAL_HOME="${REAL_HOME}"
export PROFILE="${profile_dir}"
export HOME="\${PROFILE}"
export DBUS_SESSION_BUS_ADDRESS=""
export GNOME_KEYRING_CONTROL=""
export SSH_AUTH_SOCK=""

python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --daemon >/dev/null 2>&1 &
python3 "${LOCAL_BIN}/antigravity-merge-history.py" --quiet >/dev/null 2>&1 &
disown

# SUID sandbox verification guard: prevent fatal crash if chrome-sandbox lacks 4755 root permissions
SANDBOX_FLAG=""
if [ -f "${IDE_INSTALL_DIR}/chrome-sandbox" ]; then
    sb_stat=\$(stat -c "%u:%a" "${IDE_INSTALL_DIR}/chrome-sandbox" 2>/dev/null || true)
    if [ "\$sb_stat" != "0:4755" ]; then
        if sudo -n chown root:root "${IDE_INSTALL_DIR}/chrome-sandbox" 2>/dev/null && sudo -n chmod 4755 "${IDE_INSTALL_DIR}/chrome-sandbox" 2>/dev/null; then
            :
        else
            SANDBOX_FLAG="--no-sandbox "
        fi
    fi
fi

exec "${IDE_INSTALL_DIR}/antigravity-ide" \${SANDBOX_FLAG}--user-data-dir "\${PROFILE}/.config/Antigravity IDE" --class="${wm_class}" --name="${wm_class}" "\$@"
EOF
        chmod +x "$launcher"

        # Write desktop shortcut
        cat <<EOF > "$desktop"
[Desktop Entry]
Name=Antigravity IDE (${iid})
GenericName=Code Editor
Comment=Google Antigravity AI IDE - Instance ${iid}
Exec=${launcher} %U
Terminal=false
Type=Application
Icon=${LOCAL_ICONS}/${wm_class}.png
Categories=TextEditor;Development;IDE;
StartupWMClass=${wm_class}
MimeType=x-scheme-handler/antigravity-ide;
StartupNotify=true
EOF
        chmod +x "$desktop"
    fi

    update-desktop-database "$LOCAL_APPS" 2>/dev/null || true
    if [ "$itype" = "app" ]; then
        setup_account_1
    fi
    log_success "Instance '${iid}' (${itype^^}) created successfully!"
    echo -e "  • Launcher:       ${BOLD}${launcher}${NC}"
    echo -e "  • Desktop Entry:  ${BOLD}${desktop}${NC}"
    echo -e "  • Profile Dir:    ${BOLD}${profile_dir}${NC}"
    echo -e "  • History Mode:   ${BOLD}${imode^^}${NC}"
    echo -e "  • WM_CLASS:       ${BOLD}${wm_class}${NC}"
}

list_instances() {
    python3 - "$REAL_HOME" "$PROFILE2_DIR" "$SHARED_CONV_DIR" << 'EOF'
import os, sys, glob, subprocess

real_home = sys.argv[1]
p2_dir = sys.argv[2]
shared_conv = sys.argv[3]

G = '\033[1;32m'
Y = '\033[1;33m'
B = '\033[1;38;5;75m'
C = '\033[1;36m'
NC = '\033[0m'
BOLD = '\033[1m'

print(f"{C}========================================================================================{NC}")
print(f"{BOLD}{C}                        Antigravity Suite Multi-Instance Inventory                      {NC}")
print(f"{C}========================================================================================{NC}")
print(f"{BOLD}{B}Instance Name        Type   History Mode            WM_CLASS             Status   Launcher{NC}")
print(f"----------------------------------------------------------------------------------------")

instances = []

# 1. Primary App 1
p1_running = subprocess.run(["pgrep", "-f", "user-data-dir=.*Antigravity$"], capture_output=True).returncode == 0
instances.append(("Antigravity (Acc 1)", "App", "Primary (Shared)", "antigravity-1", f"{G}Running{NC}" if p1_running else "Stopped", "~/.local/bin/antigravity-1"))

# 2. Account 2
if os.path.isdir(p2_dir):
    p2_shared = os.path.islink(os.path.join(p2_dir, ".gemini", "antigravity"))
    p2_running = subprocess.run(["pgrep", "-f", "antigravity-profile2.*Antigravity"], capture_output=True).returncode == 0
    instances.append(("Antigravity (Acc 2)", "App", f"{G}Shared{NC}" if p2_shared else f"{Y}Isolated{NC}", "antigravity-2", f"{G}Running{NC}" if p2_running else "Stopped", "~/.local/bin/antigravity-acc2"))

# 3. Custom App profiles
for p in sorted(glob.glob(os.path.join(real_home, ".antigravity-profile-app-*"))):
    if ".bak" in p or ".removed" in p: continue
    name = os.path.basename(p).replace(".antigravity-profile-app-", "")
    is_shared = os.path.islink(os.path.join(p, ".gemini", "antigravity"))
    is_run = subprocess.run(["pgrep", "-f", f"{os.path.basename(p)}.*Antigravity"], capture_output=True).returncode == 0
    instances.append((f"App ({name})", "App", f"{G}Shared{NC}" if is_shared else f"{Y}Isolated{NC}", f"antigravity-app-{name}", f"{G}Running{NC}" if is_run else "Stopped", f"~/.local/bin/antigravity-app-{name}"))

# 4. Primary IDE
ide_shared = os.path.islink(os.path.join(real_home, ".gemini", "antigravity-ide", "conversations"))
ide_run = subprocess.run(["pgrep", "-f", "antigravity-ide"], capture_output=True).returncode == 0
instances.append(("Antigravity IDE (1)", "IDE", f"{G}Shared{NC}" if ide_shared else f"{Y}Isolated{NC}", "antigravity-ide", f"{G}Running{NC}" if ide_run else "Stopped", "~/.local/bin/antigravity-ide"))

# 5. Custom IDE profiles
for p in sorted(glob.glob(os.path.join(real_home, ".antigravity-ide-profile-*"))):
    if ".bak" in p or ".removed" in p: continue
    name = os.path.basename(p).replace(".antigravity-ide-profile-", "")
    is_shared = os.path.islink(os.path.join(p, ".gemini", "antigravity-ide"))
    is_run = subprocess.run(["pgrep", "-f", f"{os.path.basename(p)}"], capture_output=True).returncode == 0
    instances.append((f"IDE ({name})", "IDE", f"{G}Shared{NC}" if is_shared else f"{Y}Isolated{NC}", f"antigravity-ide-{name}", f"{G}Running{NC}" if is_run else "Stopped", f"~/.local/bin/antigravity-ide-{name}"))

for iname, itype, imode, iclass, istat, ilnch in instances:
    # Strip ANSI when calculating pad
    raw_mode = imode.replace(G, '').replace(Y, '').replace(NC, '')
    pad_mode = 20 + (len(imode) - len(raw_mode))
    raw_stat = istat.replace(G, '').replace(NC, '')
    pad_stat = 10 + (len(istat) - len(raw_stat))
    print(f"{iname:<20} {itype:<6} {imode:<{pad_mode}} {iclass:<24} {istat:<{pad_stat}} {ilnch}")

print(f"{C}========================================================================================{NC}")
EOF
}

set_history_mode() {
    local itype="$1"
    local iid="$2"
    local target_mode="$3"

    if [ -z "$itype" ] || [ -z "$iid" ] || [ -z "$target_mode" ]; then
        echo "Usage: $(basename "$0") set-history [app|ide] [instance_id] [shared|isolated]"
        return 1
    fi

    itype=$(echo "$itype" | tr '[:upper:]' '[:lower:]')
    target_mode=$(echo "$target_mode" | tr '[:upper:]' '[:lower:]')

    local profile_gemini=""
    if [ "$itype" = "app" ]; then
        if [ "$iid" = "2" ]; then
            profile_gemini="${REAL_HOME}/.antigravity-profile2/.gemini/antigravity"
        else
            profile_gemini="${REAL_HOME}/.antigravity-profile-app-${iid}/.gemini/antigravity"
        fi
    elif [ "$itype" = "ide" ]; then
        if [ "$iid" = "1" ] || [ "$iid" = "default" ]; then
            profile_gemini="${REAL_HOME}/.gemini/antigravity-ide"
        else
            profile_gemini="${REAL_HOME}/.antigravity-ide-profile-${iid}/.gemini/antigravity-ide"
        fi
    fi

    local parent_dir
    parent_dir="$(dirname "$profile_gemini")"
    if [ ! -d "$parent_dir" ]; then
        log_err "Instance directory for ${itype} '${iid}' does not exist (${parent_dir})."
        return 1
    fi

    # Automated restorable backup before altering history mode
    if [ -f "${LOCAL_BIN}/antigravity-migration.py" ]; then
        python3 "${LOCAL_BIN}/antigravity-migration.py" create-backup --category history --label "pre_set_history_${itype}_${iid}" >/dev/null 2>&1 || true
    elif [ -f "${SCRIPT_DIR}/bin/antigravity-migration.py" ]; then
        python3 "${SCRIPT_DIR}/bin/antigravity-migration.py" create-backup --category history --label "pre_set_history_${itype}_${iid}" >/dev/null 2>&1 || true
    fi

    if [ "$target_mode" = "shared" ]; then
        log_info "Switching ${itype} '${iid}' to SHARED history..."
        if [ "$itype" = "ide" ]; then
            local ide_conv="${profile_gemini}/conversations"
            local ide_brain="${profile_gemini}/brain"
            mkdir -p "${SHARED_CONV_DIR}/conversations" "${SHARED_CONV_DIR}/brain"
            if [ -d "$ide_conv" ] && [ ! -L "$ide_conv" ]; then
                cp -n "${ide_conv}"/*.db "${SHARED_CONV_DIR}/conversations/" 2>/dev/null || true
                mv "$ide_conv" "${ide_conv}.bak_$(date +%s)"
            fi
            if [ -d "$ide_brain" ] && [ ! -L "$ide_brain" ]; then
                cp -rn "${ide_brain}"/* "${SHARED_CONV_DIR}/brain/" 2>/dev/null || true
                mv "$ide_brain" "${ide_brain}.bak_$(date +%s)"
            fi
            ln -sfn "${SHARED_CONV_DIR}/conversations" "$ide_conv"
            ln -sfn "${SHARED_CONV_DIR}/brain" "$ide_brain"
            merge_history
        else
            if [ -d "$profile_gemini" ] && [ ! -L "$profile_gemini" ]; then
                log_info "Preserving and merging private conversations into shared pool first..."
                mkdir -p "${SHARED_CONV_DIR}/conversations" "${SHARED_CONV_DIR}/brain"
                if [ -d "${profile_gemini}/conversations" ]; then
                    cp -n "${profile_gemini}/conversations"/*.db "${SHARED_CONV_DIR}/conversations/" 2>/dev/null || true
                fi
                if [ -d "${profile_gemini}/brain" ]; then
                    cp -rn "${profile_gemini}/brain"/* "${SHARED_CONV_DIR}/brain/" 2>/dev/null || true
                fi
                mv "$profile_gemini" "${profile_gemini}.bak_$(date +%s)"
            fi
            ln -sfn "$SHARED_CONV_DIR" "$profile_gemini"
            merge_history
        fi
        log_success "${itype^^} '${iid}' is now linked to SHARED history."
    elif [ "$target_mode" = "isolated" ]; then
        log_info "Switching ${itype} '${iid}' to ISOLATED history..."
        if [ "$itype" = "ide" ]; then
            local ide_conv="${profile_gemini}/conversations"
            local ide_brain="${profile_gemini}/brain"
            [ -L "$ide_conv" ] && rm -f "$ide_conv"
            [ -L "$ide_brain" ] && rm -f "$ide_brain"
            mkdir -p "$ide_conv" "$ide_brain"
            # Clone existing conversations so chats do not vanish
            cp -n "${SHARED_CONV_DIR}/conversations"/*.db "$ide_conv/" 2>/dev/null || true
        else
            if [ -L "$profile_gemini" ]; then
                rm -f "$profile_gemini"
            fi
            mkdir -p "${profile_gemini}/conversations" "${profile_gemini}/brain"
            # Clone existing conversations so chats do not vanish
            cp -n "${SHARED_CONV_DIR}/conversations"/*.db "${profile_gemini}/conversations/" 2>/dev/null || true
            cp -n "${SHARED_CONV_DIR}"/*summaries* "${profile_gemini}/" 2>/dev/null || true
        fi
        log_success "${itype^^} '${iid}' now has ISOLATED private history (existing conversations cloned). "
    else
        log_err "Unknown mode '${target_mode}'. Use 'shared' or 'isolated'."
        return 1
    fi
}

# ------------------------------------------------------------------------------
# Cross-System Migration & Backup Wrappers
# ------------------------------------------------------------------------------
get_migration_script() {
    if [ -f "${LOCAL_BIN}/antigravity-migration.py" ]; then
        echo "${LOCAL_BIN}/antigravity-migration.py"
    elif [ -f "${SCRIPT_DIR}/bin/antigravity-migration.py" ]; then
        echo "${SCRIPT_DIR}/bin/antigravity-migration.py"
    else
        echo ""
    fi
}

export_history() {
    local m_script
    m_script="$(get_migration_script)"
    [ -z "$m_script" ] && { log_err "antigravity-migration.py not found."; return 1; }
    python3 "$m_script" export-history "$@"
}

import_history() {
    local m_script
    m_script="$(get_migration_script)"
    [ -z "$m_script" ] && { log_err "antigravity-migration.py not found."; return 1; }
    python3 "$m_script" import-history "$@"
}

export_suite() {
    local m_script
    m_script="$(get_migration_script)"
    [ -z "$m_script" ] && { log_err "antigravity-migration.py not found."; return 1; }
    python3 "$m_script" export-suite "$@"
}

import_suite() {
    local m_script
    m_script="$(get_migration_script)"
    [ -z "$m_script" ] && { log_err "antigravity-migration.py not found."; return 1; }
    python3 "$m_script" import-suite "$@"
}

export_all() {
    local m_script
    m_script="$(get_migration_script)"
    [ -z "$m_script" ] && { log_err "antigravity-migration.py not found."; return 1; }
    python3 "$m_script" export-all "$@"
}

import_all() {
    local m_script
    m_script="$(get_migration_script)"
    [ -z "$m_script" ] && { log_err "antigravity-migration.py not found."; return 1; }
    python3 "$m_script" import-all "$@"
}

manage_backups() {
    local m_script
    m_script="$(get_migration_script)"
    [ -z "$m_script" ] && { log_err "antigravity-migration.py not found."; return 1; }
    local act="${1:-list}"
    shift || true
    case "$act" in
        list)
            python3 "$m_script" list-backups
            ;;
        create)
            python3 "$m_script" create-backup "$@"
            ;;
        restore)
            python3 "$m_script" restore-backup "$@"
            ;;
        *)
            echo "Usage: $(basename "$0") backups [list|create|restore <path>]"
            ;;
    esac
}

remove_instance() {
    local itype="$1"
    local iid="$2"

    if [ -z "$itype" ] || [ -z "$iid" ]; then
        echo "Usage: $(basename "$0") remove-instance [app|ide] [instance_id]"
        return 1
    fi

    itype=$(echo "$itype" | tr '[:upper:]' '[:lower:]')
    local wm_class=""
    local profile_dir=""
    local launcher=""
    local desktop=""

    if [ "$itype" = "app" ]; then
        wm_class="antigravity-app-${iid}"
        profile_dir="${REAL_HOME}/.antigravity-profile-app-${iid}"
        launcher="${LOCAL_BIN}/antigravity-app-${iid}"
        desktop="${LOCAL_APPS}/antigravity-app-${iid}.desktop"
    elif [ "$itype" = "ide" ]; then
        wm_class="antigravity-ide-${iid}"
        profile_dir="${REAL_HOME}/.antigravity-ide-profile-${iid}"
        launcher="${LOCAL_BIN}/antigravity-ide-${iid}"
        desktop="${LOCAL_APPS}/antigravity-ide-${iid}.desktop"
    fi

    log_warn "Removing instance ${itype^^} '${iid}'..."
    rm -f "$launcher" "$desktop"
    rm -f "${LOCAL_ICONS}/${wm_class}.png"
    rm -f "${LOCAL_ICONS}/hicolor"/*/apps/"${wm_class}.png"
    update-desktop-database "$LOCAL_APPS" 2>/dev/null || true

    if [ -d "$profile_dir" ]; then
        log_info "Backing up profile directory before removal..."
        mv "$profile_dir" "${profile_dir}.removed_bak_$(date +%s)"
    fi
    log_success "Instance ${itype^^} '${iid}' successfully removed."
    if [ "$itype" = "app" ]; then
        setup_account_1
    fi
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
    local patch_js="${LOCAL_BIN}/antigravity-f5-patch.js"
    if [ ! -f "$patch_js" ]; then
        local SCRIPT_DIR
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [ -f "${SCRIPT_DIR}/antigravity-f5-patch.js" ]; then
            patch_js="${SCRIPT_DIR}/antigravity-f5-patch.js"
        fi
    fi
    if [ ! -f "$patch_js" ]; then
        log_err "antigravity-f5-patch.js not found in ${LOCAL_BIN} or ${SCRIPT_DIR}."
        return 1
    fi

    local tmp_dir
    tmp_dir=$(mktemp -d /tmp/asar_patch_XXXXXX)

    npx --yes asar extract "$asar_file" "$tmp_dir/unpacked"
    node "$patch_js" "$tmp_dir/unpacked"
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
# 13. Full Suite Installation & Smart Update
# ------------------------------------------------------------------------------
install_antigravity_all() {
    auto_detect_installations
    resolve_dynamic_urls
    log_info "Installing full Google Antigravity suite (App + IDE)..."

    install_binary "Antigravity-App" "$APP_URL" "$TARGET_APP_VER" "$APP_INSTALL_DIR"
    setup_account_1
    if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
        setup_account_2
    fi

    install_binary "Antigravity-IDE" "$IDE_URL" "$TARGET_IDE_VER" "$IDE_INSTALL_DIR"
    setup_ide_shortcuts

    if [ "$SKIP_RTL" != true ]; then
        patch_rtl_all
    elif [ "$SKIP_F5" != true ]; then
        patch_f5_reload
    fi

    log_success "Google Antigravity suite installed successfully!"
    check_status
}

update_all() {
    auto_detect_installations
    resolve_dynamic_urls
    log_info "Inspecting pre-update status & patches..."
    check_status

    log_info "Starting full suite update..."
    log_info "User configurations, databases, keys, and history will be fully preserved."

    install_binary "Antigravity-App" "$APP_URL" "$TARGET_APP_VER" "$APP_INSTALL_DIR"
    setup_account_1
    if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
        setup_account_2
    fi

    install_binary "Antigravity-IDE" "$IDE_URL" "$TARGET_IDE_VER" "$IDE_INSTALL_DIR"
    setup_ide_shortcuts

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
ACC1_ICON_THEME="${ACC1_ICON_THEME}"
ACC1_EMBLEM_COLOR="${ACC1_EMBLEM_COLOR}"
ACC2_ICON_THEME="${ACC2_ICON_THEME}"
ACC2_EMBLEM_COLOR="${ACC2_EMBLEM_COLOR}"
ACC2_RECOLOR="${ACC2_RECOLOR}"
IDE_ICON_THEME="${IDE_ICON_THEME}"
IDE_EMBLEM_COLOR="${IDE_EMBLEM_COLOR}"
EOF
}

apply_icons_config() {
    log_info "Configuring Suite Icons: App1=${ACC1_ICON_THEME} (${ACC1_EMBLEM_COLOR}), App2=${ACC2_ICON_THEME} (${ACC2_EMBLEM_COLOR}), IDE=${IDE_ICON_THEME} (${IDE_EMBLEM_COLOR})..."
    save_icons_config

    local gen_py=""
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    for cand in "${SCRIPT_DIR}/antigravity-generate-icons.py" \
                "${SCRIPT_DIR}/bin/antigravity-generate-icons.py" \
                "${REAL_HOME}/.antigravity-suite-manager/bin/antigravity-generate-icons.py" \
                "${LOCAL_BIN}/antigravity-generate-icons.py"; do
        if [ -f "$cand" ]; then
            gen_py="$cand"
            break
        fi
    done

    # Ensure generator script in LOCAL_BIN is copied/updated from source
    if [ -n "$gen_py" ] && [ -f "$gen_py" ]; then
        if [ "$gen_py" != "${LOCAL_BIN}/antigravity-generate-icons.py" ]; then
            mkdir -p "$LOCAL_BIN"
            cp -f "$gen_py" "${LOCAL_BIN}/antigravity-generate-icons.py" 2>/dev/null || sudo -n cp -f "$gen_py" "${LOCAL_BIN}/antigravity-generate-icons.py" 2>/dev/null || true
            chmod +x "${LOCAL_BIN}/antigravity-generate-icons.py" 2>/dev/null || true
            gen_py="${LOCAL_BIN}/antigravity-generate-icons.py"
        fi
    fi

    # Immediately ensure master icons exist in LOCAL_ICONS as guaranteed baseline
    mkdir -p "$LOCAL_ICONS"
    for master_b in "${LOCAL_ICONS}/antigravity-master-black.png" \
                    "${REAL_HOME}/.antigravity-suite-manager/assets/antigravity-master-black.png" \
                    "$(dirname "$(dirname "$gen_py")")/assets/antigravity-master-black.png" \
                    "${APP_INSTALL_DIR}/resources/icon.png" \
                    "/opt/Antigravity-x64/resources/icon.png" \
                    "/opt/antigravity2/resources/icon.png" \
                    "/opt/antigravity/resources/icon.png"; do
        if [ -f "$master_b" ]; then
            cp -f "$master_b" "${LOCAL_ICONS}/antigravity-master-black.png" 2>/dev/null || true
            cp -f "$master_b" "${LOCAL_ICONS}/antigravity-1.png" 2>/dev/null || true
            cp -f "$master_b" "${LOCAL_ICONS}/antigravity.png" 2>/dev/null || true
            break
        fi
    done

    for master_w in "${LOCAL_ICONS}/antigravity-master-white.png" \
                    "${REAL_HOME}/.antigravity-suite-manager/assets/antigravity-master-white.png" \
                    "$(dirname "$(dirname "$gen_py")")/assets/antigravity-master-white.png" \
                    "${IDE_INSTALL_DIR}/resources/app/resources/linux/code.png" \
                    "/opt/antigravity-ide/resources/app/resources/linux/code.png" \
                    "/opt/antigravity/resources/app/resources/linux/code.png"; do
        if [ -f "$master_w" ]; then
            cp -f "$master_w" "${LOCAL_ICONS}/antigravity-master-white.png" 2>/dev/null || true
            cp -f "$master_w" "${LOCAL_ICONS}/antigravity-ide.png" 2>/dev/null || true
            break
        fi
    done

    if [ ! -f "${LOCAL_ICONS}/antigravity-ide.png" ] && [ -f "${LOCAL_ICONS}/antigravity-master-black.png" ]; then
        cp -f "${LOCAL_ICONS}/antigravity-master-black.png" "${LOCAL_ICONS}/antigravity-ide.png" 2>/dev/null || true
    fi

    if [ -f "$gen_py" ]; then
        python3 "$gen_py" \
            --acc1 "${ACC1_ICON_THEME}" \
            --acc1-color "${ACC1_EMBLEM_COLOR}" \
            --acc2 "${ACC2_ICON_THEME}" \
            --acc2-color "${ACC2_EMBLEM_COLOR}" \
            --acc2-recolor "${ACC2_RECOLOR}" \
            --ide "${IDE_ICON_THEME}" \
            --ide-color "${IDE_EMBLEM_COLOR}" \
            --save-config 2>/dev/null || python3 "$gen_py" 2>/dev/null || true
    fi
}

configure_icons_interactive() {
    local target="${1:-all}"
    case "$target" in
        app1|acc1|1)
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "${CYAN}   Configure Antigravity (Account 1) Icon            ${NC}"
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "Current Configuration: Background: ${BOLD}${ACC1_ICON_THEME}${NC} | Emblem: ${BOLD}${ACC1_EMBLEM_COLOR}${NC}"
            echo -e "${CYAN}-----------------------------------------------------${NC}"

            echo -e "\n${BOLD}Configure Antigravity (Account 1):${NC}"
            read -rp "  Background Color [1: Black (default), 2: White]: " bg1
            case "$bg1" in
                2|white) ACC1_ICON_THEME="white" ;;
                *) ACC1_ICON_THEME="black" ;;
            esac

            echo -e "  Emblem Colors:"
            echo -e "    [1] Original Google Multi-Color (default)"
            echo -e "    [2] Violet / Magenta"
            echo -e "    [3] Royal Blue / Cyan"
            echo -e "    [4] Emerald Green"
            echo -e "    [5] Amber / Gold"
            echo -e "    [6] Ruby Red"
            echo -e "    [7] Monochrome Silver"
            read -rp "  Select Emblem Color [1-7, Default: 1]: " col1
            case "$col1" in
                2|violet|purple) ACC1_EMBLEM_COLOR="violet" ;;
                3|blue|cyan) ACC1_EMBLEM_COLOR="blue" ;;
                4|green|emerald) ACC1_EMBLEM_COLOR="green" ;;
                5|amber|gold|orange) ACC1_EMBLEM_COLOR="amber" ;;
                6|red|ruby) ACC1_EMBLEM_COLOR="red" ;;
                7|silver|monochrome|grey) ACC1_EMBLEM_COLOR="monochrome" ;;
                *) ACC1_EMBLEM_COLOR="original" ;;
            esac
            ;;

        ide)
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "${CYAN}        Configure Antigravity IDE Icon               ${NC}"
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "Current Configuration: Background: ${BOLD}${IDE_ICON_THEME}${NC} | Emblem: ${BOLD}${IDE_EMBLEM_COLOR}${NC}"
            echo -e "${CYAN}-----------------------------------------------------${NC}"

            echo -e "\n${BOLD}Configure Antigravity IDE:${NC}"
            read -rp "  Background Color [1: White (default), 2: Black]: " bgi
            case "$bgi" in
                2|black) IDE_ICON_THEME="black" ;;
                *) IDE_ICON_THEME="white" ;;
            esac

            echo -e "  Emblem Colors:"
            echo -e "    [1] Original Google Multi-Color (default)"
            echo -e "    [2] Royal Blue / Cyan"
            echo -e "    [3] Violet / Magenta"
            echo -e "    [4] Emerald Green"
            echo -e "    [5] Amber / Gold"
            echo -e "    [6] Ruby Red"
            echo -e "    [7] Monochrome Silver"
            read -rp "  Select Emblem Color [1-7, Default: 1]: " coli
            case "$coli" in
                2|blue|cyan) IDE_EMBLEM_COLOR="blue" ;;
                3|violet|purple) IDE_EMBLEM_COLOR="violet" ;;
                4|green|emerald) IDE_EMBLEM_COLOR="green" ;;
                5|amber|gold|orange) IDE_EMBLEM_COLOR="amber" ;;
                6|red|ruby) IDE_EMBLEM_COLOR="red" ;;
                7|silver|monochrome|grey) IDE_EMBLEM_COLOR="monochrome" ;;
                *) IDE_EMBLEM_COLOR="original" ;;
            esac
            ;;

        app2|acc2|2)
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "${CYAN}   Configure Antigravity (Account 2) Icon            ${NC}"
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "Current Configuration: Background: ${BOLD}${ACC2_ICON_THEME}${NC} | Emblem: ${BOLD}${ACC2_EMBLEM_COLOR}${NC}"
            echo -e "${CYAN}-----------------------------------------------------${NC}"

            echo -e "\n${BOLD}Configure Antigravity (Account 2):${NC}"
            read -rp "  Background Color [1: Black (default), 2: White]: " bg2
            case "$bg2" in
                2|white) ACC2_ICON_THEME="white" ;;
                *) ACC2_ICON_THEME="black" ;;
            esac

            echo -e "  Emblem Colors:"
            echo -e "    [1] Violet / Magenta (default)"
            echo -e "    [2] Original Google Multi-Color"
            echo -e "    [3] Royal Blue / Cyan"
            echo -e "    [4] Emerald Green"
            echo -e "    [5] Amber / Gold"
            echo -e "    [6] Ruby Red"
            echo -e "    [7] Monochrome Silver"
            read -rp "  Select Emblem Color [1-7, Default: 1]: " col2
            case "$col2" in
                2|original) ACC2_EMBLEM_COLOR="original" ;;
                3|blue|cyan) ACC2_EMBLEM_COLOR="blue" ;;
                4|green|emerald) ACC2_EMBLEM_COLOR="green" ;;
                5|amber|gold|orange) ACC2_EMBLEM_COLOR="amber" ;;
                6|red|ruby) ACC2_EMBLEM_COLOR="red" ;;
                7|silver|monochrome|grey) ACC2_EMBLEM_COLOR="monochrome" ;;
                *) ACC2_EMBLEM_COLOR="violet" ;;
            esac
            ACC2_RECOLOR="true"
            [ "$ACC2_EMBLEM_COLOR" = "original" ] && ACC2_RECOLOR="false"
            ;;

        *)
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "${CYAN}        Configure Antigravity Suite Icons            ${NC}"
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "Current Configuration:"
            echo -e "  • Antigravity 1:    Background: ${BOLD}${ACC1_ICON_THEME}${NC} | Emblem: ${BOLD}${ACC1_EMBLEM_COLOR}${NC}"
            echo -e "  • Antigravity IDE:  Background: ${BOLD}${IDE_ICON_THEME}${NC} | Emblem: ${BOLD}${IDE_EMBLEM_COLOR}${NC}"
            if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
                echo -e "  • Antigravity 2:    Background: ${BOLD}${ACC2_ICON_THEME}${NC} | Emblem: ${BOLD}${ACC2_EMBLEM_COLOR}${NC}"
            fi
            echo -e "${CYAN}-----------------------------------------------------${NC}"

            echo -e "\n${BOLD}[1] Configure Antigravity (Account 1):${NC}"
            read -rp "  Background Color [1: Black (default), 2: White]: " bg1
            case "$bg1" in
                2|white) ACC1_ICON_THEME="white" ;;
                *) ACC1_ICON_THEME="black" ;;
            esac

            echo -e "  Emblem Colors:"
            echo -e "    [1] Original Google Multi-Color (default)"
            echo -e "    [2] Violet / Magenta"
            echo -e "    [3] Royal Blue / Cyan"
            echo -e "    [4] Emerald Green"
            echo -e "    [5] Amber / Gold"
            echo -e "    [6] Ruby Red"
            echo -e "    [7] Monochrome Silver"
            read -rp "  Select Emblem Color [1-7, Default: 1]: " col1
            case "$col1" in
                2|violet|purple) ACC1_EMBLEM_COLOR="violet" ;;
                3|blue|cyan) ACC1_EMBLEM_COLOR="blue" ;;
                4|green|emerald) ACC1_EMBLEM_COLOR="green" ;;
                5|amber|gold|orange) ACC1_EMBLEM_COLOR="amber" ;;
                6|red|ruby) ACC1_EMBLEM_COLOR="red" ;;
                7|silver|monochrome|grey) ACC1_EMBLEM_COLOR="monochrome" ;;
                *) ACC1_EMBLEM_COLOR="original" ;;
            esac

            echo -e "\n${BOLD}[2] Configure Antigravity IDE:${NC}"
            read -rp "  Background Color [1: White (default), 2: Black]: " bgi
            case "$bgi" in
                2|black) IDE_ICON_THEME="black" ;;
                *) IDE_ICON_THEME="white" ;;
            esac

            echo -e "  Emblem Colors:"
            echo -e "    [1] Original Google Multi-Color (default)"
            echo -e "    [2] Royal Blue / Cyan"
            echo -e "    [3] Violet / Magenta"
            echo -e "    [4] Emerald Green"
            echo -e "    [5] Amber / Gold"
            echo -e "    [6] Ruby Red"
            echo -e "    [7] Monochrome Silver"
            read -rp "  Select Emblem Color [1-7, Default: 1]: " coli
            case "$coli" in
                2|blue|cyan) IDE_EMBLEM_COLOR="blue" ;;
                3|violet|purple) IDE_EMBLEM_COLOR="violet" ;;
                4|green|emerald) IDE_EMBLEM_COLOR="green" ;;
                5|amber|gold|orange) IDE_EMBLEM_COLOR="amber" ;;
                6|red|ruby) IDE_EMBLEM_COLOR="red" ;;
                7|silver|monochrome|grey) IDE_EMBLEM_COLOR="monochrome" ;;
                *) IDE_EMBLEM_COLOR="original" ;;
            esac

            if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
                echo -e "\n${BOLD}[3] Configure Antigravity (Account 2):${NC}"
                read -rp "  Background Color [1: Black (default), 2: White]: " bg2
                case "$bg2" in
                    2|white) ACC2_ICON_THEME="white" ;;
                    *) ACC2_ICON_THEME="black" ;;
                esac

                echo -e "  Emblem Colors:"
                echo -e "    [1] Violet / Magenta (default)"
                echo -e "    [2] Original Google Multi-Color"
                echo -e "    [3] Royal Blue / Cyan"
                echo -e "    [4] Emerald Green"
                echo -e "    [5] Amber / Gold"
                echo -e "    [6] Ruby Red"
                echo -e "    [7] Monochrome Silver"
                read -rp "  Select Emblem Color [1-7, Default: 1]: " col2
                case "$col2" in
                    2|original) ACC2_EMBLEM_COLOR="original" ;;
                    3|blue|cyan) ACC2_EMBLEM_COLOR="blue" ;;
                    4|green|emerald) ACC2_EMBLEM_COLOR="green" ;;
                    5|amber|gold|orange) ACC2_EMBLEM_COLOR="amber" ;;
                    6|red|ruby) ACC2_EMBLEM_COLOR="red" ;;
                    7|silver|monochrome|grey) ACC2_EMBLEM_COLOR="monochrome" ;;
                    *) ACC2_EMBLEM_COLOR="violet" ;;
                esac
                ACC2_RECOLOR="true"
                [ "$ACC2_EMBLEM_COLOR" = "original" ] && ACC2_RECOLOR="false"
            fi
            ;;
    esac

    apply_icons_config
}

# ------------------------------------------------------------------------------
# 16. Keyring & Credential Storage Management
# ------------------------------------------------------------------------------
keyring_command() {
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local TOOL=""
    if [ -f "${SCRIPT_DIR}/antigravity-keyring.py" ]; then
        TOOL="${SCRIPT_DIR}/antigravity-keyring.py"
    elif [ -f "${LOCAL_BIN}/antigravity-keyring.py" ]; then
        TOOL="${LOCAL_BIN}/antigravity-keyring.py"
    fi

    if [ -z "$TOOL" ]; then
        log_err "antigravity-keyring.py not found in ${SCRIPT_DIR} or ${LOCAL_BIN}."
        return 1
    fi

    python3 "$TOOL" "$@"
}

keyring_status() {
    keyring_command status
}

keyring_purge() {
    keyring_command purge
}

set_keyring_mode() {
    local target="${1:-all}"
    local mode="${2:-normal}"
    keyring_command set "$target" "$mode"
}

configure_keyring_interactive() {
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${CYAN}   Configure Keyring & Credential Storage Mode       ${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo "1) Switch Account 1 to Normal File Storage (Bypass GNOME Keyring)"
    echo "2) Switch Account 1 to GNOME Keyring (Secret Service)"
    echo "3) Switch Account 2 to Normal File Storage (Bypass GNOME Keyring)"
    echo "4) Switch Account 2 to GNOME Keyring (Secret Service)"
    echo "5) Switch ALL Instances to Normal File Storage (Bypass Keyring Everywhere)"
    echo "6) Switch ALL Instances to GNOME Keyring"
    echo "7) Purge Antigravity Credentials from GNOME Keyring"
    echo "8) View Detailed Keyring & Credential Status"
    echo "0) Cancel / Back"
    echo -e "${CYAN}-----------------------------------------------------${NC}"
    read -rp "Select an option [0-8]: " kchoice

    case "$kchoice" in
        1) set_keyring_mode "app1" "normal" ;;
        2) set_keyring_mode "app1" "gnome" ;;
        3) set_keyring_mode "app2" "normal" ;;
        4) set_keyring_mode "app2" "gnome" ;;
        5) set_keyring_mode "all" "normal" ;;
        6) set_keyring_mode "all" "gnome" ;;
        7) keyring_purge ;;
        8) keyring_status ;;
        0) return 0 ;;
        *)
            log_err "Invalid selection."
            ;;
    esac
}

# ------------------------------------------------------------------------------
# 17. Path Configuration & Relocation
# ------------------------------------------------------------------------------
configure_paths() {
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local DETECT_SCRIPT=""
    if [ -f "${SCRIPT_DIR}/antigravity-detect.py" ]; then
        DETECT_SCRIPT="${SCRIPT_DIR}/antigravity-detect.py"
    elif [ -f "${LOCAL_BIN}/antigravity-detect.py" ]; then
        DETECT_SCRIPT="${LOCAL_BIN}/antigravity-detect.py"
    fi

    if [ -z "$DETECT_SCRIPT" ]; then
        log_err "antigravity-detect.py not found in ${SCRIPT_DIR} or ${LOCAL_BIN}."
        return 1
    fi

    python3 "$DETECT_SCRIPT" --configure-paths

    if [ -f "$PATHS_CONF" ]; then
        # shellcheck source=/dev/null
        source "$PATHS_CONF"
    fi

    if [ -t 0 ]; then
        read -rp "Would you like to re-generate desktop shortcuts/launchers with updated paths now? [Y/n] " regen_ans
        regen_ans="${regen_ans:-Y}"
        if [[ "$regen_ans" =~ ^[Yy]$ ]]; then
            setup_account_1
            if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
                setup_account_2
            fi
            setup_ide_shortcuts
            log_success "Updated desktop launchers with new installation paths."
        fi
    fi
}

handle_paths_command() {
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local DETECT_SCRIPT=""
    [ -f "${SCRIPT_DIR}/antigravity-detect.py" ] && DETECT_SCRIPT="${SCRIPT_DIR}/antigravity-detect.py"
    [ -z "$DETECT_SCRIPT" ] && [ -f "${LOCAL_BIN}/antigravity-detect.py" ] && DETECT_SCRIPT="${LOCAL_BIN}/antigravity-detect.py"
    if [ ${#CMD_ARGS[@]} -gt 0 ]; then
        python3 "$DETECT_SCRIPT" "${CMD_ARGS[@]}"
        [ -f "$PATHS_CONF" ] && source "$PATHS_CONF"
    else
        configure_paths
    fi
}

handle_wizard_command() {
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local INSTALLER=""
    [ -f "${SCRIPT_DIR}/../install.sh" ] && INSTALLER="${SCRIPT_DIR}/../install.sh"
    [ -f "${SCRIPT_DIR}/install.sh" ] && INSTALLER="${SCRIPT_DIR}/install.sh"
    [ -f "${REAL_HOME}/PhpstormProjects/antigravity-suite-manager/install.sh" ] && INSTALLER="${REAL_HOME}/PhpstormProjects/antigravity-suite-manager/install.sh"
    if [ -n "$INSTALLER" ]; then
        exec "$INSTALLER" "${CMD_ARGS[@]}"
    else
        log_err "install.sh not found."
    fi
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
  detect        Scan and identify all installed Antigravity instances on system (aliases: scan, find)
  install       Install Antigravity suite [all|app|ide] (default: all; aliases: install-all, install-app, install-ide)
  all           Install / update both Antigravity Apps (Account 1 & 2), IDE, F5 patch, and RTL
  app           Install / update Antigravity App (Both Accounts, RTL, and F5)
  ide           Install / update Antigravity IDE and RTL patch
  app1          Configure Account 1 launcher and desktop shortcut
  app2          Configure Account 2 isolated profile, shared history, and shortcuts
  ide-shortcuts Configure Antigravity IDE launcher and desktop shortcut
  set-icons     Configure or re-apply icons (Black/White and Acc 2 Recolor)
  merge-history Sync & backfill conversation history across all profiles/IDEs (alias: merge)
  keyring       Configure & switch credential storage (GNOME Keyring vs Normal File Storage)
                Subcommands: status | set [app1|app2|ide|all] [normal|gnome] | purge
                Aliases: set-keyring, switch-keyring, toggle-keyring
  paths         Configure & switch Antigravity installation paths (interactive or CLI)
                Aliases: set-paths
  wizard        Launch the interactive step-by-step setup wizard (alias: setup)
  create-instance Create arbitrary App or IDE instances with shared/isolated history (alias: add)
  list-instances  Show all created App and IDE instances and their history status (alias: list)
  set-history     Toggle instance history between 'shared' and 'isolated'
  remove-instance Delete an App or IDE instance and archive its profile (alias: remove)
  f5            Re-apply manual F5 backend reload sync patch
  rtl           Apply / re-apply antigravity-rtl to App and IDE
  update-rtl    Update antigravity-rtl to latest and re-apply
  update        Smart update: checks versions, downloads to /tmp/antigravity-cache, skips if up-to-date
  export-history Export conversation history & brains to portable tarball [out]
  import-history Import & merge conversation history from archive <file>
  export-suite  Export suite configurations (rules, skills, plugins, MCP, accounts) [out]
  import-suite  Import & merge suite configurations from archive <file>
  export-all    Export full unified migration bundle (History + Configs) [out]
  import-all    Auto-detect & import any Antigravity archive <file>
  backups       Manage safety backups (list | create [--label <name>] | restore <file>)
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
  $(basename "$0") paths
  $(basename "$0") wizard
  $(basename "$0") keyring status
  $(basename "$0") keyring set app1 normal
  $(basename "$0") keyring purge
  $(basename "$0") detect
  $(basename "$0") install
  $(basename "$0") update
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
    echo "1) Install Antigravity Suite (App + IDE + RTL + F5)"
    echo "2) Smart Update All (App 1, App 2, IDE, RTL, F5) [Uses /tmp cache]"
    echo "3) Install / Update Antigravity App (Both Accounts)"
    echo "4) Install / Update Antigravity IDE"
    echo "5) Detect & Scan Installed Antigravity Instances"
    echo "6) Check Versions, Cache & Patch Statuses (Status Table)"
    echo "7) Configure / Repair Account 2 (Isolated Profile & Shared History)"
    echo "8) Apply / Update RTL Patcher (mmnaderi/antigravity-rtl)"
    echo "9) Re-apply F5 Manual Sync Backend Reload Patch"
    echo "10) Configure Icons & Appearance Themes"
    echo "11) Merge & Sync Conversation History (All Profiles & IDEs)"
    echo "12) Create New Instance (App or IDE with Shared/Isolated History)"
    echo "13) List All Instances & History Statuses"
    echo "14) Set / Toggle Instance History Mode (Shared vs Isolated)"
    echo "15) Configure / Switch Keyring Mode (GNOME Keyring vs Normal File Storage)"
    echo "16) Configure / Switch Antigravity Installation Paths & Targets"
    echo "17) Antigravity Control Center & Step-by-Step Setup Wizard"
    echo "18) Remove an Instance"
    echo "19) Force Full Re-download & Reinstall Everything (--force)"
    echo "20) Clean Download Cache (/tmp/antigravity-cache)"
    echo "21) Export Suite or History Archive (Cross-System Migration)"
    echo "22) Import Suite or History Archive (Cross-System Restore/Merge)"
    echo "23) Manage Backups & Snapshots (List, Create, Restore)"
    echo "0) Exit"
    echo -e "${CYAN}-----------------------------------------------------${NC}"
    read -rp "Select an option [0-23]: " choice

    case "$choice" in
        1) install_antigravity_all ;;
        2) update_all ;;
        3) install_antigravity_app ;;
        4) install_antigravity_ide ;;
        5) detect_installations ;;
        6) resolve_dynamic_urls && check_status ;;
        7) setup_account_2 ;;
        8) update_rtl ;;
        9) patch_f5_reload ;;
        10) configure_icons_interactive ;;
        11) merge_history ;;
        12) create_instance ;;
        13) list_instances ;;
        14)
            read -rp "Enter instance type [app/ide]: " stype
            read -rp "Enter instance id/name: " sid
            read -rp "Enter mode [shared/isolated]: " smode
            set_history_mode "$stype" "$sid" "$smode"
            ;;
        15) configure_keyring_interactive ;;
        16) configure_paths ;;
        17)
            local SCRIPT_DIR
            SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
            local INSTALLER=""
            [ -f "${SCRIPT_DIR}/../install.sh" ] && INSTALLER="${SCRIPT_DIR}/../install.sh"
            [ -f "${SCRIPT_DIR}/install.sh" ] && INSTALLER="${SCRIPT_DIR}/install.sh"
            [ -f "${REAL_HOME}/PhpstormProjects/antigravity-suite-manager/install.sh" ] && INSTALLER="${REAL_HOME}/PhpstormProjects/antigravity-suite-manager/install.sh"
            if [ -n "$INSTALLER" ]; then
                exec "$INSTALLER"
            else
                log_err "install.sh not found."
            fi
            ;;
        18)
            read -rp "Enter instance type [app/ide]: " rtype
            read -rp "Enter instance id/name: " rid
            remove_instance "$rtype" "$rid"
            ;;
        19) FORCE_INSTALL=true install_antigravity_all ;;
        20) clean_cache ;;
        21)
            echo -e "\nSelect Export Category:"
            echo "1) Full Bundle (History + Suite Configs, Skills, Rules, MCP, Accounts)"
            echo "2) Conversation History Only (Chats, Brain, Summaries)"
            echo "3) Suite Configurations Only (Rules, Skills, Plugins, MCP, Accounts)"
            read -rp "Choose [1-3, Default: 1]: " ecat
            read -rp "Enter output destination path [Enter for default]: " edest
            case "$ecat" in
                2) export_history ${edest:+"$edest"} ;;
                3) export_suite ${edest:+"$edest"} ;;
                *) export_all ${edest:+"$edest"} ;;
            esac
            ;;
        22)
            read -rp "Enter path to archive (.tar.gz) to import: " iarc
            if [ -n "$iarc" ]; then
                import_all "$iarc"
            else
                log_err "No archive path provided."
            fi
            ;;
        23)
            echo -e "\nManage Backups:"
            echo "1) List Available Snapshots"
            echo "2) Create Instant Snapshot"
            echo "3) Restore From Snapshot"
            read -rp "Choose [1-3, Default: 1]: " bcat
            case "$bcat" in
                2)
                    read -rp "Enter snapshot label [default: manual]: " blbl
                    manage_backups create --label "${blbl:-manual}"
                    ;;
                3)
                    read -rp "Enter path to backup archive (.tar.gz): " barc
                    manage_backups restore "$barc"
                    ;;
                *)
                    manage_backups list
                    ;;
            esac
            ;;
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
CMD_ARGS=()

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
        merge-history|merge)
            COMMAND="merge-history"
            shift
            ;;
        export-history|export-chats)
            COMMAND="export-history"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        import-history|import-chats)
            COMMAND="import-history"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        export-suite|export-config)
            COMMAND="export-suite"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        import-suite|import-config)
            COMMAND="import-suite"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        export-all|export)
            COMMAND="export-all"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        import-all|import)
            COMMAND="import-all"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        backups|backup)
            COMMAND="backups"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        create-instance|add-instance|add-profile|create-profile|add)
            COMMAND="create-instance"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        list-instances|list-profiles|list)
            COMMAND="list-instances"
            shift
            ;;
        set-history|toggle-history)
            COMMAND="set-history"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        remove-instance|delete-instance|remove)
            COMMAND="remove-instance"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        detect|scan|find|find-installations)
            COMMAND="detect"
            shift
            ;;
        install)
            COMMAND="install"
            shift
            if [ -n "$1" ] && [[ "$1" != -* ]]; then
                SUB_COMMAND="$1"
                shift
            fi
            ;;
        install-all)
            COMMAND="install"
            SUB_COMMAND="all"
            shift
            ;;
        install-app)
            COMMAND="install"
            SUB_COMMAND="app"
            shift
            ;;
        install-ide)
            COMMAND="install"
            SUB_COMMAND="ide"
            shift
            ;;
        set-keyring|keyring|switch-keyring|toggle-keyring)
            COMMAND="keyring"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        paths|set-paths)
            COMMAND="paths"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        wizard|setup|center|control-center)
            COMMAND="wizard"
            shift
            CMD_ARGS=("$@")
            break
            ;;
        rtl|patch-rtl)
            COMMAND="rtl"
            shift
            if [ -n "$1" ] && [[ "$1" != -* ]]; then
                SUB_COMMAND="$1"
                shift
            fi
            ;;
        f5|patch-f5)
            COMMAND="f5"
            shift
            ;;
        set-icons|icons)
            COMMAND="set-icons"
            shift
            if [ -n "$1" ] && [[ "$1" != -* ]]; then
                SUB_COMMAND="$1"
                shift
            fi
            ;;
        status|all|app|ide|app1|app2|ide-shortcuts|update-rtl|update|clean-cache|help)
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
        detect)
            auto_detect_installations
            detect_installations
            ;;
        install)
            auto_detect_installations
            case "${SUB_COMMAND:-all}" in
                app)
                    install_antigravity_app
                    ;;
                ide)
                    install_antigravity_ide
                    ;;
                all|*)
                    install_antigravity_all
                    ;;
            esac
            ;;
        keyring)
            if [ ${#CMD_ARGS[@]} -eq 0 ]; then
                configure_keyring_interactive
            else
                case "${CMD_ARGS[0]}" in
                    status)
                        keyring_status
                        ;;
                    purge|clean)
                        keyring_purge
                        ;;
                    set)
                        keyring_command "${CMD_ARGS[@]}"
                        ;;
                    *)
                        if [ ${#CMD_ARGS[@]} -ge 2 ]; then
                            keyring_command set "${CMD_ARGS[0]}" "${CMD_ARGS[1]}"
                        else
                            keyring_command "${CMD_ARGS[@]}"
                        fi
                        ;;
                esac
            fi
            ;;
        paths)
            handle_paths_command
            ;;
        wizard|setup|center|control-center)
            handle_wizard_command
            ;;
        status)
            resolve_dynamic_urls
            check_status
            ;;
        all)
            install_antigravity_all
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
                configure_icons_interactive "$SUB_COMMAND"
            fi
            ;;
        merge-history)
            merge_history
            ;;
        export-history|export-chats)
            export_history "${CMD_ARGS[@]}"
            ;;
        import-history|import-chats)
            import_history "${CMD_ARGS[@]}"
            ;;
        export-suite|export-config)
            export_suite "${CMD_ARGS[@]}"
            ;;
        import-suite|import-config)
            import_suite "${CMD_ARGS[@]}"
            ;;
        export-all|export)
            export_all "${CMD_ARGS[@]}"
            ;;
        import-all|import)
            import_all "${CMD_ARGS[@]}"
            ;;
        backups|backup)
            manage_backups "${CMD_ARGS[@]}"
            ;;
        create-instance)
            create_instance "${CMD_ARGS[@]}"
            ;;
        list-instances)
            list_instances
            ;;
        set-history)
            set_history_mode "${CMD_ARGS[@]}"
            ;;
        remove-instance)
            remove_instance "${CMD_ARGS[@]}"
            ;;
        f5|patch-f5)
            patch_f5_reload
            ;;
        rtl|patch-rtl)
            auto_detect_installations
            case "${SUB_COMMAND:-all}" in
                app)
                    patch_rtl_app
                    patch_f5_reload
                    ;;
                ide)
                    patch_rtl_ide
                    ;;
                all|*)
                    patch_rtl_all
                    ;;
            esac
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
