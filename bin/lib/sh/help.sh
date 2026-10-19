#!/usr/bin/env bash
# Help and usage documentation for Antigravity Suite Manager

show_help() {
    cat <<EOF
Antigravity & Antigravity IDE Suite Manager

Usage:
  $(basename "$0") [command] [options]

Commands:
  status        Check installed vs target versions, patch statuses, and cache
  detect        Scan and identify all installed Antigravity instances on system (aliases: scan, find)
  install       Install Antigravity suite [all|app|ide] (default: all)
  all           Install / update both Antigravity Apps (Account 1 & 2), IDE, F5 patch, and RTL
  app           Install / update Antigravity App (Both Accounts, RTL, and F5)
  ide           Install / update Antigravity IDE and RTL patch
  app1          Configure Account 1 launcher and desktop shortcut
  app2          Configure Account 2 isolated profile, shared history, and shortcuts
  ide-shortcuts Configure Antigravity IDE launcher and desktop shortcut
  set-icons     Configure or re-apply icons (Black/White and Acc 2 Recolor)
  merge-history Sync & backfill conversation history across all profiles/IDEs (alias: merge)
  keyring       Configure & switch credential storage (GNOME Keyring vs Normal File Storage)
                Subcommands: status | set [app1|app2|ide|all] [normal|gnome] | purge
  paths         Configure & switch Antigravity installation paths (interactive or CLI)
  wizard        Launch the interactive step-by-step setup wizard (alias: setup)
  create-instance Create arbitrary App or IDE instances with shared/isolated history (alias: add)
  list-instances  Show all created App and IDE instances and their history status (alias: list)
  set-history     Toggle instance history between 'shared' and 'isolated'
  remove-instance Delete an App or IDE instance and archive its profile (alias: remove)
  f5            Re-apply manual F5 backend reload sync patch
  rtl           Apply / re-apply antigravity-rtl to App and IDE
  update        Smart update components [all|app|ide|rtl|f5|checksums|repo|services] (preserves user data)
  update-repo   Update Antigravity Suite Manager repository, recompile, and redeploy
  restart-services Restart systemd history sync and X11 icon injector daemons
  update-rtl    Update antigravity-rtl to latest and re-apply
  update-f5     Re-apply manual F5 backend reload sync patch (alias for update f5)
  checksums     Verify and synchronize Antigravity IDE bundle integrity checksums
  export-history Export conversation history & brains to portable tarball [out]
  import-history Import & merge conversation history from archive <file>
  export-suite  Export suite configurations (rules, skills, plugins, MCP, accounts) [out]
  import-suite  Import & merge suite configurations from archive <file>
  export-all    Export full unified migration bundle (History + Configs) [out]
  import-all    Auto-detect & import any Antigravity archive <file>
  backups       Manage safety backups (list | create [--label <name>] | restore <file>)
  clean-cache   Remove cached tarballs in /tmp/antigravity-cache
  help          Show this help message

Options:
  --force, -f                 Force re-download and re-installation even if already at latest version
  --no-cache                  Bypass /tmp archive cache and force fresh download
  --cache-dir <dir>           Override cache directory (default: /tmp/antigravity-cache)
  --app-url <url>             Override Antigravity App download URL (skips auto-discovery)
  --ide-url <url>             Override Antigravity IDE download URL (skips auto-discovery)
  --app-dir <path>            Override Antigravity App install directory (default: /opt/antigravity2)
  --ide-dir <path>            Override Antigravity IDE install directory (default: /opt/antigravity)
  --acc1-icon <black|white>   Set Antigravity 1 icon theme (black or white)
  --acc2-icon <black|white>   Set Antigravity 2 icon theme (black or white)
  --acc2-recolor <true|false> Toggle color recoloring for Antigravity 2 (true=Violet, false=original)
  --ide-icon <white|black>    Set Antigravity IDE icon theme (white or black)
  --skip-rtl                  Skip RTL patching step
  --skip-f5                   Skip F5 reload patching step

Examples:
  $(basename "$0") status
  $(basename "$0") paths
  $(basename "$0") wizard
  $(basename "$0") keyring status
  $(basename "$0") keyring set app1 normal
  $(basename "$0") keyring purge
  $(basename "$0") detect
  $(basename "$0") install
  $(basename "$0") update
  $(basename "$0") set-icons
EOF
}
