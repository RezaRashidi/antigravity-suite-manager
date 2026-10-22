#!/usr/bin/env bash
# Antigravity Account Selector Patcher (App & IDE)

ensure_selector_dirs() {
    auto_detect_installations 2>/dev/null || true
    if [ -z "$APP_INSTALL_DIR" ] || [ ! -f "${APP_INSTALL_DIR}/resources/app.asar" ]; then
        for c in "$APP_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_APP" "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity"; do
            [ -n "$c" ] && [ -f "${c}/resources/app.asar" ] && { APP_INSTALL_DIR="$c"; break; }
        done
    fi
    if [ -z "$IDE_INSTALL_DIR" ] || [ ! -d "${IDE_INSTALL_DIR}/resources/app/out" ]; then
        for c in "$IDE_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_IDE" "/opt/antigravity-ide" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity-ide"; do
            [ -n "$c" ] && [ -d "${c}/resources/app/out" ] && { IDE_INSTALL_DIR="$c"; break; }
        done
    fi
}

get_selector_patch_js() {
    local s_dir; s_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
    local cand
    for cand in \
        "${LOCAL_BIN}/antigravity-selector-patch.js" \
        "${s_dir}/antigravity-selector-patch.js" \
        "${s_dir}/bin/antigravity-selector-patch.js" \
        "${SCRIPT_DIR}/antigravity-selector-patch.js" \
        "${SCRIPT_DIR}/bin/antigravity-selector-patch.js" \
        "${REAL_HOME}/antigravity-suite-manager/bin/antigravity-selector-patch.js" \
        "${REAL_HOME}/PhpstormProjects/antigravity-suite-manager/bin/antigravity-selector-patch.js" \
        "/usr/local/bin/antigravity-selector-patch.js"; do
        if [ -f "$cand" ]; then
            if [ ! -f "${LOCAL_BIN}/antigravity-selector-patch.js" ]; then
                mkdir -p "${LOCAL_BIN}"
                cp -f "$cand" "${LOCAL_BIN}/antigravity-selector-patch.js" 2>/dev/null || true
                chmod +x "${LOCAL_BIN}/antigravity-selector-patch.js" 2>/dev/null || true
            fi
            local cand_dir; cand_dir="$(dirname "$cand")"
            if [ -d "${cand_dir}/lib/patch" ] && [ ! -d "${LOCAL_BIN}/lib/patch" ]; then
                mkdir -p "${LOCAL_BIN}/lib"
                cp -rf "${cand_dir}/lib/patch" "${LOCAL_BIN}/lib/" 2>/dev/null || true
            fi
            echo "$cand"
            return 0
        fi
    done

    if declare -f find_suite_repo_root >/dev/null 2>&1; then
        local r_dir; r_dir=$(find_suite_repo_root 2>/dev/null || true)
        if [ -n "$r_dir" ] && [ -f "${r_dir}/bin/antigravity-selector-patch.js" ]; then
            cand="${r_dir}/bin/antigravity-selector-patch.js"
            mkdir -p "${LOCAL_BIN}"
            cp -f "$cand" "${LOCAL_BIN}/antigravity-selector-patch.js" 2>/dev/null || true
            chmod +x "${LOCAL_BIN}/antigravity-selector-patch.js" 2>/dev/null || true
            if [ -d "${r_dir}/bin/lib/patch" ] && [ ! -d "${LOCAL_BIN}/lib/patch" ]; then
                mkdir -p "${LOCAL_BIN}/lib"
                cp -rf "${r_dir}/bin/lib/patch" "${LOCAL_BIN}/lib/" 2>/dev/null || true
            fi
            echo "$cand"
            return 0
        fi
    fi
}

sync_selector_skills() {
    local r_dir; r_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    for base in "${REAL_HOME:-$HOME}/.gemini" "${REAL_HOME:-$HOME}/.gemide"; do
        mkdir -p "${base}/config/skills" 2>/dev/null || true
        for sk in whoami accounts switch; do
            [ -d "${r_dir}/skills/${sk}" ] && cp -rf "${r_dir}/skills/${sk}" "${base}/config/skills/" 2>/dev/null || true
        done
    done
}

ensure_keyring_decoupled() {
    log_info "Ensuring keyring storage mode is decoupled (Normal File Storage)..."
    local s_dir; s_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
    if declare -f set_keyring_mode >/dev/null 2>&1; then
        set_keyring_mode "all" "normal" >/dev/null 2>&1 || true
    elif declare -f keyring_command >/dev/null 2>&1; then
        keyring_command set all normal >/dev/null 2>&1 || true
    elif [ -f "${s_dir}/bin/antigravity-keyring.py" ]; then
        python3 "${s_dir}/bin/antigravity-keyring.py" set all normal >/dev/null 2>&1 || true
    elif [ -f "${LOCAL_BIN}/antigravity-keyring.py" ]; then
        python3 "${LOCAL_BIN}/antigravity-keyring.py" set all normal >/dev/null 2>&1 || true
    fi

    for c_dir in "${REAL_HOME:-$HOME}/.gemini/cache" "${REAL_HOME:-$HOME}/.gemide/cache" "${REAL_HOME:-$HOME}/.gemini/antigravity-ide/cache"; do
        mkdir -p "$c_dir" 2>/dev/null || true
        touch "${c_dir}/antigravity-keyring-unavailable" 2>/dev/null || true
    done

    if [ ! -f "${REAL_HOME:-$HOME}/.gemini/jetski-standalone-oauth-token" ]; then
        python3 -c "from antigravity_suite.auth.keyring_apply import apply_mode_for_app1; apply_mode_for_app1('normal', migrate_token=True)" 2>/dev/null || true
    fi
}

patch_selector_app() {
    ensure_selector_dirs
    ensure_keyring_decoupled
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    local p_js; p_js="$(get_selector_patch_js)"

    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}. Skipping App selector patch."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-selector-patch.js not found."
        return 1
    fi

    if [ "$FORCE_INSTALL" != true ] && grep -qa "ANTIGRAVITY_SUITE_SELECTOR_PATCH_V1" "$asar"; then
        log_info "Account selector already applied to app.asar (${APP_INSTALL_DIR})."
        return 0
    fi
    log_info "Applying account selector to Antigravity App at ${APP_INSTALL_DIR}..."
    fix_permissions "$APP_INSTALL_DIR"

    local orig="${asar}.orig"
    [ ! -f "$orig" ] && cp -p "$asar" "$orig"

    local tmp; tmp=$(mktemp -d /tmp/asar_patch_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    if ! node "$p_js" --app "$tmp/unpacked"; then
        log_err "Selector patch script failed for App."
        rm -rf "$tmp"
        return 1
    fi

    if ! run_asar pack "$tmp/unpacked" "$tmp/app.asar.patched" --unpack "*.node"; then
        log_err "Failed to pack patched app.asar."
        rm -rf "$tmp"
        return 1
    fi

    cp "$tmp/app.asar.patched" "$asar"
    rm -rf "$tmp"
    sync_selector_skills
    log_success "Account selector applied to Antigravity App (${APP_INSTALL_DIR})."
}

unpatch_selector_app() {
    ensure_selector_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    local p_js; p_js="$(get_selector_patch_js)"

    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-selector-patch.js not found."
        return 1
    fi

    log_info "Removing account selector from Antigravity App at ${APP_INSTALL_DIR}..."
    fix_permissions "$APP_INSTALL_DIR"

    local tmp; tmp=$(mktemp -d /tmp/asar_patch_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    if ! node "$p_js" --app --unpatch "$tmp/unpacked"; then
        log_err "Selector unpatch script failed for App."
        rm -rf "$tmp"
        return 1
    fi

    if ! run_asar pack "$tmp/unpacked" "$tmp/app.asar.patched" --unpack "*.node"; then
        log_err "Failed to pack unpatched app.asar."
        rm -rf "$tmp"
        return 1
    fi

    cp "$tmp/app.asar.patched" "$asar"
    rm -rf "$tmp"
    log_success "Account selector removed from Antigravity App (${APP_INSTALL_DIR})."
}

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
                if [ "$cand" != "$ls_bin" ]; then
                    cp -p "$cand" "$ls_bin"
                    chmod 755 "$ls_bin"
                fi
                if [ ! -f "$ls_orig" ]; then
                    cp -p "$cand" "$ls_orig"
                    chmod 755 "$ls_orig"
                fi
                break
            fi
        fi
    done

    if [ "$is_elf" -eq 1 ]; then
        return 0
    fi

    log_warn "Language server binary appears corrupted or missing in ${bin_dir}."
    log_info "Attempting automatic recovery of language_server_linux_x64 from archives..."

    local recovered=0
    local cand_archives=()
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
        if declare -f resolve_dynamic_urls >/dev/null 2>&1; then
            resolve_dynamic_urls
        fi
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

patch_selector_ide() {
    ensure_selector_dirs
    ensure_keyring_decoupled
    local ide="${IDE_INSTALL_DIR}"
    local p_js; p_js="$(get_selector_patch_js)"

    if [ ! -d "$ide" ]; then
        log_warn "Antigravity IDE directory not found at ${ide:-'<undefined>'}. Skipping IDE selector patch."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-selector-patch.js not found."
        return 1
    fi

    local marker="${ide}/resources/app/out/antigravity_ide_selector_patch.marker"
    if [ "$FORCE_INSTALL" != true ] && [ -f "$marker" ]; then
        log_info "Account selector already applied to IDE (${ide})."
        return 0
    fi
    log_info "Applying account selector to Antigravity IDE at ${ide}..."
    fix_permissions "$ide"
    check_and_prep_ide_ls "$ide"
    if ! node "$p_js" --ide "$ide"; then
        log_err "Selector patch script failed for IDE."
        return 1
    fi
    sync_selector_skills
    fix_ide_checksums "$ide"
    log_success "Account selector applied to Antigravity IDE (${ide})."
}

unpatch_selector_ide() {
    ensure_selector_dirs
    local ide="${IDE_INSTALL_DIR}"
    local p_js; p_js="$(get_selector_patch_js)"

    if [ ! -d "$ide" ]; then
        log_warn "Antigravity IDE directory not found at ${ide:-'<undefined>'}."
        return 1
    fi
    if [ -z "$p_js" ] || [ ! -f "$p_js" ]; then
        log_err "antigravity-selector-patch.js not found."
        return 1
    fi

    log_info "Removing account selector from Antigravity IDE at ${ide}..."
    fix_permissions "$ide"
    check_and_prep_ide_ls "$ide"
    if ! node "$p_js" --ide --unpatch "$ide"; then
        log_err "Selector unpatch script failed for IDE."
        return 1
    fi
    fix_ide_checksums "$ide"
    log_success "Account selector removed from Antigravity IDE (${ide})."
}

patch_selector() {
    ensure_keyring_decoupled
    for arg in "$@"; do [ "$arg" = "--force" ] || [ "$arg" = "-f" ] && FORCE_INSTALL=true; done
    case "${SUB_COMMAND:-${1:-all}}" in
        app) patch_selector_app "$@" ;;
        ide) patch_selector_ide "$@" ;;
        all|*)
            local err=0
            patch_selector_app "$@" || err=1
            patch_selector_ide "$@" || err=1
            return $err
            ;;
    esac
}

unpatch_selector() {
    case "${SUB_COMMAND:-${1:-all}}" in
        app) unpatch_selector_app "$@" ;;
        ide) unpatch_selector_ide "$@" ;;
        all|*)
            local err=0
            unpatch_selector_app "$@" || err=1
            unpatch_selector_ide "$@" || err=1
            return $err
            ;;
    esac
}
