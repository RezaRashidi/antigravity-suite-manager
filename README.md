# Antigravity Suite Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![OS: Linux](https://img.shields.io/badge/OS-Ubuntu%20%7C%20Debian%20%7C%20Linux-E95420.svg?logo=linux)](#-installation--getting-started)
[![Multi-Account](https://img.shields.io/badge/Multi--Account-Per--Chat%20Selector-success.svg)](#4-️-per-chat-multi-account-google-switching)
[![Custom Models](https://img.shields.io/badge/Custom%20Models-Claude%20%7C%20OpenAI%20%7C%20Ollama-blue.svg)](#5--custom-models--third-party-providers)

A powerful, all-in-one productivity suite for **Google Antigravity** (Desktop App) and **Antigravity IDE** on Linux. It eliminates quota bottlenecks, brings multi-account switching per chat, unlocks external AI models (Ollama, Claude, OpenAI, DeepSeek), enables parallel subagent swarms, and restores essential power-user controls.

---

## ✨ Core Features

### 1. 🔄 One-Shot Chat Migrator
- **Seamless Database Upgrade**: Upgrades legacy chat histories from older versions (v2.5.5 `state.vscdb`) into the modern unified v2.6.0+ SQLite database (`conversation_summaries.db`).
- **Zero Data Loss**: Automatically detects, validates, and transfers your conversations, titles, and trajectories with automated safety backups.
- **No Background Daemons**: Runs as a fast one-time migration utility and exits immediately—no memory-heavy background daemons needed.

### 2. 🖥️ App Cloning & Multi-Instance with Shared History
- **Run Multiple Apps Side-by-Side**: Launch multiple independent Antigravity instances at the same time without process conflicts.
- **Full History Sharing**: Every cloned instance reads and writes to the same unified conversation database, giving you instant access to all your chats everywhere.
- **Taskbar De-Grouping & Visual Themes**: Dedicated launcher shortcuts, distinct icon colors (Black / White), and clean window separation in your desktop dock.

### 3. ⚡ Automated One-Line Install & Auto-Updates
- **Zero-Friction Setup**: One curl command downloads, detects your system architecture, installs the latest binaries, and configures everything automatically.
- **Smart Upstream Updates**: Check for and apply the latest Google Antigravity App and IDE updates with a single command (`update`), automatically reapplying all active enhancements cleanly.

### 4. 🛡️ Per-Chat Multi-Account Google Switching
- **Use Multiple Google Accounts in One App**: Connect personal, work, and Google One AI Premium accounts simultaneously.
- **Per-Conversation Account Binding**: Pin Conversation A to Account 1, Conversation B to Account 2, etc. Never run out of quotas again.
- **In-Prompt Account Dropdown**: Pick your active account right next to the model selector inside the chat prompt bar.
- **Live Quota Display**: View real-time weekly and 5-hour quota percentages and countdown timers for both Gemini and Claude.

### 5. 🤖 Custom Models & Third-Party Providers
- **Bring Your Own AI**: Connect external providers directly into the native Antigravity interface—including Anthropic Claude, OpenAI, DeepSeek, OpenRouter, and local Ollama.
- **In-App Settings UI**: Add API keys, endpoints, and custom models directly from the Antigravity App settings page.
- **Zero Latency Switch**: Custom models appear instantly in the chat dropdown alongside native models.

### 6. 🐝 Subagent Swarms with Multi-Account Scaling
- **Parallel AI Workflows**: When launching autonomous subagents to write code, conduct research, or run background tests, the suite dynamically leases idle connected Google accounts.
- **Quota Protection**: Subagent operations run on separate accounts so they never exhaust the quota of your main conversation.

### 7. 🧪 Unified Experiments, Forking, Telemetry & Power Features (`[EX]`)
- **Experiment Flags & Controls (`Flags`)**: Safe curated 17-flag & config switcher (`~/.config/antigravity/experiments.json`) synced seamlessly across the in-process App DevUI server (`AGY_DEV_UI_URL`), IDE workbench, router `listExperiments`/`fetchConfig`, and `localStorage` without clobbering user overrides.
- **Conversation Forking & Open in IDE**: Merged into one atomic pass — unlocks branch/historical-step/worktree forking plus the toggleable native `"Open in IDE"` titlebar button.
- **Native Context Ring, `models.dev` Cost Repricer & Telemetry**: Restores the context window ring, reprices token spend against live `models.dev` rates, displays live `tok/s`, `TTFT`, cache hit percentage, cache drop alerts, subagent cost summaries, and per-turn metadata with a consistent right-footer gauge icon.
- **Productivity & Layout Controls**: Includes **Compact Layout**, **Full-Text Chat Search** inside the conversation picker, **`File Context Menu (#L:C)`** (`Attach to Chat`, `Copy Path`, `Reveal in Folder`, `Open Externally`), **`Artifact Pane Width`** (`Default` / `Wide` / `Full`), **`Chats / Project`** limit (`Default (6)` / `10` / `20` / `All`), experimental **`Context Target`** (`Default` / `256K` / `500K` / `1M`), and race-free **`Restart`**.

### 8. 📊 Multi-Account Usage & Spend Analytics (`usage` & In-App `Usage`)
- **Terminal Usage Report (`[TU]` / `usage`)**: Read-only scanner across `transcript.jsonl` trajectories and CLI sessions with account attribution, Cache Hit Rate, USD spend, and `models.dev` rate caching.
- **In-App Multi-Account Dashboard (`Usage`)**: Visual modal inside App and IDE with per-account and combined filtering, `Today` / `Weekly` / `30 Days` / `All Time` ranges, 53-week SVG activity heatmap, model share breakdown, and recent session jump links.

### 9. 🪟 X11 Window Bounds Fix & Display Auto-Detection
- **Automatic Wayland / X11 Detection**: Launchers dynamically detect the active display server (`WAYLAND_DISPLAY` / `DISPLAY`) and configure Chromium Ozone flags accordingly instead of forcing X11 everywhere.
- **X11 Maximize & Resize Viewport Fix (`patch-window`)**: Standalone App ASAR patch that eliminates the App v2.30+ X11 `BaseWindow` bottom viewport cutoff during maximize/unmaximize/resize transitions.

### 10. ⇄ Internal Smart RTL & Typography Engine (`rtl`)
- **Zero-Dependency Self-Contained Patch**: Replaces external `npx antigravity-rtl` downloads and `patch_rtl_v234_shim.js` with an in-house patcher (`bin/lib/patch/rtl/`) compatible with both App (`await`/`void win.loadURL`) and IDE while preserving Multi-Account hooks across patch/unpatch cycles.
- **Code-Stripped & Streaming-Safe Direction**: Strips inline `<code>`, URLs, file paths, and `@mention` pills before classifying direction, keeps `WeakMap` memoization over historical turns, and updates streamed replies live even while typing in the prompt box.
- **Table-Safe RTL, OS Fonts & Typography Controls**: Reverses Persian table columns right-to-left via `table[dir="rtl"]` (correcting cell dividers) while locking `.md-table-host` and `.md-table-scroll` to LTR so width bleed and horizontal scrolling remain intact; aligns Persian prompt bubbles to the right, populates font & weight dropdowns directly from OS `fc-list` metadata (`100–900`), and provides uniform `<select>` controls for `Font Weight`, `Line Height` (`1.2–2.5`), and `Font Size` (`11px–24px`) across chat prose and prompt bubbles.

---

## 📥 Installation & Getting Started

### Quick Install (One Command)
Run this command in your Linux terminal to install the complete suite:

```bash
curl -fsSL https://raw.githubusercontent.com/RezaRashidi/antigravity-suite-manager/main/install.sh | bash
```

### Launch Interactive Control Center
Open the terminal dashboard to manage everything with single-key shortcuts:

```bash
~/manage-antigravity.sh center
```

### Update Anytime
Keep your App, IDE, and enhancements up to date:

```bash
~/manage-antigravity.sh update
```

---

## ⌨️ Common Commands

| Command | What it does |
| :--- | :--- |
| `~/manage-antigravity.sh center` | Open the interactive graphical terminal dashboard |
| `~/manage-antigravity.sh update` | Check for updates and upgrade App + IDE automatically |
| `~/manage-antigravity.sh accounts` | Manage connected Google accounts, quotas & chat bindings |
| `~/manage-antigravity.sh migrate-chats` | One-shot migrate legacy chats into modern unified database |
| `~/manage-antigravity.sh status` | Show installed versions, cache status, and active patches |
| `~/manage-antigravity.sh patch-all` | Apply all active enhancements in verified order |
| `~/manage-antigravity.sh experiments` | Apply unified Experiments, Forking, Cost, Telemetry & Open-IDE patch (`unpatch-experiments` to revert) |
| `~/manage-antigravity.sh usage` | Show read-only multi-account token usage, Cache Hit Rate & USD spend report |
| `~/manage-antigravity.sh rtl` | Apply internal smart RTL & typography patch to App and IDE (`unpatch-rtl` to revert) |
| `~/manage-antigravity.sh patch-window` | Apply standalone App X11 window bounds fix (`unpatch-window` to revert) |
| `~/manage-antigravity.sh unpatch` | Safely revert all patches back to original pristine state |

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
