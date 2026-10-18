#!/usr/bin/env bash
# Icon configuration save and apply routines

save_icons_config() {
    mkdir -p "$ICONS_CONF_DIR"
    cat <<EOF > "$ICONS_CONF"
# Antigravity Suite Icon Configuration
ACC1_ICON_THEME="${ACC1_ICON_THEME}"
ACC1_EMBLEM_COLOR="${ACC1_EMBLEM_COLOR}"
ACC2_ICON_THEME="${ACC2_ICON_THEME}"
ACC2_EMBLEM_COLOR="${ACC2_EMBLEM_COLOR}"
ACC2_RECOLOR="${ACC2_RECOLOR}"
IDE_ICON_THEME="${IDE_ICON_THEME}"
IDE_EMBLEM_COLOR="${IDE_EMBLEM_COLOR}"
EOF
}

find_icon_generator() {
    local sdir
    sdir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    for cand in "${sdir}/antigravity-generate-icons.py" \
                "${sdir}/bin/antigravity-generate-icons.py" \
                "${REAL_HOME}/.antigravity-suite-manager/bin/antigravity-generate-icons.py" \
                "${LOCAL_BIN}/antigravity-generate-icons.py"; do
        if [ -f "$cand" ]; then
            echo "$cand"
            return 0
        fi
    done
    return 1
}

apply_icons_config() {
    log_info "Configuring Suite Icons: App1=${ACC1_ICON_THEME} (${ACC1_EMBLEM_COLOR}), App2=${ACC2_ICON_THEME} (${ACC2_EMBLEM_COLOR}), IDE=${IDE_ICON_THEME} (${IDE_EMBLEM_COLOR})..."
    save_icons_config

    local gen_py
    gen_py="$(find_icon_generator 2>/dev/null || true)"

    if [ -n "$gen_py" ] && [ -f "$gen_py" ] && [ "$gen_py" != "${LOCAL_BIN}/antigravity-generate-icons.py" ]; then
        mkdir -p "$LOCAL_BIN"
        cp -f "$gen_py" "${LOCAL_BIN}/antigravity-generate-icons.py" 2>/dev/null || sudo -n cp -f "$gen_py" "${LOCAL_BIN}/antigravity-generate-icons.py" 2>/dev/null || true
        chmod +x "${LOCAL_BIN}/antigravity-generate-icons.py" 2>/dev/null || true
        gen_py="${LOCAL_BIN}/antigravity-generate-icons.py"
    fi

    mkdir -p "$LOCAL_ICONS"
    for mb in "${LOCAL_ICONS}/antigravity-master-black.png" \
              "${REAL_HOME}/.antigravity-suite-manager/assets/antigravity-master-black.png" \
              "${APP_INSTALL_DIR}/resources/icon.png" \
              "/opt/antigravity2/resources/icon.png" \
              "/opt/antigravity/resources/icon.png"; do
        if [ -f "$mb" ]; then
            cp -f "$mb" "${LOCAL_ICONS}/antigravity-master-black.png" 2>/dev/null || true
            cp -f "$mb" "${LOCAL_ICONS}/antigravity-1.png" 2>/dev/null || true
            cp -f "$mb" "${LOCAL_ICONS}/antigravity.png" 2>/dev/null || true
            break
        fi
    done

    for mw in "${LOCAL_ICONS}/antigravity-master-white.png" \
              "${REAL_HOME}/.antigravity-suite-manager/assets/antigravity-master-white.png" \
              "${IDE_INSTALL_DIR}/resources/app/resources/linux/code.png" \
              "/opt/antigravity-ide/resources/app/resources/linux/code.png" \
              "/opt/antigravity/resources/app/resources/linux/code.png"; do
        if [ -f "$mw" ]; then
            cp -f "$mw" "${LOCAL_ICONS}/antigravity-master-white.png" 2>/dev/null || true
            cp -f "$mw" "${LOCAL_ICONS}/antigravity-ide.png" 2>/dev/null || true
            break
        fi
    done

    if [ ! -f "${LOCAL_ICONS}/antigravity-ide.png" ] && [ -f "${LOCAL_ICONS}/antigravity-master-black.png" ]; then
        cp -f "${LOCAL_ICONS}/antigravity-master-black.png" "${LOCAL_ICONS}/antigravity-ide.png" 2>/dev/null || true
    fi

    if [ -f "$gen_py" ]; then
        python3 "$gen_py" \
            --acc1 "${ACC1_ICON_THEME}" \
            --acc1-color "${ACC1_EMBLEM_COLOR}" \
            --acc2 "${ACC2_ICON_THEME}" \
            --acc2-color "${ACC2_EMBLEM_COLOR}" \
            --acc2-recolor "${ACC2_RECOLOR}" \
            --ide "${IDE_ICON_THEME}" \
            --ide-color "${IDE_EMBLEM_COLOR}" \
            --save-config 2>/dev/null || python3 "$gen_py" 2>/dev/null || true
    fi
}
