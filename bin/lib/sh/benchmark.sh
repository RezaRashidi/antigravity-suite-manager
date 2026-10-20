#!/usr/bin/env bash
# AI response speed and latency benchmarking dispatcher

dispatch_benchmark() {
    local b_script=""
    if [ -n "${LOCAL_BIN:-}" ] && [ -f "${LOCAL_BIN}/antigravity-benchmark.py" ]; then
        b_script="${LOCAL_BIN}/antigravity-benchmark.py"
    elif command -v antigravity-benchmark.py >/dev/null 2>&1; then
        b_script="$(command -v antigravity-benchmark.py)"
    else
        local sdir
        sdir="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
        [ -f "${sdir}/bin/antigravity-benchmark.py" ] && b_script="${sdir}/bin/antigravity-benchmark.py"
        [ -f "${sdir}/antigravity-benchmark.py" ] && b_script="${sdir}/antigravity-benchmark.py"
    fi

    if [ -n "$b_script" ] && [ -f "$b_script" ]; then
        python3 "$b_script" "$@"
        return $?
    fi

    if python3 -c "import antigravity_suite.benchmark" >/dev/null 2>&1; then
        python3 -m antigravity_suite.benchmark "$@"
        return $?
    fi

    log_err "antigravity-benchmark.py not found. Please run Option 24 (Update Suite Manager Repository) or git pull."
    return 1
}
