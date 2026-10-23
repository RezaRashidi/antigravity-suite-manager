#!/usr/bin/env bash
# Options and examples documentation for Antigravity Suite Manager

show_help_options() {
    cat <<EOF
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
