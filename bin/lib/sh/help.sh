#!/usr/bin/env bash
# Help and usage documentation for Antigravity Suite Manager

show_help() {
    cat <<EOF
Antigravity & Antigravity IDE Suite Manager

Usage:
  $(basename "$0") [command|options]

Interactive Modes:
  (no args)     Open the modern Antigravity Control Center (detected instances, hotkeys)
  --menu        Open the modern Antigravity Control Center (alias: --center, --control-center)
  --classic-menu Open the classic 29-item numbered bash menu
  -w, --wizard  Launch the interactive step-by-step setup wizard (prompts after each step)
  -s, --step <N|name>      Start execution from step N (1-8 or alias e.g. paths, icons)
  -o, --only-step <N|name> Execute only step N and exit (1-8 or alias e.g. paths, icons)

Commands:
  status        Check installed vs target versions, patch statuses, and cache
  detect        Scan and identify all installed Antigravity instances on system (aliases: scan, find)
  install       Install Antigravity suite [all|app|ide] (default: all)
  all           Install / update Antigravity Suite (App, IDE, F5 patch, and RTL)
  app           Install / update Antigravity App (RTL and F5 patches)
  ide           Install / update Antigravity IDE and RTL patch
  app1          Configure Primary App launcher and desktop shortcut
  app2          Configure Account 2 isolated profile, shared history, and shortcuts (optional)
  ide-shortcuts Configure Antigravity IDE launcher and desktop shortcut
  set-icons     Configure or re-apply icons (Black/White and Acc 2 Recolor)
  merge-history Sync & backfill conversation history across all profiles/IDEs (alias: merge)
  keyring       Configure & switch credential storage (GNOME Keyring vs Normal File Storage)
  paths         Configure & switch Antigravity installation paths (interactive or CLI)
  wizard        Launch the interactive step-by-step setup wizard (alias: setup)
  create-instance Create arbitrary App or IDE instances with shared/isolated history (alias: add)
  list-instances  Show all created App and IDE instances and their history status (alias: list)
  set-history     Toggle instance history between 'shared' and 'isolated'
  remove-instance Delete an App or IDE instance and archive its profile (alias: remove)
  f5            Apply manual F5 backend reload sync patch (isolated)
  unpatch-f5    Revert F5 backend reload sync patch
  selector      Apply prompt-bar account selector & multi-account patch (alias: patch-selector)
  unpatch-selector Revert prompt-bar account selector patch (preserves F5)
  fork          Apply experimental conversation forking patch to App and IDE (alias: patch-fork)
  unpatch-fork  Revert conversation forking patch
  open-ide      Enable native 'Open in IDE' titlebar button in App (alias: patch-open-ide)
  unpatch-open-ide Revert native 'Open in IDE' button patch
  unpatch       Restore clean unmodified original app.asar (revert all patches)
  rtl           Apply / re-apply antigravity-rtl to App and IDE
  unpatch-rtl   Revert RTL typography patch from App and IDE
  clean-data    Clean or purge user data and caches [app|ide|history|all]
  uninstall     Uninstall Antigravity binaries and shortcuts [all|app|ide] [--with-data|--keep-data]
  update        Smart update components [all|app|ide|rtl|f5|checksums|repo|services] (preserves user data & active patches)
  update-repo   Update Antigravity Suite Manager repository, recompile, and redeploy
  restart-services Restart systemd history sync and X11 icon injector daemons
  benchmark     Benchmark AI response speed, IPv6/proxy latency, and context bloat (alias: bench)
  multi-account Manage connected Google accounts, quotas & chat bindings (aliases: accounts, multiaccount)
  trace         Live stream multi-account request routing and token swaps (alias: traffic)
  export-history Export conversation history & brains to portable tarball [out]
  import-history Import & merge conversation history from archive <file>
  export-suite  Export suite configurations (rules, skills, plugins, MCP, accounts) [out]
  import-suite  Import & merge suite configurations from archive <file>
  export-all    Export full unified migration bundle (History + Configs) [out]
  import-all    Auto-detect & import any Antigravity archive <file>
  backups       Manage safety backups (list | create [--label <name>] | restore <file>)
  clean-cache   Remove cached tarballs in /tmp/antigravity-cache
  help          Show this help message
EOF
    show_help_options
}
