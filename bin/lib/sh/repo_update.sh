#!/usr/bin/env bash
# Antigravity Suite Manager repository self-update engine

find_suite_repo_root() {
    local candidate
    for candidate in \
        "$SCRIPT_DIR" \
        "${SCRIPT_DIR}/.." \
        "$PWD" \
        "${PWD}/.." \
        "${REAL_HOME}/.antigravity-suite-manager" \
        "${REAL_HOME}/antigravity-suite-manager" \
        "${REAL_HOME}/PhpstormProjects/antigravity-suite-manager" \
        "${REAL_HOME}/projects/antigravity-suite-manager" \
        "${REAL_HOME}/src/antigravity-suite-manager" \
        "/opt/antigravity-suite-manager"; do
        if [ -d "${candidate}/.git" ]; then
            echo "$(cd -P "$candidate" && pwd)"
            return 0
        fi
    done
    local py_repo
    py_repo=$(python3 -c "import antigravity_suite, os; print(os.path.abspath(os.path.join(os.path.dirname(antigravity_suite.__file__), '..', '..')))" 2>/dev/null || true)
    if [ -n "$py_repo" ] && [ -d "${py_repo}/.git" ]; then
        echo "$py_repo"
        return 0
    fi
    return 1
}

update_suite_repo() {
    log_info "Detecting Antigravity Suite Manager repository..."
    local repo_dir
    repo_dir=$(find_suite_repo_root) || {
        log_err "Failed to locate Antigravity Suite Manager git repository."
        return 1
    }
    log_info "Updating repository at ${repo_dir} via git pull..."
    local branch
    branch=$(git -C "$repo_dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
    if [ "$(git -C "$repo_dir" rev-parse --is-shallow-repository 2>/dev/null)" = "true" ]; then
        log_info "Unshallowing repository to ensure complete history fetch..."
        git -C "$repo_dir" fetch --unshallow origin 2>/dev/null || true
    fi
    if ! git -C "$repo_dir" pull origin "$branch"; then
        log_err "Git pull failed for branch '$branch'."
        return 1
    fi
    log_success "Repository successfully updated from origin/${branch}."

    if [ -f "${repo_dir}/src/scale_icon.c" ]; then
        log_info "Recompiling Catmull-Rom resampler..."
        gcc -O3 -Wall "${repo_dir}/src/scale_icon.c" -lm -o "${LOCAL_BIN}/scale_icon" 2>/dev/null || true
        chmod +x "${LOCAL_BIN}/scale_icon" 2>/dev/null || true
    fi

    log_info "Redeploying suite scripts and libraries to ${LOCAL_BIN}..."
    if [ -d "${repo_dir}/bin" ]; then
        mkdir -p "${LOCAL_BIN}"
        for f in "${repo_dir}/bin"/*; do
            [ -f "$f" ] || continue
            cp -f "$f" "${LOCAL_BIN}/" 2>/dev/null || true
            chmod +x "${LOCAL_BIN}/$(basename "$f")" 2>/dev/null || true
        done
        if [ -d "${repo_dir}/bin/lib" ]; then
            mkdir -p "${LOCAL_BIN}/lib"
            cp -rf "${repo_dir}/bin/lib/"* "${LOCAL_BIN}/lib/" 2>/dev/null || true
        fi
    fi
    if [ -f "${repo_dir}/install.sh" ]; then
        cp -f "${repo_dir}/install.sh" "${LOCAL_BIN}/" 2>/dev/null || true
        chmod +x "${LOCAL_BIN}/install.sh" 2>/dev/null || true
        ln -sfn "${LOCAL_BIN}/install.sh" "${REAL_HOME}/install.sh" 2>/dev/null || true
    fi

    local py_ver
    py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3")
    local user_sp="${REAL_HOME}/.local/lib/python${py_ver}/site-packages"
    mkdir -p "$user_sp" 2>/dev/null || true
    echo "${repo_dir}/src" > "${user_sp}/antigravity_suite.pth" 2>/dev/null || true

    ln -sfn "${LOCAL_BIN}/manage-antigravity.sh" "${LOCAL_BIN}/manage-antigravity" 2>/dev/null || true
    ln -sfn "${LOCAL_BIN}/manage-antigravity.sh" "${LOCAL_BIN}/antigravity-suite" 2>/dev/null || true
    ln -sfn "${LOCAL_BIN}/manage-antigravity.sh" "${REAL_HOME}/manage-antigravity.sh" 2>/dev/null || true
    ln -sfn "${LOCAL_BIN}/manage-antigravity.sh" "${REAL_HOME}/manage-antigravity" 2>/dev/null || true

    if [ -w "/usr/local/bin" ]; then
        ln -sfn "${LOCAL_BIN}/manage-antigravity.sh" "/usr/local/bin/manage-antigravity" 2>/dev/null || true
        ln -sfn "${LOCAL_BIN}/manage-antigravity.sh" "/usr/local/bin/manage-antigravity.sh" 2>/dev/null || true
        ln -sfn "${LOCAL_BIN}/manage-antigravity.sh" "/usr/local/bin/antigravity-suite" 2>/dev/null || true
    elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
        sudo -n ln -sfn "${LOCAL_BIN}/manage-antigravity.sh" "/usr/local/bin/manage-antigravity" 2>/dev/null || true
        sudo -n ln -sfn "${LOCAL_BIN}/manage-antigravity.sh" "/usr/local/bin/manage-antigravity.sh" 2>/dev/null || true
        sudo -n ln -sfn "${LOCAL_BIN}/manage-antigravity.sh" "/usr/local/bin/antigravity-suite" 2>/dev/null || true
    fi

    log_info "Restarting background services with updated codebase..."
    restart_suite_services

    log_success "Antigravity Suite Manager repository update complete!"
}
