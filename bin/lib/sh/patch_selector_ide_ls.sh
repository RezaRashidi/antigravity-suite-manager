#!/usr/bin/env bash
# Language server binary validation and archive recovery helper for IDE selector

check_and_prep_ide_ls() {
    local ide_dir="$1"
    local bin_dir="${ide_dir}/resources/app/extensions/antigravity/bin"
    [ ! -d "$bin_dir" ] && return 0

    local ls_path="${bin_dir}/language_server_linux_x64"
    local ls_bin="${bin_dir}/language_server_linux_x64.bin"
    local ls_orig="${bin_dir}/language_server_linux_x64.bin.orig"

    local is_elf=0
    for cand in "$ls_bin" "$ls_orig" "$ls_path" "${APP_INSTALL_DIR}/resources/bin/language_server" "/opt/Antigravity-x64/resources/bin/language_server" "/opt/antigravity2/resources/bin/language_server"; do
        if [ -f "$cand" ]; then
            if file -b "$cand" 2>/dev/null | grep -q "ELF" && ("$cand" --help >/dev/null 2>&1 || [ $? -ne 126 ]); then
                is_elf=1
                [ "$cand" != "$ls_bin" ] && cp -p "$cand" "$ls_bin" && chmod 755 "$ls_bin"
                [ ! -f "$ls_orig" ] && cp -p "$cand" "$ls_orig" && chmod 755 "$ls_orig"
                break
            fi
        fi
    done

    [ "$is_elf" -eq 1 ] && return 0

    log_warn "Language server binary appears corrupted or missing in ${bin_dir}."
    log_info "Attempting automatic recovery of language_server_linux_x64 from archives..."

    local recovered=0 cand_archives=()
    [ -d "${CACHE_DIR:-/tmp/antigravity-cache}" ] && while IFS= read -r f; do [ -n "$f" ] && cand_archives+=("$f"); done < <(find "${CACHE_DIR:-/tmp/antigravity-cache}" -type f \( -name "*Antigravity-IDE*.tar.gz" -o -name "*antigravity*.tar.gz" \) 2>/dev/null || true)
    while IFS= read -r f; do [ -n "$f" ] && cand_archives+=("$f"); done < <(find /tmp -maxdepth 2 -type f -name "*Antigravity-IDE*.tar.gz" 2>/dev/null || true)

    for arch in "${cand_archives[@]}"; do
        if [ -f "$arch" ]; then
            local in_arch; in_arch=$(tar -ztf "$arch" 2>/dev/null | grep -m1 "bin/language_server_linux_x64$" || true)
            if [ -n "$in_arch" ]; then
                log_info "Extracting language_server_linux_x64 from ${arch}..."
                local tmp_rec; tmp_rec=$(mktemp -d /tmp/ls_recover_XXXXXX)
                if tar -zxf "$arch" -C "$tmp_rec" "$in_arch" 2>/dev/null; then
                    if [ -f "${tmp_rec}/${in_arch}" ]; then
                        cp -f "${tmp_rec}/${in_arch}" "$ls_bin"
                        cp -f "${tmp_rec}/${in_arch}" "$ls_orig"
                        chmod 755 "$ls_bin" "$ls_orig"
                        recovered=1
                        rm -rf "$tmp_rec"
                        break
                    fi
                fi
                rm -rf "$tmp_rec"
            fi
        fi
    done

    if [ "$recovered" -eq 0 ]; then
        log_info "Downloading Antigravity IDE archive to restore language_server_linux_x64..."
        declare -f resolve_dynamic_urls >/dev/null 2>&1 && resolve_dynamic_urls
        if [ -n "$IDE_URL" ] && [ -n "$TARGET_IDE_VER" ]; then
            local arch; arch=$(get_or_download_package "Antigravity-IDE" "$IDE_URL" "$TARGET_IDE_VER" | tail -n1 | tr -d '\r\n')
            if [ -f "$arch" ]; then
                local in_arch; in_arch=$(tar -ztf "$arch" 2>/dev/null | grep -m1 "bin/language_server_linux_x64$" || true)
                if [ -n "$in_arch" ]; then
                    local tmp_rec; tmp_rec=$(mktemp -d /tmp/ls_recover_XXXXXX)
                    if tar -zxf "$arch" -C "$tmp_rec" "$in_arch" 2>/dev/null; then
                        cp -f "${tmp_rec}/${in_arch}" "$ls_bin"
                        cp -f "${tmp_rec}/${in_arch}" "$ls_orig"
                        chmod 755 "$ls_bin" "$ls_orig"
                        recovered=1
                    fi
                    rm -rf "$tmp_rec"
                fi
            fi
        fi
    fi

    if [ "$recovered" -eq 1 ]; then
        log_success "Language server binary recovered successfully."
        return 0
    else
        log_warn "Could not automatically restore language_server_linux_x64."
        return 1
    fi
}
