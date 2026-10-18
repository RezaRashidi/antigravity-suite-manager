#!/usr/bin/env bash
# Toggles history sharing mode (Shared vs Isolated) for any instance.

set_history_mode() {
    local itype="$1" iid="$2" target_mode="$3"
    [ -z "$itype" ] || [ -z "$iid" ] || [ -z "$target_mode" ] && {
        echo "Usage: $(basename "$0") set-history [app|ide] [instance_id] [shared|isolated]"; return 1;
    }
    itype=$(echo "$itype" | tr '[:upper:]' '[:lower:]')
    target_mode=$(echo "$target_mode" | tr '[:upper:]' '[:lower:]')

    local profile_gemini=""
    if [ "$itype" = "app" ]; then
        profile_gemini="${REAL_HOME}/.antigravity-profile2/.gemini/antigravity"
        [ "$iid" != "2" ] && profile_gemini="${REAL_HOME}/.antigravity-profile-app-${iid}/.gemini/antigravity"
    elif [ "$itype" = "ide" ]; then
        profile_gemini="${REAL_HOME}/.gemini/antigravity-ide"
        [ "$iid" != "1" ] && [ "$iid" != "default" ] && profile_gemini="${REAL_HOME}/.antigravity-ide-profile-${iid}/.gemini/antigravity-ide"
    fi

    local parent_dir="$(dirname "$profile_gemini")"
    [ ! -d "$parent_dir" ] && { log_err "Instance dir for ${itype} '${iid}' missing (${parent_dir})."; return 1; }

    local mig_tool="${LOCAL_BIN}/antigravity-migration.py"
    [ ! -f "$mig_tool" ] && mig_tool="${SCRIPT_DIR}/bin/antigravity-migration.py"
    [ ! -f "$mig_tool" ] && mig_tool="${SCRIPT_DIR}/antigravity-migration.py"
    [ -f "$mig_tool" ] && python3 "$mig_tool" create-backup --category history --label "pre_set_history_${itype}_${iid}" >/dev/null 2>&1 || true

    if [ "$target_mode" = "shared" ]; then
        log_info "Switching ${itype} '${iid}' to SHARED history..."
        if [ "$itype" = "ide" ]; then
            local ide_conv="${profile_gemini}/conversations" ide_brain="${profile_gemini}/brain"
            mkdir -p "${SHARED_CONV_DIR}/conversations" "${SHARED_CONV_DIR}/brain"
            if [ -d "$profile_gemini" ] && [ ! -L "$profile_gemini" ]; then
                python3 "${LOCAL_BIN}/antigravity-merge-history.py" --source "$profile_gemini" --quiet 2>/dev/null || true
                [ -d "$ide_brain" ] && [ ! -L "$ide_brain" ] && { cp -rn "${ide_brain}"/* "${SHARED_CONV_DIR}/brain/" 2>/dev/null || true; mv "$ide_brain" "${ide_brain}.bak_$(date +%s)"; }
                [ -d "$ide_conv" ] && [ ! -L "$ide_conv" ] && mv "$ide_conv" "${ide_conv}.bak_$(date +%s)"
            fi
            ln -sfn "${SHARED_CONV_DIR}/conversations" "$ide_conv" && ln -sfn "${SHARED_CONV_DIR}/brain" "$ide_brain"
            ln -sfn "${SHARED_CONV_DIR}/conversation_summaries.db" "${profile_gemini}/conversation_summaries.db"
            [ -f "${SHARED_CONV_DIR}/agyhub_summaries_proto.pb" ] && ln -sfn "${SHARED_CONV_DIR}/agyhub_summaries_proto.pb" "${profile_gemini}/agyhub_summaries_proto.pb"
            merge_history
        else
            if [ -d "$profile_gemini" ] && [ ! -L "$profile_gemini" ]; then
                mkdir -p "${SHARED_CONV_DIR}/conversations" "${SHARED_CONV_DIR}/brain"
                python3 "${LOCAL_BIN}/antigravity-merge-history.py" --source "$profile_gemini" --quiet 2>/dev/null || true
                [ -d "${profile_gemini}/brain" ] && cp -rn "${profile_gemini}/brain"/* "${SHARED_CONV_DIR}/brain/" 2>/dev/null || true
                mv "$profile_gemini" "${profile_gemini}.bak_$(date +%s)"
            fi
            ln -sfn "$SHARED_CONV_DIR" "$profile_gemini" && merge_history
        fi
        log_success "${itype^^} '${iid}' is now linked to SHARED history."
    elif [ "$target_mode" = "isolated" ]; then
        log_info "Switching ${itype} '${iid}' to ISOLATED history..."
        if [ "$itype" = "ide" ]; then
            [ -L "$profile_gemini" ] && { rm -f "$profile_gemini"; mkdir -p "$profile_gemini"; }
            local ide_conv="${profile_gemini}/conversations" ide_brain="${profile_gemini}/brain"
            rm -f "$ide_conv" "$ide_brain" "${profile_gemini}/conversation_summaries.db" "${profile_gemini}/agyhub_summaries_proto.pb" 2>/dev/null || true
            mkdir -p "$ide_conv" "$ide_brain"
            cp -n "${SHARED_CONV_DIR}/conversations"/*.db* "$ide_conv/" 2>/dev/null || true
            cp -rn "${SHARED_CONV_DIR}/brain"/* "$ide_brain/" 2>/dev/null || true
            cp -n "${SHARED_CONV_DIR}"/*summaries* "${profile_gemini}/" 2>/dev/null || true
        else
            [ -L "$profile_gemini" ] && rm -f "$profile_gemini"
            mkdir -p "${profile_gemini}/conversations" "${profile_gemini}/brain"
            cp -n "${SHARED_CONV_DIR}/conversations"/*.db* "${profile_gemini}/conversations/" 2>/dev/null || true
            cp -rn "${SHARED_CONV_DIR}/brain"/* "${profile_gemini}/brain/" 2>/dev/null || true
            cp -n "${SHARED_CONV_DIR}"/*summaries* "${profile_gemini}/" 2>/dev/null || true
        fi
        log_success "${itype^^} '${iid}' now has ISOLATED private history."
    else
        log_err "Unknown mode '${target_mode}'. Use 'shared' or 'isolated'."
        return 1
    fi
}
