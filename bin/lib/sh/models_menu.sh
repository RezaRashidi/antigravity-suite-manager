#!/usr/bin/env bash
# Interactive menu for Custom Models and Multi-Provider management

custom_models_menu() {
    local mpy; mpy="$(get_models_py)"
    while true; do
        echo -e "\n\033[0;36m=====================================================\033[0m"
        echo -e "\033[1;36m       Antigravity Custom Model Management           \033[0m"
        echo -e "\033[0;36m=====================================================\033[0m"
        echo "1) View Configured Providers & Active Models"
        echo "2) Add / Register New Provider (Base URL + Token)"
        echo "3) Discover & Fetch Available Models from Provider"
        echo "4) Enable / Select Specific Models (or All Models)"
        echo "5) Test Provider Connection & AI Response Speed"
        echo "6) Model Proxy Service Status & Controls"
        echo "7) Connect / Apply Custom Models to Antigravity IDE"
        echo "8) Restore Antigravity IDE to Official Google Gemini"
        echo "9) Inject Custom Models Settings UI into Antigravity App (Patch)"
        echo "10) Revert In-App Custom Models UI from App (Unpatch)"
        echo "0) Return to Main Menu"
        echo -e "\033[0;36m-----------------------------------------------------\033[0m"
        read -rp "Select an option [0-10]: " opt
        case "$opt" in
            1) python3 "$mpy" list ;;
            2) _prompt_add_provider ;;
            3) _prompt_fetch_models ;;
            4) _prompt_select_models ;;
            5) _prompt_test_provider ;;
            6) _prompt_proxy_controls ;;
            7) python3 "$mpy" apply-ide ;;
            8) python3 "$mpy" restore-ide ;;
            9) FORCE_INSTALL=true patch_models_app ;;
            10) unpatch_models_app ;;
            0) break ;;
            *) echo -e "\033[0;31mInvalid option.\033[0m" ;;
        esac
    done
}
