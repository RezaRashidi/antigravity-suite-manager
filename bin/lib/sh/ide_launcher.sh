#!/usr/bin/env bash
# Antigravity IDE launcher script and desktop entry generator.

write_ide_launcher_and_desktop() {
    local ide_pass_store="$1"

    cat <<EOF > "${LOCAL_BIN}/antigravity-ide"
#!/usr/bin/env bash
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

exec "${IDE_INSTALL_DIR}/antigravity-ide" \${SANDBOX_FLAG}${ide_pass_store}--ozone-platform=x11 --class="antigravity-ide" --name="antigravity-ide" "\$@"
EOF
    chmod +x "${LOCAL_BIN}/antigravity-ide"

    cat <<EOF > "${LOCAL_APPS}/antigravity-ide.desktop"
[Desktop Entry]
Name=Antigravity IDE
GenericName=Code Editor
Comment=Google Antigravity AI IDE
Exec=${LOCAL_BIN}/antigravity-ide %U
Terminal=false
Type=Application
Icon=antigravity-ide
Categories=TextEditor;Development;IDE;
StartupWMClass=antigravity-ide
MimeType=x-scheme-handler/antigravity-ide;
StartupNotify=true
EOF
    chmod +x "${LOCAL_APPS}/antigravity-ide.desktop"

    if [ ! -f "${LOCAL_ICONS}/antigravity-ide.png" ]; then
        if [ -f "${LOCAL_ICONS}/antigravity-master-white.png" ]; then
            cp -f "${LOCAL_ICONS}/antigravity-master-white.png" "${LOCAL_ICONS}/antigravity-ide.png" 2>/dev/null || true
        elif [ -f "${LOCAL_ICONS}/antigravity-master-black.png" ]; then
            cp -f "${LOCAL_ICONS}/antigravity-master-black.png" "${LOCAL_ICONS}/antigravity-ide.png" 2>/dev/null || true
        fi
    fi

    update-desktop-database "${LOCAL_APPS}" 2>/dev/null || true
    xdg-mime default antigravity-ide.desktop x-scheme-handler/antigravity-ide 2>/dev/null || true
}
