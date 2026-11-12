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

### 7. 🌿 Restored Native Buttons (Fork & Open in IDE)
- **Fork Conversation Button**: Branch any chat at any message turn into a new trajectory or an isolated Git worktree without losing context.
- **Native "Open in IDE" Titlebar Button**: Restores the titlebar button to jump instantly from the Desktop App into Antigravity IDE with your current workspace and files loaded.

### 8. 🪟 X11 Window Bounds Fix & Display Auto-Detection
- **Automatic Wayland / X11 Detection**: Launchers dynamically detect the active display server (`WAYLAND_DISPLAY` / `DISPLAY`) and configure Chromium Ozone flags accordingly instead of forcing X11 everywhere.
- **X11 Maximize & Resize Viewport Fix (`patch-window`)**: Standalone App ASAR patch that eliminates the App v2.30+ X11 `BaseWindow` bottom viewport cutoff during maximize/unmaximize/resize transitions.

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
| `~/manage-antigravity.sh patch-window` | Apply standalone App X11 window bounds fix (`unpatch-window` to revert) |
| `~/manage-antigravity.sh unpatch` | Safely revert all patches back to original pristine state |

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
