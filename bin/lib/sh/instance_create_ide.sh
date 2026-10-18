#!/usr/bin/env bash
# Dedicated creator for custom Antigravity IDE instances and profiles.

create_ide_instance() {
    local iid="$1"
    local imode="$2"
    local itheme="${3:-black}"
    local ihue="$4"

    local profile_dir="${REAL_HOME}/.antigravity-ide-profile-${iid}"
    local wm_class="antigravity-ide-${iid}"
    local launcher="${LOCAL_BIN}/antigravity-ide-${iid}"
    local desktop="${LOCAL_APPS}/antigravity-ide-${iid}.desktop"

    mkdir -p "${profile_dir}/.gemini/antigravity-ide" "${profile_dir}/.gemide/cache" "${profile_dir}/.local/share"
    ln -sfn "$LOCAL_APPS" "${profile_dir}/.local/share/applications"
    ln -sfn "$LOCAL_ICONS" "${profile_dir}/.local/share/icons"
    [ -f "${SHARED_GEMINI_DIR}/GEMINI.md" ] && ln -sfn "${SHARED_GEMINI_DIR}/GEMINI.md" "${profile_dir}/.gemini/GEMINI.md"
    [ -d "${SHARED_CONFIG_DIR}" ] && ln -sfn "${SHARED_CONFIG_DIR}" "${profile_dir}/.gemini/config"
    ln -sfn ../.gemini/GEMINI.md "${profile_dir}/.gemide/GEMINI.md" 2>/dev/null || true
    ln -sfn ../.gemini/config "${profile_dir}/.gemide/config" 2>/dev/null || true
    touch "${profile_dir}/.gemide/cache/antigravity-keyring-unavailable"

    if [ "$imode" = "shared" ]; then
        log_info "Configuring shared conversation history with master pool..."
        ln -sfn "$SHARED_CONV_DIR/conversations" "${profile_dir}/.gemini/antigravity-ide/conversations"
        ln -sfn "$SHARED_CONV_DIR/brain" "${profile_dir}/.gemini/antigravity-ide/brain"
        ln -sfn "$SHARED_CONV_DIR/conversation_summaries.db" "${profile_dir}/.gemini/antigravity-ide/conversation_summaries.db"
        [ -f "$SHARED_CONV_DIR/agyhub_summaries_proto.pb" ] && ln -sfn "$SHARED_CONV_DIR/agyhub_summaries_proto.pb" "${profile_dir}/.gemini/antigravity-ide/agyhub_summaries_proto.pb"
    else
        log_info "Configuring isolated private conversation history..."
        mkdir -p "${profile_dir}/.gemini/antigravity-ide/conversations" "${profile_dir}/.gemini/antigravity-ide/brain"
    fi

    log_info "Generating dedicated icon for ${wm_class}..."
    local icon_args=(--custom-instance "$wm_class" --custom-theme "$itheme")
    [ -n "$ihue" ] && icon_args+=(--custom-hue "$ihue")
    python3 "${LOCAL_BIN}/antigravity-generate-icons.py" "${icon_args[@]}" >/dev/null 2>&1 || true

    cat <<EOF > "$launcher"
#!/usr/bin/env bash
set -e
export REAL_HOME="${REAL_HOME}"
export PROFILE="${profile_dir}"
export HOME="\${PROFILE}"
export XDG_CONFIG_HOME="\${PROFILE}/.config"
export ELECTRON_OZONE_PLATFORM_HINT="x11"

! pgrep -f "antigravity-apply-icon.py --daemon" >/dev/null 2>&1 && python3 "${LOCAL_BIN}/antigravity-apply-icon.py" --daemon >/dev/null 2>&1 &
! pgrep -f "antigravity-merge-history.py" >/dev/null 2>&1 && python3 "${LOCAL_BIN}/antigravity-merge-history.py" --quiet >/dev/null 2>&1 &
disown -a 2>/dev/null || true

SANDBOX_FLAG=""
if [ -f "${IDE_INSTALL_DIR}/chrome-sandbox" ]; then
    sb_stat=\$(stat -c "%u:%a" "${IDE_INSTALL_DIR}/chrome-sandbox" 2>/dev/null || true)
    if [ "\$sb_stat" != "0:4755" ] && ! (sudo -n chown root:root "${IDE_INSTALL_DIR}/chrome-sandbox" 2>/dev/null && sudo -n chmod 4755 "${IDE_INSTALL_DIR}/chrome-sandbox" 2>/dev/null); then
        SANDBOX_FLAG="--no-sandbox "
    fi
fi

exec "${IDE_INSTALL_DIR}/antigravity-ide" \${SANDBOX_FLAG}--password-store=basic --ozone-platform=x11 --user-data-dir "\${PROFILE}/.config/Antigravity IDE" --class="${wm_class}" --name="${wm_class}" "\$@"
EOF
    chmod +x "$launcher"

    cat <<EOF > "$desktop"
[Desktop Entry]
Name=Antigravity IDE (${iid})
GenericName=Code Editor
Comment=Google Antigravity AI IDE - Instance ${iid}
Exec=${launcher} %U
Terminal=false
Type=Application
Icon=${LOCAL_ICONS}/${wm_class}.png
Categories=TextEditor;Development;IDE;
StartupWMClass=${wm_class}
MimeType=x-scheme-handler/antigravity-ide;
StartupNotify=true
EOF
    chmod +x "$desktop"
    update-desktop-database "$LOCAL_APPS" 2>/dev/null || true
}
