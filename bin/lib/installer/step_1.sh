#!/usr/bin/env bash
# Step 1: Check Platform & Prerequisites

step_1_prerequisites() {
    echo -e "\n${BLUE}[Step 1/8] $(get_step_name 1)...${NC}"
    if [ -f /etc/os-release ]; then
        # shellcheck source=/dev/null
        . /etc/os-release
        if [[ "${ID:-}" != "ubuntu" && "${ID_LIKE:-}" != *"debian"* && "${ID_LIKE:-}" != *"ubuntu"* && "${ID:-}" != "debian" ]]; then
            echo -e "${YELLOW}[INFO] Detected distribution: ${NAME:-Linux}. Designed for Debian-based systems with .desktop support.${NC}"
        fi
    fi

    local MISSING=()
    for cmd in python3 gcc tar curl; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            MISSING+=("$cmd")
        fi
    done

    if [ ${#MISSING[@]} -gt 0 ]; then
        echo -e "${RED}[ERROR] Missing required packages: ${MISSING[*]}${NC}"
        echo -e "${YELLOW}Please install them first (e.g. sudo apt install ${MISSING[*]})${NC}"
        return 1
    fi
    echo -e "${GREEN}[OK] Core dependencies verified.${NC}"
}
