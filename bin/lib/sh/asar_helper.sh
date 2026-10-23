#!/usr/bin/env bash
# Helper for locating and running electron asar utility.

run_asar() {
    if command -v asar >/dev/null 2>&1; then
        asar "$@"
    elif [ -x "${REAL_HOME:-$HOME}/.local/bin/asar" ]; then
        "${REAL_HOME:-$HOME}/.local/bin/asar" "$@"
    elif [ -x "${REAL_HOME:-$HOME}/.local/node_modules/.bin/asar" ]; then
        "${REAL_HOME:-$HOME}/.local/node_modules/.bin/asar" "$@"
    elif [ -x "/usr/local/bin/asar" ]; then
        /usr/local/bin/asar "$@"
    elif npx --yes --no-install @electron/asar --version >/dev/null 2>&1; then
        npx --yes --no-install @electron/asar "$@"
    elif npx --yes --no-install asar --version >/dev/null 2>&1; then
        npx --yes --no-install asar "$@"
    elif command -v npm >/dev/null 2>&1; then
        log_info "Installing @electron/asar locally for fast offline packaging..."
        mkdir -p "${REAL_HOME:-$HOME}/.local/bin"
        npm install --prefix "${REAL_HOME:-$HOME}/.local" @electron/asar 2>/dev/null || true
        if [ -x "${REAL_HOME:-$HOME}/.local/node_modules/.bin/asar" ]; then
            ln -sfn "${REAL_HOME:-$HOME}/.local/node_modules/.bin/asar" "${REAL_HOME:-$HOME}/.local/bin/asar" 2>/dev/null || true
            "${REAL_HOME:-$HOME}/.local/bin/asar" "$@"
            return $?
        fi
        if command -v npx >/dev/null 2>&1; then
            npx --yes @electron/asar "$@"
        fi
    elif command -v npx >/dev/null 2>&1; then
        npx --yes @electron/asar "$@"
    else
        log_err "Neither 'asar' nor 'npm'/'npx' is available to unpack app.asar."
        return 1
    fi
}
