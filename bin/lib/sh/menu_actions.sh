#!/usr/bin/env bash
# Action handlers for interactive menu options

menu_action_history_mode() {
    read -rp "Enter instance type [app/ide]: " stype
    read -rp "Enter instance id/name: " sid
    read -rp "Enter mode [shared/isolated]: " smode
    set_history_mode "$stype" "$sid" "$smode"
}

menu_action_remove_instance() {
    read -rp "Enter instance type [app/ide]: " rtype
    read -rp "Enter instance id/name: " rid
    remove_instance "$rtype" "$rid"
}

menu_action_export() {
    echo -e "\nSelect Export Category:"
    echo "1) Full Bundle (History + Suite Configs, Skills, Rules, MCP, Accounts)"
    echo "2) Conversation History Only (Chats, Brain, Summaries)"
    echo "3) Suite Configurations Only (Rules, Skills, Plugins, MCP, Accounts)"
    read -rp "Choose [1-3, Default: 1]: " ecat
    read -rp "Enter output destination path [Enter for default]: " edest
    case "$ecat" in
        2) export_history ${edest:+"$edest"} ;;
        3) export_suite ${edest:+"$edest"} ;;
        *) export_all ${edest:+"$edest"} ;;
    esac
}

menu_action_import() {
    read -rp "Enter path to archive (.tar.gz) to import: " iarc
    if [ -n "$iarc" ]; then
        import_all "$iarc"
    else
        log_err "No archive path provided."
    fi
}

menu_action_backups() {
    echo -e "\nManage Backups:"
    echo "1) List Available Snapshots"
    echo "2) Create Instant Snapshot"
    echo "3) Restore From Snapshot"
    read -rp "Choose [1-3, Default: 1]: " bcat
    case "$bcat" in
        2)
            read -rp "Enter snapshot label [default: manual]: " blbl
            manage_backups create --label "${blbl:-manual}"
            ;;
        3)
            read -rp "Enter path to backup archive (.tar.gz): " barc
            manage_backups restore "$barc"
            ;;
        *)
            manage_backups list
            ;;
    esac
}
