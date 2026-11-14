#!/usr/bin/env bash
# Antigravity App & IDE Downgrade Orchestrator with smart patch re-application

get_downgrade_resolver() {
    local cand
    for cand in "${LIB_SH_DIR}/downgrade_resolver.py" "${SCRIPT_DIR}/lib/sh/downgrade_resolver.py" "${ANTIGRAVITY_SUITE_DIR}/bin/lib/sh/downgrade_resolver.py"; do
        if [ -f "$cand" ]; then
            echo "$cand"
            return 0
        fi
    done
    return 1
}

prompt_select_version() {
    local comp="$1"
    local curr_ver="$2"
    local resolver
    resolver=$(get_downgrade_resolver)
    if [ -z "$resolver" ] || [ ! -f "$resolver" ]; then
        log_err "Downgrade resolver script not found."
        return 1
    fi

    local title_name="Antigravity App"
    [ "$comp" = "ide" ] && title_name="Antigravity IDE"

    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${CYAN}        Available ${title_name} Releases            ${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "Currently installed: ${BOLD}v${curr_ver:-Unknown}${NC}"
    echo ""

    local lines=()
    while IFS= read -r line; do
        [ -n "$line" ] && lines+=("$line")
    done < <(python3 "$resolver" list "$comp" "${CACHE_DIR:-/tmp/antigravity-cache}")

    if [ ${#lines[@]} -eq 0 ]; then
        log_warn "No releases discovered from endpoints or cache."
        read -rp "Enter target version number or download URL: " manual_ver
        if [ -n "$manual_ver" ]; then
            python3 "$resolver" resolve "$comp" "$manual_ver" "$curr_ver" "${CACHE_DIR:-/tmp/antigravity-cache}"
            return 0
        fi
        return 1
    fi

    local max_items=15
    [ ${#lines[@]} -lt $max_items ] && max_items=${#lines[@]}

    local idx=1
    for ((i=0; i<max_items; i++)); do
        local line="${lines[i]}"
        IFS='|' read -r r_ver r_url r_cached <<< "$line"
        local tag=""
        [ "$r_ver" = "$curr_ver" ] && tag="${YELLOW}[Installed]${NC} "
        [ "$r_cached" = "1" ] && tag="${tag}${GREEN}[Cached]${NC} "
        printf "  [%2d] v%-10s %b\n" "$idx" "$r_ver" "$tag"
        ((idx++))
    done

    echo "  [ C] Custom Version / Direct Download URL"
    echo "  [ 0] Cancel"
    echo -e "${CYAN}-----------------------------------------------------${NC}"

    read -rp "Select release to install [1-${max_items}, C, 0]: " choice
    case "$choice" in
        0|q|exit|"")
            log_info "Downgrade canceled."
            return 1
            ;;
        [cC])
            read -rp "Enter target version number or download URL: " manual_ver
            if [ -n "$manual_ver" ]; then
                python3 "$resolver" resolve "$comp" "$manual_ver" "$curr_ver" "${CACHE_DIR:-/tmp/antigravity-cache}"
                return 0
            fi
            return 1
            ;;
        *)
            if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "$max_items" ]; then
                local chosen_line="${lines[$((choice-1))]}"
                IFS='|' read -r c_ver c_url _ <<< "$chosen_line"
                echo "${c_ver}|${c_url}"
                return 0
            else
                log_err "Invalid selection '$choice'."
                return 1
            fi
            ;;
    esac
}

downgrade_app() {
    auto_detect_installations
    local target_ver="${1:-}"
    local target_url="${2:-}"

    # Filter flags from positional arguments
    for a in "$@"; do
        case "$a" in
            -y|--yes) NON_INTERACTIVE=true ;;
            -f|--force) FORCE_INSTALL=true ;;
        esac
    done
    [ -n "$TARGET_DOWNGRADE_VER" ] && [ -z "$target_ver" ] && target_ver="$TARGET_DOWNGRADE_VER"

    local current_installed
    current_installed=$(get_installed_version "Antigravity-App" "$APP_INSTALL_DIR")
    [ -z "$current_installed" ] && current_installed="Unknown"

    local resolver
    resolver=$(get_downgrade_resolver)

    if [ -z "$target_ver" ]; then
        if [ "$NON_INTERACTIVE" = true ]; then
            log_err "Non-interactive mode requires a target version (e.g. manage-antigravity.sh downgrade app 2.30.0)"
            return 1
        fi
        local sel
        sel=$(prompt_select_version "app" "$current_installed") || return 1
        [ -z "$sel" ] && return 0
        IFS='|' read -r target_ver target_url <<< "$sel"
    elif [ -z "$target_url" ]; then
        if [ -n "$resolver" ] && [ -f "$resolver" ]; then
            local resolved
            resolved=$(python3 "$resolver" resolve "app" "$target_ver" "$current_installed" "${CACHE_DIR:-/tmp/antigravity-cache}" 2>/dev/null || true)
            if [ -n "$resolved" ]; then
                IFS='|' read -r target_ver target_url <<< "$resolved"
            fi
        fi
    fi

    if [ -z "$target_ver" ] || [ -z "$target_url" ]; then
        log_err "Unable to resolve release details for Antigravity App (target: '${target_ver:-unknown}')."
        return 1
    fi

    if [ "$current_installed" = "$target_ver" ] && [ "$FORCE_INSTALL" != true ]; then
        log_warn "Antigravity App is already at v${current_installed}. Use --force to reinstall."
        return 0
    fi

    log_info "Initiating Antigravity App downgrade: v${current_installed} -> v${target_ver}"
    log_info "Package Source: ${target_url}"

    # Detect currently active patches before replacing binaries
    detect_active_app_patches
    log_info "Pre-downgrade active App patches: Selector=${HAD_APP_SELECTOR}, RTL=${HAD_APP_RTL}, Fork=${HAD_APP_FORK}, OpenIDE=${HAD_APP_OPEN_IDE}, WinBounds=${HAD_APP_WINDOW_BOUNDS}, TypingPerf=${HAD_APP_TYPING_PERF}, Models=${HAD_APP_MODELS}"

    if [ "$NON_INTERACTIVE" != true ]; then
        read -rp "Are you sure you want to downgrade Antigravity App to v${target_ver}? [y/N]: " confirm
        if [[ ! "$confirm" =~ ^[yY]([eE][sS])?$ ]]; then
            log_info "Downgrade canceled by user."
            return 0
        fi
    fi

    terminate_running_app

    ALLOW_DOWNGRADE=true FORCE_INSTALL=true install_binary "Antigravity-App" "$target_url" "$target_ver" "$APP_INSTALL_DIR"
    setup_account_1
    if [ -d "$PROFILE2_DIR" ] && [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then
        setup_account_2
    fi

    log_info "Re-applying previously applied App patches..."
    [ "$HAD_APP_MODELS" = true ] && { FORCE_INSTALL=true patch_models_app; }
    [ "$HAD_APP_RTL" = true ] && [ "$SKIP_RTL" != true ] && { FORCE_INSTALL=true patch_rtl_app --force; }
    [ "$HAD_APP_SELECTOR" = true ] && { FORCE_INSTALL=true patch_selector_app; }
    [ "$HAD_APP_FORK" = true ] && { FORCE_INSTALL=true patch_fork_app; }
    [ "$HAD_APP_OPEN_IDE" = true ] && { FORCE_INSTALL=true patch_open_ide_app; }
    [ "$HAD_APP_WINDOW_BOUNDS" = true ] && { FORCE_INSTALL=true patch_window_bounds_app; }
    [ "$HAD_APP_TYPING_PERF" = true ] && { FORCE_INSTALL=true patch_typing_perf_app; }

    log_success "Antigravity App downgrade to v${target_ver} complete."
}

downgrade_ide() {
    auto_detect_installations
    local target_ver="${1:-}"
    local target_url="${2:-}"

    for a in "$@"; do
        case "$a" in
            -y|--yes) NON_INTERACTIVE=true ;;
            -f|--force) FORCE_INSTALL=true ;;
        esac
    done
    [ -n "$TARGET_DOWNGRADE_VER" ] && [ -z "$target_ver" ] && target_ver="$TARGET_DOWNGRADE_VER"

    local current_installed
    current_installed=$(get_installed_version "Antigravity-IDE" "$IDE_INSTALL_DIR")
    [ -z "$current_installed" ] && current_installed="Unknown"

    local resolver
    resolver=$(get_downgrade_resolver)

    if [ -z "$target_ver" ]; then
        if [ "$NON_INTERACTIVE" = true ]; then
            log_err "Non-interactive mode requires a target version (e.g. manage-antigravity.sh downgrade ide 2.5.5)"
            return 1
        fi
        local sel
        sel=$(prompt_select_version "ide" "$current_installed") || return 1
        [ -z "$sel" ] && return 0
        IFS='|' read -r target_ver target_url <<< "$sel"
    elif [ -z "$target_url" ]; then
        if [ -n "$resolver" ] && [ -f "$resolver" ]; then
            local resolved
            resolved=$(python3 "$resolver" resolve "ide" "$target_ver" "$current_installed" "${CACHE_DIR:-/tmp/antigravity-cache}" 2>/dev/null || true)
            if [ -n "$resolved" ]; then
                IFS='|' read -r target_ver target_url <<< "$resolved"
            fi
        fi
    fi

    if [ -z "$target_ver" ] || [ -z "$target_url" ]; then
        log_err "Unable to resolve release details for Antigravity IDE (target: '${target_ver:-unknown}')."
        return 1
    fi

    if [ "$current_installed" = "$target_ver" ] && [ "$FORCE_INSTALL" != true ]; then
        log_warn "Antigravity IDE is already at v${current_installed}. Use --force to reinstall."
        return 0
    fi

    log_info "Initiating Antigravity IDE downgrade: v${current_installed} -> v${target_ver}"
    log_info "Package Source: ${target_url}"

    detect_active_ide_patches
    log_info "Pre-downgrade active IDE patches: Selector=${HAD_IDE_SELECTOR}, RTL=${HAD_IDE_RTL}, Fork=${HAD_IDE_FORK}, TypingPerf=${HAD_IDE_TYPING_PERF}"

    if [ "$NON_INTERACTIVE" != true ]; then
        read -rp "Are you sure you want to downgrade Antigravity IDE to v${target_ver}? [y/N]: " confirm
        if [[ ! "$confirm" =~ ^[yY]([eE][sS])?$ ]]; then
            log_info "Downgrade canceled by user."
            return 0
        fi
    fi

    pkill -f "${IDE_INSTALL_DIR}/antigravity-ide" 2>/dev/null || true

    ALLOW_DOWNGRADE=true FORCE_INSTALL=true install_binary "Antigravity-IDE" "$target_url" "$target_ver" "$IDE_INSTALL_DIR"
    setup_ide_shortcuts

    log_info "Re-applying previously applied IDE patches..."
    if [ "$HAD_IDE_SELECTOR" = true ]; then
        local is_below_26
        is_below_26=$(python3 -c "import sys; print(1 if tuple(int(x) for x in '${target_ver}'.split('.') if x.isdigit()) < (2, 6, 0) else 0)" 2>/dev/null || echo 0)
        if [ "$is_below_26" = "1" ]; then
            log_warn "Target IDE v${target_ver} is below v2.6.0. Selector patch requires v2.6.0+; skipping IDE selector."
        else
            FORCE_INSTALL=true patch_selector_ide
        fi
    fi
    [ "$HAD_IDE_RTL" = true ] && [ "$SKIP_RTL" != true ] && { FORCE_INSTALL=true patch_rtl_ide --force; }
    [ "$HAD_IDE_FORK" = true ] && { FORCE_INSTALL=true patch_fork_ide; }
    [ "$HAD_IDE_TYPING_PERF" = true ] && { FORCE_INSTALL=true patch_typing_perf_ide; }

    if [ "$HAD_IDE_SELECTOR" = true ] || [ "$HAD_IDE_RTL" = true ] || [ "$HAD_IDE_FORK" = true ] || [ "$HAD_IDE_TYPING_PERF" = true ]; then
        fix_ide_checksums "${IDE_INSTALL_DIR}"
    fi

    log_success "Antigravity IDE downgrade to v${target_ver} complete."
}

downgrade_all() {
    auto_detect_installations
    local app_ver="${1:-}"
    local ide_ver="${2:-}"

    log_info "Downgrading full Antigravity Suite (App + IDE)..."
    downgrade_app "$app_ver" || return 1
    downgrade_ide "$ide_ver" || return 1
    log_success "Full Antigravity Suite downgrade complete."
}

downgrade_interactive_or_target() {
    local target="${1:-}"
    shift 2>/dev/null || true

    # Extract flags from arguments if present
    for a in "$@"; do
        case "$a" in
            -y|--yes) NON_INTERACTIVE=true ;;
            -f|--force) FORCE_INSTALL=true ;;
        esac
    done

    # If first argument looks like a version string (e.g. 2.30.0 or v2.30.0)
    if [[ "$target" =~ ^v?[0-9]+\.[0-9]+ ]]; then
        downgrade_app "$target" "$@"
        return $?
    fi

    case "$target" in
        app)
            downgrade_app "$@"
            ;;
        ide)
            downgrade_ide "$@"
            ;;
        all|suite)
            downgrade_all "$@"
            ;;
        "")
            if [ "$NON_INTERACTIVE" = true ]; then
                log_err "Component or version required (e.g. manage-antigravity.sh downgrade app 2.30.0)"
                return 1
            fi
            auto_detect_installations
            local cur_app
            cur_app=$(get_installed_version "Antigravity-App" "$APP_INSTALL_DIR")
            local cur_ide
            cur_ide=$(get_installed_version "Antigravity-IDE" "$IDE_INSTALL_DIR")

            echo -e "${CYAN}=====================================================${NC}"
            echo -e "${CYAN}        Antigravity Suite Version Downgrade          ${NC}"
            echo -e "${CYAN}=====================================================${NC}"
            echo -e "Select component to downgrade:"
            echo -e "  1) Antigravity App (Current: v${cur_app:-Unknown})"
            echo -e "  2) Antigravity IDE (Current: v${cur_ide:-Unknown})"
            echo -e "  3) Both Suite Components (App + IDE)"
            echo -e "  0) Cancel"
            echo -e "${CYAN}-----------------------------------------------------${NC}"
            read -rp "Select option [0-3]: " c_choice
            case "$c_choice" in
                1) downgrade_app "$@" ;;
                2) downgrade_ide "$@" ;;
                3) downgrade_all "$@" ;;
                0|q|exit) log_info "Downgrade canceled."; return 0 ;;
                *) log_err "Invalid selection."; return 1 ;;
            esac
            ;;
        *)
            log_err "Unknown downgrade target: '$target'. Valid targets: app, ide, all, or version number."
            return 1
            ;;
    esac
}
