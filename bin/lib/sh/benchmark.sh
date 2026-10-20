#!/usr/bin/env bash
# AI response speed and latency benchmarking dispatcher

dispatch_benchmark() {
    local b_script="${LOCAL_BIN}/antigravity-benchmark.py"
    if [ ! -f "$b_script" ]; then
        local sdir
        sdir="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
        [ -f "${sdir}/bin/antigravity-benchmark.py" ] && b_script="${sdir}/bin/antigravity-benchmark.py"
        [ -f "${sdir}/antigravity-benchmark.py" ] && b_script="${sdir}/antigravity-benchmark.py"
    fi

    if [ ! -f "$b_script" ]; then
        log_err "antigravity-benchmark.py not found."
        return 1
    fi

    python3 "$b_script" "$@"
}
