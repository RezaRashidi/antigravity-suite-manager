#!/usr/bin/env bash
# Token usage, cache hit rate, and USD cost reporting dispatcher

dispatch_usage() {
    if ! command -v python3 >/dev/null 2>&1; then
        log_err "Python 3 is required for usage analytics."
        return 1
    fi
    local root_dir="${ANTIGRAVITY_SUITE_DIR:-}"
    if [ -z "$root_dir" ]; then
        root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
    fi
    if [ -d "${root_dir}/src" ]; then
        export PYTHONPATH="${root_dir}/src:${PYTHONPATH:-}"
    fi
    python3 -m antigravity_suite.usage "$@"
}
