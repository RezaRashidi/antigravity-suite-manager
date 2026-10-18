#!/usr/bin/env bash
# Interactive prompts for icon themes and emblem colors

prompt_acc1_icon() {
    echo -e "\n${BOLD}Configure Antigravity (Account 1):${NC}"
    read -rp "  Background Color [1: Black (default), 2: White]: " bg1
    case "$bg1" in
        2|white) ACC1_ICON_THEME="white" ;;
        *) ACC1_ICON_THEME="black" ;;
    esac
    echo -e "  Emblem Colors:"
    echo -e "    [1] Original Google Multi-Color (default)\n    [2] Violet / Magenta\n    [3] Royal Blue / Cyan"
    echo -e "    [4] Emerald Green\n    [5] Amber / Gold\n    [6] Ruby Red\n    [7] Monochrome Silver"
    read -rp "  Select Emblem Color [1-7, Default: 1]: " col1
    case "$col1" in
        2|violet|purple) ACC1_EMBLEM_COLOR="violet" ;;
        3|blue|cyan) ACC1_EMBLEM_COLOR="blue" ;;
        4|green|emerald) ACC1_EMBLEM_COLOR="green" ;;
        5|amber|gold|orange) ACC1_EMBLEM_COLOR="amber" ;;
        6|red|ruby) ACC1_EMBLEM_COLOR="red" ;;
        7|silver|monochrome|grey) ACC1_EMBLEM_COLOR="monochrome" ;;
        *) ACC1_EMBLEM_COLOR="original" ;;
    esac
}

prompt_ide_icon() {
    echo -e "\n${BOLD}Configure Antigravity IDE:${NC}"
    read -rp "  Background Color [1: White (default), 2: Black]: " bgi
    case "$bgi" in
        2|black) IDE_ICON_THEME="black" ;;
        *) IDE_ICON_THEME="white" ;;
    esac
    echo -e "  Emblem Colors:"
    echo -e "    [1] Original Google Multi-Color (default)\n    [2] Royal Blue / Cyan\n    [3] Violet / Magenta"
    echo -e "    [4] Emerald Green\n    [5] Amber / Gold\n    [6] Ruby Red\n    [7] Monochrome Silver"
    read -rp "  Select Emblem Color [1-7, Default: 1]: " coli
    case "$coli" in
        2|blue|cyan) IDE_EMBLEM_COLOR="blue" ;;
        3|violet|purple) IDE_EMBLEM_COLOR="violet" ;;
        4|green|emerald) IDE_EMBLEM_COLOR="green" ;;
        5|amber|gold|orange) IDE_EMBLEM_COLOR="amber" ;;
        6|red|ruby) IDE_EMBLEM_COLOR="red" ;;
        7|silver|monochrome|grey) IDE_EMBLEM_COLOR="monochrome" ;;
        *) IDE_EMBLEM_COLOR="original" ;;
    esac
}

prompt_acc2_icon() {
    echo -e "\n${BOLD}Configure Antigravity (Account 2):${NC}"
    read -rp "  Background Color [1: Black (default), 2: White]: " bg2
    case "$bg2" in
        2|white) ACC2_ICON_THEME="white" ;;
        *) ACC2_ICON_THEME="black" ;;
    esac
    echo -e "  Emblem Colors:"
    echo -e "    [1] Violet / Magenta (default)\n    [2] Original Google Multi-Color\n    [3] Royal Blue / Cyan"
    echo -e "    [4] Emerald Green\n    [5] Amber / Gold\n    [6] Ruby Red\n    [7] Monochrome Silver"
    read -rp "  Select Emblem Color [1-7, Default: 1]: " col2
    case "$col2" in
        2|original) ACC2_EMBLEM_COLOR="original" ;;
        3|blue|cyan) ACC2_EMBLEM_COLOR="blue" ;;
        4|green|emerald) ACC2_EMBLEM_COLOR="green" ;;
        5|amber|gold|orange) ACC2_EMBLEM_COLOR="amber" ;;
        6|red|ruby) ACC2_EMBLEM_COLOR="red" ;;
        7|silver|monochrome|grey) ACC2_EMBLEM_COLOR="monochrome" ;;
        *) ACC2_EMBLEM_COLOR="violet" ;;
    esac
    ACC2_RECOLOR="true"
    [ "$ACC2_EMBLEM_COLOR" = "original" ] && ACC2_RECOLOR="false"
}
