#!/usr/bin/env bash
# Step 3: Prepare Directories & Compile C Bicubic Resampler

step_3_compile_resampler() {
    echo -e "\n${BLUE}[Step 3/8] $(get_step_name 3)...${NC}"
    mkdir -p "$TARGET_BIN" "$TARGET_ICONS" "$TARGET_CONF" "/tmp/antigravity-cache"
    if [ -f "${SCRIPT_DIR}/src/scale_icon.c" ]; then
        gcc -O3 -Wall "${SCRIPT_DIR}/src/scale_icon.c" -lm -o "${TARGET_BIN}/scale_icon"
        chmod +x "${TARGET_BIN}/scale_icon"
        echo -e "${GREEN}[OK] Resampler compiled to ${TARGET_BIN}/scale_icon${NC}"
    elif [ -f "${TARGET_BIN}/scale_icon" ]; then
        echo -e "${GREEN}[OK] Existing resampler found at ${TARGET_BIN}/scale_icon${NC}"
    else
        echo -e "${YELLOW}[WARN] src/scale_icon.c not found, skipping compilation.${NC}"
    fi
}
