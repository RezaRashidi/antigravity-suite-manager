#!/usr/bin/env bash
# Antigravity IDE 3-way history and customization symlinking.

setup_ide_sharing() {
    local ide_gemini="${SHARED_GEMINI_DIR}/antigravity-ide"
    mkdir -p "$ide_gemini" "$SHARED_CONV_DIR/conversations" "$SHARED_CONV_DIR/brain"

    if [ -d "$ide_gemini/conversations" ] && [ ! -L "$ide_gemini/conversations" ]; then
        log_info "Merging existing IDE conversations into shared history..."
        for f in "$ide_gemini/conversations/"*; do
            [ -e "$f" ] || continue
            dst="$SHARED_CONV_DIR/conversations/$(basename "$f")"
            [ -e "$dst" ] || cp -a "$f" "$dst" 2>/dev/null || true
        done
        mv "$ide_gemini/conversations" "$ide_gemini/conversations.bak_$(date +%s)"
    fi
    ln -sfn "$SHARED_CONV_DIR/conversations" "$ide_gemini/conversations"

    if [ -d "$ide_gemini/brain" ] && [ ! -L "$ide_gemini/brain" ]; then
        log_info "Merging existing IDE brain artifacts into shared brain..."
        for b in "$ide_gemini/brain/"*; do
            [ -e "$b" ] || continue
            dst="$SHARED_CONV_DIR/brain/$(basename "$b")"
            [ -e "$dst" ] || cp -a "$b" "$dst" 2>/dev/null || true
        done
        mv "$ide_gemini/brain" "$ide_gemini/brain.bak_$(date +%s)"
    fi
    ln -sfn "$SHARED_CONV_DIR/brain" "$ide_gemini/brain"

    if [ -f "${LOCAL_BIN}/antigravity-merge-history.py" ]; then
        python3 "${LOCAL_BIN}/antigravity-merge-history.py" --master "$SHARED_CONV_DIR" --quiet >/dev/null 2>&1 || true
    fi

    if [ -f "$ide_gemini/conversation_summaries.db" ] && [ ! -L "$ide_gemini/conversation_summaries.db" ]; then
        mv "$ide_gemini/conversation_summaries.db" "$ide_gemini/conversation_summaries.db.bak_$(date +%s)"
    fi
    [ -f "$SHARED_CONV_DIR/conversation_summaries.db" ] && ln -sfn "$SHARED_CONV_DIR/conversation_summaries.db" "$ide_gemini/conversation_summaries.db"

    for sym_proto in "agyhub_summaries_proto.pb" "jetbox_summaries_proto.pb" "jetbox_summaries.pb"; do
        [ -f "$SHARED_CONV_DIR/agyhub_summaries_proto.pb" ] && ln -sfn "$SHARED_CONV_DIR/agyhub_summaries_proto.pb" "$ide_gemini/$sym_proto"
    done

    mkdir -p "${REAL_HOME}/.gemide"
    for ide_root in "${REAL_HOME}/.gemide" "${REAL_HOME}/.gemini-ide"; do
        if [ -d "$ide_root" ]; then
            [ -f "${SHARED_GEMINI_DIR}/GEMINI.md" ] && ln -sfn "${SHARED_GEMINI_DIR}/GEMINI.md" "$ide_root/GEMINI.md"
            for shared_json in projects.json settings.json .env state.json trustedFolders.json; do
                [ -f "${SHARED_GEMINI_DIR}/$shared_json" ] && ln -sfn "${SHARED_GEMINI_DIR}/$shared_json" "$ide_root/$shared_json"
            done
            if [ -d "$ide_root/config" ] && [ ! -L "$ide_root/config" ]; then
                mv "$ide_root/config" "$ide_root/config.bak_$(date +%s)"
            fi
            ln -sfn "$SHARED_CONFIG_DIR" "$ide_root/config"

            local target_ide_app="$ide_root/antigravity-ide"
            mkdir -p "$target_ide_app"
            ln -sfn "$SHARED_CONV_DIR/mcp" "$target_ide_app/mcp"
            ln -sfn "$SHARED_CONV_DIR/plugin_data" "$target_ide_app/plugin_data"
            ln -sfn "$SHARED_CONV_DIR/conversations" "$target_ide_app/conversations"
            ln -sfn "$SHARED_CONV_DIR/brain" "$target_ide_app/brain"
            ln -sfn "$SHARED_CONV_DIR/conversation_summaries.db" "$target_ide_app/conversation_summaries.db"
            [ -f "$SHARED_CONV_DIR/agyhub_summaries_proto.pb" ] && ln -sfn "$SHARED_CONV_DIR/agyhub_summaries_proto.pb" "$target_ide_app/agyhub_summaries_proto.pb"
            ln -sfn "$SHARED_CONV_DIR/conversation_summaries.db" "$ide_root/conversation_summaries.db"
            [ -f "$SHARED_CONV_DIR/agyhub_summaries_proto.pb" ] && ln -sfn "$SHARED_CONV_DIR/agyhub_summaries_proto.pb" "$ide_root/agyhub_summaries_proto.pb"
            rm -f "$target_ide_app/GEMINI.md" "$ide_root/config/GEMINI.md"
        fi
    done
}
