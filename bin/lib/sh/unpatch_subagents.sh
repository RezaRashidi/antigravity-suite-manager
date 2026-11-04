#!/usr/bin/env bash
# Revert/disable Subagent Dynamic Multi-Account Allocator & Swarm patch

unpatch_subagents() {
    log_info "Reverting Subagent Dynamic Multi-Account & Swarm patch..."
    local acc_dir="${REAL_HOME:-$HOME}/.config/antigravity/accounts"
    mkdir -p "$acc_dir" 2>/dev/null || true
    cat <<EOF > "${acc_dir}/subagent_policy.json"
{
  "enabled": false,
  "proactive_mode": false,
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

    for base in "${REAL_HOME:-$HOME}/.gemini" "${REAL_HOME:-$HOME}/.gemide"; do
        rm -rf "${base}/config/plugins/subagent-swarm" 2>/dev/null || true
    done

    log_success "Subagent Dynamic Multi-Account & Swarm patch disabled."
    log_info "Subagents will now follow standard default account binding."
}
