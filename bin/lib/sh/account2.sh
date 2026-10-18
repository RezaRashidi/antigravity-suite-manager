#!/usr/bin/env bash
# Secondary account 2 environment setup and desktop shortcut generator.

setup_account_2() {
    log_info "Configuring Account 2 (Secondary isolated profile)..."
    auto_detect_installations
    if [ -z "$APP_INSTALL_DIR" ] || [ ! -f "${APP_INSTALL_DIR}/antigravity" ]; then
        for cand in "$APP_INSTALL_DIR" "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity"; do
            [ -n "$cand" ] && [ -f "${cand}/antigravity" ] && { APP_INSTALL_DIR="$cand"; break; }
        done
    fi
    APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/Antigravity-x64}"

    mkdir -p "$PROFILE2_DIR/.gemini"
    local pass_store_flag=""
    if [ "$KEYRING_MODE_APP2" = "normal" ]; then
        pass_store_flag="--password-store=basic "
        mkdir -p "$PROFILE2_DIR/.gemini/cache" && touch "$PROFILE2_DIR/.gemini/cache/antigravity-keyring-unavailable"
    else
        rm -f "$PROFILE2_DIR/.gemini/cache/antigravity-keyring-unavailable" 2>/dev/null || true
    fi

    ln -sfn "$SHARED_CONV_DIR" "$PROFILE2_DIR/.gemini/antigravity"
    ln -sfn "$SHARED_CONFIG_DIR" "$PROFILE2_DIR/.gemini/config"
    [ -f "$SHARED_GEMINI_DIR/GEMINI.md" ] && ln -sfn "$SHARED_GEMINI_DIR/GEMINI.md" "$PROFILE2_DIR/.gemini/GEMINI.md"
    for shared_json in projects.json settings.json .env state.json trustedFolders.json; do
        [ -f "$SHARED_GEMINI_DIR/$shared_json" ] && ln -sfn "$SHARED_GEMINI_DIR/$shared_json" "$PROFILE2_DIR/.gemini/$shared_json"
    done

    mkdir -p "$PROFILE2_DIR/.local/share"
    ln -sfn "$LOCAL_APPS" "$PROFILE2_DIR/.local/share/applications"
    ln -sfn "$LOCAL_ICONS" "$PROFILE2_DIR/.local/share/icons"

    apply_icons_config || true
    write_account2_launcher "$pass_store_flag"

    cat <<EOF > "${LOCAL_APPS}/antigravity-2.desktop"
[Desktop Entry]
Name=Antigravity (Account 2)
GenericName=AI Pair Programmer
Comment=Antigravity AI Platform - Account 2
Exec=${LOCAL_BIN}/antigravity-acc2 %U
Terminal=false
Type=Application
Icon=${LOCAL_ICONS}/antigravity-acc2.png
Categories=Development;IDE;
StartupWMClass=antigravity-2
StartupNotify=true
Actions=Restart;

[Desktop Action Restart]
Name=Restart Account 2
Exec=${LOCAL_BIN}/antigravity-acc2 --restart
EOF
    chmod +x "${LOCAL_APPS}/antigravity-2.desktop"
    update-desktop-database "${LOCAL_APPS}" 2>/dev/null || true

    setup_account_1
    log_success "Account 2 configured with distinct icons and single-instance management."
}
