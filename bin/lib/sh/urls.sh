#!/usr/bin/env bash
# Dynamic release URL and version discovery from Google endpoints.

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
    return "", ""

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
    return "", ""

app_ver, app_url = get_app()
ide_ver, ide_url = get_ide()
print(f"{app_ver}|{app_url}|{ide_ver}|{ide_url}")
PYEOF
)

    IFS='|' read -r disc_app_ver disc_app_url disc_ide_ver disc_ide_url <<< "$py_resolver"

    if [ -n "$disc_app_url" ]; then
        if [ -z "$APP_URL" ]; then
            APP_URL="$disc_app_url"
            TARGET_APP_VER="$disc_app_ver"
        else
            TARGET_APP_VER=$(echo "$APP_URL" | grep -o -E '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1 || echo "Custom")
        fi
    else
        log_warn "Could not reach Google App discovery endpoint (offline or changed). Skipping auto-resolution."
    fi

    if [ -n "$disc_ide_url" ]; then
        if [ -z "$IDE_URL" ]; then
            IDE_URL="$disc_ide_url"
            TARGET_IDE_VER="$disc_ide_ver"
        else
            TARGET_IDE_VER=$(echo "$IDE_URL" | grep -o -E '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1 || echo "Custom")
        fi
    else
        log_warn "Could not reach Google IDE discovery endpoint (offline or changed). Skipping auto-resolution."
    fi

    if [ -n "$TARGET_APP_VER" ] || [ -n "$TARGET_IDE_VER" ]; then
        log_success "Discovered Latest: App ${TARGET_APP_VER:+v}${TARGET_APP_VER:-Unknown} | IDE ${TARGET_IDE_VER:+v}${TARGET_IDE_VER:-Unknown}"
    fi
}
