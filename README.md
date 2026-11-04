# Antigravity Suite Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![OS: Linux](https://img.shields.io/badge/OS-Ubuntu%20%7C%20Debian%20%7C%20Linux-E95420.svg?logo=linux)](#quick-install)
[![Multi-Account](https://img.shields.io/badge/Multi--Account-Per--Chat%20Selector-success.svg)](#1--per-chat-multi-account-selector--subagent-swarms)
[![Custom Models](https://img.shields.io/badge/Custom%20Models-OpenAI%20%7C%20Anthropic%20%7C%20Ollama-blue.svg)](#2--custom-models--multi-provider-gateway)
[![Unified Workspace](https://img.shields.io/badge/Unified%20Workspace-App%20%2B%20IDE%20v2.6.0-purple.svg)](#3--unified-app--ide-workspace--one-shot-chat-migrator)
[![RTL Support](https://img.shields.io/badge/RTL-Persian%20%26%20Arabic-green.svg)](#6--first-class-persian--arabic-rtl-typography)

A lightweight, powerful Linux management suite and runtime booster for **Google Antigravity** (Desktop App) and **Antigravity IDE** (VS Code edition).

Eliminates quota exhaustion bottlenecks, unlocks third-party AI models (Claude, OpenAI, DeepSeek, Ollama), bridges the Desktop App and IDE into a unified database, and injects essential power-user productivity tools.

---

## ⚡ Quick Install

Install the complete Antigravity Suite in one command:

```bash
curl -fsSL https://raw.githubusercontent.com/RezaRashidi/antigravity-suite-manager/main/install.sh | bash
```

To update an existing installation anytime:

```bash
~/manage-antigravity.sh update
```

Open the modern interactive Control Center:

```bash
~/manage-antigravity.sh center
```

---

## 🚀 Core Features

### 1. 🛡️ Per-Chat Multi-Account Selector & Subagent Swarms

Overcomes single-account lock-in and quota exhaustion by enabling granular, per-conversation Google account selection directly inside the prompt bar.

```
+-----------------------------------------------------------------------------------+
|               Antigravity Desktop App / Antigravity IDE                           |
|                                                                                   |
|  [Model: Gemini 2.0 Pro ▼]  [@ Account: work@gmail.com ▼]  [ Send ➤ ]            |
|                             |                                                     |
|                             +--> ● user1@gmail.com       [78% Quota] [Usage ›]    |
|                                  ● work@gmail.com        [Active]    [Usage ›]    |
|                                  + [ + Add Account ]    [ Refresh ]               |
+-----------------------------------------------------------------------------------+
```

- **Per-Conversation Account Binding**: Pin Conversation A to personal Gmail, Conversation B to a Google One AI Premium account, and Conversation C to a work account with independent quotas.
- **Subagent Dynamic Swarm Allocator**: When invoking subagents, the suite automatically allocates idle connected accounts so parallel subagents work concurrently without draining your active conversation's quota.
- **Live Quota Telemetry**: Hover over **Usage ›** to inspect real-time weekly and 5-hour reset timers for Gemini and Claude models.
- **In-Chat Slash Commands**:
  - `/whoami`: Displays active Google account, conversation binding, and quota status.
  - `/accounts`: Lists all registered vault accounts and real-time quotas.
  - `/switch <id|email>`: Instantly switches the current conversation to another account.

---

### 2. 🤖 Custom Models & Multi-Provider Gateway

Connect external AI providers directly into the native Antigravity UI:

- **Universal Multi-Provider Support**: Use Anthropic Claude 3.5 Sonnet, OpenAI GPT-4o, DeepSeek-V3/R1, Ollama, OpenRouter, LiteLLM, or vLLM directly inside Antigravity.
- **In-App Settings UI**: Seamlessly adds a "Custom Models" tab into Antigravity App Settings to manage providers, API keys, endpoints, and model discovery.
- **Wire-Format Gateway**: Automatically transforms Antigravity's internal Gemini protocol into standard OpenAI/Anthropic schemas, including function calling and tool execution.
- **Fast Model Selector Sync**: Adding or editing models reflects in the prompt-bar dropdown within 50ms without restarting the Language Server.

---

### 3. 🔄 Unified App & IDE Workspace & One-Shot Chat Migrator

Starting with Antigravity IDE **v2.6.0+**, the Desktop App and IDE natively share the exact same SQLite database at `~/.gemini/antigravity/conversation_summaries.db`.

- **Zero-Daemon Architecture**: Heavy background synchronization daemons have been retired, saving over 560MB of RAM and eliminating idle CPU wakeups.
- **One-Shot Chat Migrator (`migrate-chats`)**: Seamlessly transfers legacy chat histories stored in older v2.5.5 `state.vscdb` format into the modern unified v2.6.0+ database:
  ```bash
  # Check versions and inspect legacy chats without modifying anything:
  ~/manage-antigravity.sh migrate-chats --dry-run

  # Run one-shot migration:
  ~/manage-antigravity.sh migrate-chats
  ```

---

### 4. 🪟 Native "Open in IDE" Titlebar Button

Restores the official native titlebar button in the Antigravity Desktop App:

- **One-Click Hand-off**: Click the IDE icon in the App titlebar to instantly open the current workspace, active trajectory, and recent files directly in Antigravity IDE.
- **Zero Config**: Automatically discovers your Antigravity IDE installation and sets up IPC protocol bridges.

---

### 5. 🌿 Conversation Forking (`conversationForking`)

Branch conversations at any historical turn into the current workspace or an isolated Git worktree:

- Unlocks the `Fork Conversation` action button on assistant responses.
- Allows exploring alternative implementation paths without losing the context of your original session.

---

### 6. ✍️ First-Class Persian & Arabic RTL Typography

Integrated right-to-left typography patch from [antigravity-rtl](https://github.com/mmnaderi/antigravity-rtl):

- **Clean Bidirectional Layout**: Formats Persian and Arabic text correctly across message cards, prompts, and code blocks.
- **Vazirmatn Font**: Crisp, modern Persian typography with instant toggle via `Alt+R` (or `⌥R`).

---

## 🛠️ CLI Command Reference

Manage your Antigravity Suite with `~/manage-antigravity.sh <command>`:

| Command | Alias | Description |
| :--- | :--- | :--- |
| `center` | `menu`, `--menu` | Open the interactive Control Center dashboard |
| `status` | | Inspect installed versions, active patches, and cache |
| `detect` | `scan`, `find` | Scan system and discover all Antigravity installations |
| `update` | | Smart update all components and re-apply active patches |
| `migrate-chats` | `migrate` | One-shot migrate legacy chats (v2.5.5 $\to$ v2.6.0) |
| `multi-account` | `accounts` | Manage connected Google accounts, quotas & chat bindings |
| `trace` | `traffic` | Stream live multi-account request routing and token swaps |
| `subagents` | `sa` | Apply Subagent Dynamic Multi-Account & Swarm patch |
| `selector` | `patch-selector` | Apply the prompt-bar Account Selector patch to App & IDE |
| `patch-models` | `models-patch` | Inject Custom Models Settings UI into Desktop App |
| `open-ide` | `patch-open-ide` | Enable native "Open in IDE" titlebar button in Desktop App |
| `fork` | `patch-fork` | Enable conversation forking in App & IDE |
| `rtl` | `patch-rtl` | Apply Persian & Arabic RTL typography patch |
| `patch-all` | | Apply all active patches in verified dependency order |
| `unpatch` | `restore` | Revert all patches and restore pristine original binaries |

---

## 🎛️ Interactive Control Center

Launch the dashboard anytime by running:

```bash
~/manage-antigravity.sh center
```

From the Control Center, you can manage installations, trigger updates, toggle patches, migrate legacy history, and monitor quotas with single-keystroke hotkeys.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
