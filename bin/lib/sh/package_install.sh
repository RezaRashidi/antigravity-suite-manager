#!/usr/bin/env bash
# Binary extraction and installation with version-guard checks.

get_installed_version() {
    local name="$1"
    local target_dir="$2"
    if [ "$name" = "Antigravity-App" ]; then
        python3 -c "
import struct, json, os, re
asar = os.path.join('${target_dir}', 'resources', 'app.asar')
if os.path.isfile(asar):
    try:
        with open(asar, 'rb') as f:
            magic, h_s, h_o, j_len = struct.unpack('<IIII', f.read(16))
            hdr = json.loads(f.read(j_len).decode('utf-8'))
            curr = hdr.get('files', {}).get('package.json', {})
            f.seek(8 + h_s + int(curr['offset']))
            raw = f.read(int(curr['size'])).decode('utf-8', errors='ignore')
            try:
                pkg = json.loads(raw)
                if 'version' in pkg: print(pkg['version'])
            except Exception:
                m = re.search(r'\"version\"\s*:\s*\"([^\"]+)\"', raw)
                if m: print(m.group(1))
    except Exception: pass
" 2>/dev/null || true
    elif [ "$name" = "Antigravity-IDE" ]; then
        python3 -c "
import json, os
p = os.path.join('${target_dir}', 'resources', 'app', 'product.json')
if os.path.isfile(p):
    try:
        with open(p, 'r') as f:
            d = json.load(f)
            print(d.get('ideVersion') or d.get('version') or '')
    except Exception: pass
" 2>/dev/null || true
    fi
}

install_binary() {
    local name="$1"
    local url="$2"
    local ver="$3"
    local target_dir="$4"

    local current_installed
    current_installed=$(get_installed_version "$name" "$target_dir")

    if [ "$FORCE_INSTALL" != true ] && [ -n "$current_installed" ] && [ "$current_installed" != "None" ]; then
        highest_ver=$(printf '%s\n%s\n' "$current_installed" "$ver" | sort -V 2>/dev/null | tail -n 1)
        if [ "$highest_ver" = "$current_installed" ]; then
            log_success "${name} is already at or newer than target version (installed: v${current_installed}, target: v${ver}). Skipping binary extraction."
            log_info "(Use --force to force re-download and re-installation)"
            return 0
        fi
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

    if [ -f "$target_dir/resources/app.asar" ]; then
        cp "$target_dir/resources/app.asar" "${REAL_HOME}/.antigravity-${name}-app.asar.bak" 2>/dev/null || sudo cp "$target_dir/resources/app.asar" "${REAL_HOME}/.antigravity-${name}-app.asar.bak" || true
    fi

    log_info "Extracting ${name} into ${target_dir}..."
    if [ "$EUID" -eq 0 ] || [ -w "$target_dir" ]; then
        tar -zxf "$archive_path" --no-same-owner --strip-components=1 -C "$target_dir"
    else
        sudo tar -zxf "$archive_path" --no-same-owner --strip-components=1 -C "$target_dir"
    fi

    fix_permissions "$target_dir"
    log_success "${name} v${ver} extracted successfully in ${target_dir}"
}
