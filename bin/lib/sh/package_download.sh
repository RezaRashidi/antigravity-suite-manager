#!/usr/bin/env bash
# Package downloading, caching, and filesystem permissions helpers.

fix_permissions() {
    local target_dir="$1"
    [ ! -d "$target_dir" ] && return
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
