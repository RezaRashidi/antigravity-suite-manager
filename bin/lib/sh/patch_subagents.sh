#!/usr/bin/env bash
# Standalone patcher for Subagent Dynamic Multi-Account Allocator & Swarm

sync_subagent_plugin() {
    local r_dir="${ANTIGRAVITY_SUITE_DIR:-}"
    if [ -z "$r_dir" ] || [ ! -d "$r_dir" ]; then
        r_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." 2>/dev/null && pwd)"
    fi
    local src_plug="${r_dir}/plugins/subagent-swarm"
    for base in "${REAL_HOME:-$HOME}/.gemini" "${REAL_HOME:-$HOME}/.gemide"; do
        mkdir -p "${base}/config/plugins" 2>/dev/null || true
        if [ -d "$src_plug" ]; then
            cp -rf "$src_plug" "${base}/config/plugins/" 2>/dev/null || true
        fi
    done
}

set_subagent_config() {
    local en="${1:-true}" pro="${2:-true}"
    local acc_dir="${REAL_HOME:-$HOME}/.config/antigravity/accounts"
    mkdir -p "$acc_dir" 2>/dev/null || true
    cat <<EOF > "${acc_dir}/subagent_policy.json"
{
  "enabled": ${en},
  "proactive_mode": ${pro},
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

patch_subagents() {
    log_info "Applying Subagent Dynamic Multi-Account & Swarm patch..."
    set_subagent_config true true
    sync_subagent_plugin

    # If App is installed and patch_selector_app is available, refresh router in asar
    if [ -f "${APP_INSTALL_DIR}/resources/app.asar" ] && declare -f patch_selector_app >/dev/null 2>&1; then
        FORCE_INSTALL=true patch_selector_app >/dev/null 2>&1 || true
    fi

    log_success "Subagent Dynamic Multi-Account & Swarm patch active."
    log_info "Idle accounts will be dynamically assigned to subagents; proactive swarm enabled."
}

subagent_status() {
    local acc_dir="${REAL_HOME:-$HOME}/.config/antigravity/accounts"
    local p_file="${acc_dir}/subagent_policy.json"
    if [ -f "$p_file" ]; then
        echo "Subagent Allocator Status:"
        cat "$p_file"
    else
        echo "Subagent Allocator Status: Default (Enabled)"
    fi
}

dispatch_subagents() {
    auto_detect_installations 2>/dev/null || true
    for arg in "$@"; do
        if [ "$arg" = "--status" ]; then subagent_status; return 0; fi
        if [ "$arg" = "--revert" ] || [ "$arg" = "--disable" ]; then unpatch_subagents "$@"; return 0; fi
        if [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
            echo "Usage: manage-antigravity.sh subagents [--status|--disable|--revert]"
            return 0
        fi
    done
    patch_subagents "$@"
}

dispatch_unpatch_subagents() {
    auto_detect_installations 2>/dev/null || true
    unpatch_subagents "$@"
}
