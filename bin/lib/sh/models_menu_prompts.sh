#!/usr/bin/env bash
# Prompt helpers for custom models interactive menu

_prompt_add_provider() {
    local mpy; mpy="$(get_models_py)"
    echo -e "\n\033[1;34m--- Add New Custom Model Provider ---\033[0m"
    read -rp "Provider Name (e.g., ODDirect, Ollama, OpenRouter): " pname
    read -rp "Base URL (e.g., https://ai.odirect.app/v1): " pbaseUrl
    read -rp "API Token / Key (leave blank for local Ollama): " ptoken
    python3 "$mpy" add-provider --name "$pname" --url "$pbaseUrl" --token "$ptoken"
}

_prompt_fetch_models() {
    local mpy; mpy="$(get_models_py)"
    echo -e "\n\033[1;34m--- Fetch Available Models from Provider ---\033[0m"
    read -rp "Provider ID or Name: " pid
    python3 "$mpy" fetch --provider "$pid"
}

_prompt_select_models() {
    local mpy; mpy="$(get_models_py)"
    echo -e "\n\033[1;34m--- Enable / Select Models ---\033[0m"
    read -rp "Provider ID or Name: " pid
    echo "1) Enable ALL models from this provider"
    echo "2) Select specific model IDs (comma-separated)"
    read -rp "Choice [1-2]: " s_opt
    if [ "$s_opt" = "1" ]; then
        python3 "$mpy" enable-all --provider "$pid"
    else
        read -rp "Enter model IDs (e.g. reza, cx/gpt-6-sol): " s_ids
        python3 "$mpy" select --provider "$pid" --models "$s_ids"
    fi
}

_prompt_test_provider() {
    local mpy; mpy="$(get_models_py)"
    echo -e "\n\033[1;34m--- Test Connection & Benchmark Latency ---\033[0m"
    read -rp "Provider ID: " pid
    read -rp "Model ID to test (e.g. reza): " t_model
    python3 "$mpy" test --provider "$pid" --model "$t_model"
}

_prompt_proxy_controls() {
    echo -e "\n\033[1;34m--- Model Proxy Daemon Controls ---\033[0m"
    echo "1) Check Proxy Status & Health"
    echo "2) Start Model Proxy Daemon"
    echo "3) Stop Model Proxy Daemon"
    read -rp "Choice [1-3]: " p_opt
    case "$p_opt" in
        1) model_proxy_service_status ;;
        2) start_model_proxy_service ;;
        3) stop_model_proxy_service ;;
    esac
}
