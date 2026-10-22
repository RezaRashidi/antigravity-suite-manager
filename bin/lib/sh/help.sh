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
  f5            Apply manual F5 backend reload sync patch (isolated)
  unpatch-f5    Revert F5 backend reload sync patch
  selector      Apply prompt-bar account selector & multi-account patch (alias: patch-selector)
  unpatch-selector Revert prompt-bar account selector patch (preserves F5)
  fork          Apply experimental conversation forking patch to App and IDE (alias: patch-fork)
  unpatch-fork  Revert conversation forking patch
  unpatch       Restore clean unmodified original app.asar (revert all patches)
  rtl           Apply / re-apply antigravity-rtl to App and IDE
  update        Smart update components [all|app|ide|rtl|f5|checksums|repo|services] (preserves user data)
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

Options:
  -s, --step <N|name>         Start execution from step N (1-8 or alias e.g. paths, icons)
  -o, --only-step <N|name>    Execute only step N and exit (1-8 or alias e.g. paths, icons)
  -w, --wizard                Enable interactive step-by-step wizard
  -u, --update                Perform smart update of installed binaries & patches
  --update-repo               Update Suite Manager repository (git pull, build & deploy)
  --restart-services          Restart background systemd sync and X11 icon daemons
  -i, --install-antigravity   Force downloading and installing Antigravity binaries
  -y, --yes                   Run non-interactively with defaults
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

Setup Steps (1-8):
  1) Check System & Dependencies (aliases: prereqs, dep)
  2) Configure Installation Paths & Engines (aliases: paths, engines, detect)
  3) Prepare Directories & Compile Catmull-Rom Bicubic Resampler (aliases: resampler, scale)
  4) Install Management Tools & Master Icon Assets (aliases: deploy, tools, bin)
  5) Configure Visual Icon Themes & Recolor (aliases: icons, themes, recolor)
  6) Configure Credential Keyring Mode (aliases: keyring, creds)
  7) Download & Install Google Antigravity Binaries (aliases: install, download, binary)
  8) Setup Multi-Account Launchers & Unified Chat History Sync (aliases: sync, launchers, chat)

Examples:
  $(basename "$0")                  # Open modern Control Center
  $(basename "$0") status           # Check versions and patch statuses
  $(basename "$0") -w               # Run step-by-step wizard
  $(basename "$0") -s 2             # Start wizard from step 2
  $(basename "$0") -o 5             # Run only step 5 (icons)
  $(basename "$0") update           # Smart update all components
  $(basename "$0") multi-account    # Multi-account & quota manager
  $(basename "$0") keyring status   # Check keyring status
EOF
}
