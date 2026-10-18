#!/usr/bin/env bash
# Step naming and index mapping utilities

get_step_num() {
    case "$1" in
        1|[Pp]rereq*|[Dd]ep*) echo 1 ;;
        2|[Pp]ath*|[Ee]ngine*|[Dd]etect*) echo 2 ;;
        3|[Rr]esample*|[Ss]cale*|[Cc]ompile*) echo 3 ;;
        4|[Dd]eploy*|[Tt]ool*|[Bb]in*) echo 4 ;;
        5|[Ii]con*|[Tt]heme*|[Rr]ecolor*) echo 5 ;;
        6|[Kk]eyring*|[Cc]red*) echo 6 ;;
        7|[Ii]nstall*|[Dd]ownload*|[Bb]inary*) echo 7 ;;
        8|[Ll]auncher*|[Ss]ync*|[Cc]hat*) echo 8 ;;
        *) echo "$1" ;;
    esac
}

get_step_name() {
    case "$1" in
        1) echo "Check Dependencies & Prerequisites" ;;
        2) echo "Configure Installation Paths & Engines" ;;
        3) echo "Compile Catmull-Rom Bicubic Resampler (C)" ;;
        4) echo "Deploy Management Tools & Master Icons" ;;
        5) echo "Configure Visual Icon Themes & Recolor" ;;
        6) echo "Configure Credential Keyring Mode (Normal vs GNOME)" ;;
        7) echo "Download & Install Google Antigravity Binaries" ;;
        8) echo "Setup Multi-Account Launchers & 3-Way Chat Sync" ;;
        *) echo "Step $1" ;;
    esac
}
