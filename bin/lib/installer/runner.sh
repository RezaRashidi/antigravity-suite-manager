#!/usr/bin/env bash
# Installer execution loop and workflow runner

run_step() {
    local s="$1"
    case "$s" in
        1) step_1_prerequisites ;;
        2) step_2_configure_paths ;;
        3) step_3_compile_resampler ;;
        4) step_4_deploy_scripts ;;
        5) step_5_configure_icons ;;
        6) step_6_configure_keyring ;;
        7) step_7_install_antigravity ;;
        8) step_8_setup_launchers_and_sync ;;
        *) return 0 ;;
    esac
}

maybe_launch_control_center() {
    if [ "$NON_INTERACTIVE" != true ] && [ "$START_STEP" -eq 1 ] && [ "$ONLY_STEP" -eq 0 ] && [ "$STEP_BY_STEP" != true ]; then
        step_3_compile_resampler >/dev/null 2>&1 || true
        step_4_deploy_scripts >/dev/null 2>&1 || true
        step_5_configure_icons >/dev/null 2>&1 || true

        local local_detect="${SCRIPT_DIR}/bin/antigravity-detect.py"
        [ ! -f "$local_detect" ] && local_detect="${TARGET_BIN}/antigravity-detect.py"
        if [ -f "$local_detect" ]; then
            set +e
            python3 "$local_detect" --control-center
            local code=$?
            set -e
            if [ "$code" -eq 10 ]; then
                STEP_BY_STEP=true
                START_STEP=1
            else
                exit 0
            fi
        fi
    fi
}

run_installer_workflow() {
    if [ "$RUN_UPDATE" = true ]; then
        step_4_deploy_scripts
        exec "${TARGET_BIN}/manage-antigravity.sh" update
    fi

    maybe_launch_control_center

    if [ "$ONLY_STEP" -ge 1 ] && [ "$ONLY_STEP" -le 8 ]; then
        echo -e "\n${CYAN}======================================================================${NC}"
        echo -e "${BOLD}${CYAN}   Executing Step ${ONLY_STEP}: $(get_step_name "$ONLY_STEP")${NC}"
        echo -e "${CYAN}======================================================================${NC}"
        run_step "$ONLY_STEP"
        echo -e "${GREEN}[SUCCESS] Step ${ONLY_STEP} ($(get_step_name "$ONLY_STEP")) complete.${NC}"
        exit 0
    fi

    local curr="$START_STEP"
    while [ "$curr" -le 8 ]; do
        run_step "$curr"
        if [ "$STEP_BY_STEP" = true ] && [ "$curr" -lt 8 ] && [ "$NON_INTERACTIVE" != true ] && [ -t 0 ]; then
            echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
            echo -e "${BOLD}Completed Step ${curr}: $(get_step_name "$curr")${NC}"
            echo -e "Next up Step $((curr + 1)): $(get_step_name "$((curr + 1))")"
            read -rp "[Enter] Continue | [s]kip next | [j <1-8>] jump | [q]uit: " next_action
            case "$next_action" in
                [Qq]*) echo "Exiting setup wizard."; exit 0 ;;
                [Ss]*) curr=$((curr + 1)) ;;
                [Jj]*)
                    local target_j
                    target_j=$(echo "$next_action" | awk '{print $2}')
                    if [ -n "$target_j" ] && [ "$target_j" -ge 1 ] && [ "$target_j" -le 8 ] 2>/dev/null; then
                        curr="$target_j"
                        continue
                    fi
                    ;;
            esac
        fi
        curr=$((curr + 1))
    done
}
