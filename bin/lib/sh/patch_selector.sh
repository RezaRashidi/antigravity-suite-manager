#!/usr/bin/env bash
# Antigravity Account Selector Patcher (App & IDE)

ensure_selector_dirs() {
    auto_detect_installations 2>/dev/null || true
    for c in "$APP_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_APP" "/opt/antigravity2" "/opt/antigravity"; do
        [ -n "$c" ] && [ -f "${c}/resources/app.asar" ] && { APP_INSTALL_DIR="$c"; break; }
    done
    for c in "$IDE_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_IDE" "/opt/antigravity" "/opt/antigravity-ide"; do
        [ -n "$c" ] && [ -d "${c}/resources/app/out" ] && { IDE_INSTALL_DIR="$c"; break; }
    done
}

get_selector_patch_js() {
    local base="${SCRIPT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
    for cand in "${base}/bin/antigravity-selector-patch.js" "${LOCAL_BIN}/antigravity-selector-patch.js"; do
        [ -f "$cand" ] && { echo "$cand"; return 0; }
    done
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

patch_selector_app() {
    ensure_selector_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar" p_js; p_js="$(get_selector_patch_js)"
    [ ! -f "$asar" ] || [ -z "$p_js" ] && return 0
    if [ "$FORCE_INSTALL" != true ] && grep -qa "ANTIGRAVITY_SUITE_SELECTOR_PATCH_V1" "$asar"; then
        log_info "Account selector already applied to app.asar."; return 0
    fi
    log_info "Applying account selector to Antigravity App..."; fix_permissions "$APP_INSTALL_DIR"
    local orig="${asar}.orig"; [ ! -f "$orig" ] && cp -p "$asar" "$orig"
    local tmp; tmp=$(mktemp -d /tmp/asar_patch_XXXXXX)
    npx --yes asar extract "$asar" "$tmp/unpacked" && node "$p_js" --app "$tmp/unpacked" && \
    npx --yes asar pack "$tmp/unpacked" "$tmp/app.asar.patched" --unpack "*.node" && \
    cp "$tmp/app.asar.patched" "$asar"; rm -rf "$tmp"
    sync_selector_skills; log_success "Account selector applied to App."
}

unpatch_selector_app() {
    ensure_selector_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar" p_js; p_js="$(get_selector_patch_js)"
    [ ! -f "$asar" ] || [ -z "$p_js" ] && return 0
    log_info "Removing account selector from App..."; fix_permissions "$APP_INSTALL_DIR"
    local tmp; tmp=$(mktemp -d /tmp/asar_patch_XXXXXX)
    npx --yes asar extract "$asar" "$tmp/unpacked" && node "$p_js" --app --unpatch "$tmp/unpacked" && \
    npx --yes asar pack "$tmp/unpacked" "$tmp/app.asar.patched" --unpack "*.node" && \
    cp "$tmp/app.asar.patched" "$asar"; rm -rf "$tmp"; log_success "App selector unpatched."
}

patch_selector_ide() {
    ensure_selector_dirs
    local ide="${IDE_INSTALL_DIR}" p_js; p_js="$(get_selector_patch_js)"
    [ ! -d "$ide" ] || [ -z "$p_js" ] && return 0
    local marker="${ide}/resources/app/out/antigravity_ide_selector_patch.marker"
    if [ "$FORCE_INSTALL" != true ] && [ -f "$marker" ]; then
        log_info "Account selector already applied to IDE."; return 0
    fi
    log_info "Applying account selector to Antigravity IDE..."; fix_permissions "$ide"
    node "$p_js" --ide "$ide"; sync_selector_skills
    fix_ide_checksums "$ide"; log_success "Account selector applied to IDE."
}

unpatch_selector_ide() {
    ensure_selector_dirs
    local ide="${IDE_INSTALL_DIR}" p_js; p_js="$(get_selector_patch_js)"
    [ ! -d "$ide" ] || [ -z "$p_js" ] && return 0
    log_info "Removing account selector from IDE..."; fix_permissions "$ide"
    node "$p_js" --ide --unpatch "$ide"
    fix_ide_checksums "$ide"; log_success "IDE selector unpatched."
}

patch_selector() {
    for arg in "$@"; do [ "$arg" = "--force" ] || [ "$arg" = "-f" ] && FORCE_INSTALL=true; done
    patch_selector_app "$@"
    patch_selector_ide "$@"
}

unpatch_selector() {
    unpatch_selector_app "$@"
    unpatch_selector_ide "$@"
}
