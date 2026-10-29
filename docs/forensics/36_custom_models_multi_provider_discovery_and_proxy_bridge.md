# Forensic Case 36: Custom Models Multi-Provider Discovery, Selective Activation, and Local Proxy Bridge

## 1. Executive Summary

### 1.1 Incident & User Requirement
Google Antigravity (both the IDE and Desktop App) natively connects only to Google Cloud Code and Gemini endpoints (`cloudcode-pa.googleapis.com` / `generativelanguage.googleapis.com`), without any native UI mechanism to connect external LLM providers (e.g. OpenAI, Anthropic, OpenRouter, DeepSeek, Groq, Ollama, vLLM, or custom enterprise endpoints).

The user requested:
1. Full custom model support integrated into Antigravity Suite Manager, leveraging architectural insights from `https://github.com/vahapogut/antigravity-add-model`.
2. Support for multiple Base URLs and API tokens simultaneously (Multi-Provider).
3. Dynamic model discovery fetching the complete list of available models from each provider (`/v1/models` or compatible endpoints).
4. Dual selection capability: either displaying and enabling all models at once, or selectively picking specific models by identifier.
5. Live test validation using a real OpenAI-compatible endpoint:
   - Base URL: `https://api.example.com/v1`
   - Token: `sk-ca523b247038011e-8nmvcd-027e56a7`
   - Target Model: `demo-model`
6. Strict adherence to codebase architecture rules: **every code file strictly `<= 100 lines`**.

---

## 2. Technical Architecture & Component Breakdown

### 2.1 Storage & Configuration Schema (`src/antigravity_suite/models/config.py`)
- Standard config path: `~/.gemini/antigravity/custom_models.json`.
- Schema normalization: supports both dictionary-based and list-based provider entries with fallback defaults (`version`, `providers`, `models`).
- File security: writes atomically using PID-suffixed temporary files with restrictive `0o600` permissions.

### 2.2 Remote Model Discovery (`src/antigravity_suite/models/discovery.py`)
- Standard library implementation using `urllib.request` (zero external pip dependencies).
- Candidate URL generation: intelligently tests candidate URLs (`{base_url}/models`, `{base_url}/v1/models`).
- Bearer token authentication, 10s configurable timeout, and SSL context handling.

### 2.3 Catalog Parsing & Capability Extraction (`src/antigravity_suite/models/parser.py`)
- Universal parsing engine supporting OpenAI `data` arrays, Ollama `models` arrays, and raw lists.
- Capability detection: parses model names, details, and families to identify vision (`vision`, `clip`, `mllama`, `vl`) and reasoning/thinking (`thinking`, `reasoning`, `deepseek-r1`, `o1`).
- Context length extraction: parses explicit context keys or extracts from regex patterns (`128k`, `1m`).

### 2.4 Selective Activation & ID Isolation (`src/antigravity_suite/models/selector.py`)
- Collision prevention: standardizes model IDs into collision-free identifiers `models/{provider}-{model_id}`.
- Dual activation modes:
  - `enable_all_models`: activates the entire catalog under the provider.
  - `enable_selected_models`: activates only targeted model IDs while preserving disabled states for others.
  - `toggle_model`: toggles individual model flags.

### 2.5 Endpoint Testing & Latency Benchmarking (`src/antigravity_suite/models/tester.py`)
- Sends minimal chat completion test payloads (`{"model": ..., "messages": [{"role": "user", "content": prompt}], "max_tokens": 16}`).
- Measures round-trip latency in milliseconds.
- Validates token validity and endpoint responsiveness before activation.

### 2.6 Antigravity IDE Integration Adapter (`src/antigravity_suite/models/ide_adapter.py`)
- Locates Antigravity IDE user configuration in `~/.config/Antigravity IDE/User/settings.json`.
- Manages automatic backup (`settings.json.bak`) prior to modification.
- `apply_ide_proxy_url`: configures `jetski.cloudCodeUrl = "http://127.0.0.1:50999"`.
- `restore_ide_proxy_url`: safely removes or reverts the override to restore official Google Gemini endpoints.

### 2.7 Proxy Daemon Supervisor (`src/antigravity_suite/models/proxy_daemon.py`)
- Supervises local model proxy running on port `50999`.
- Multi-layer status check: queries HTTP health check (`/_addon/health`) and TCP socket connectivity.
- Reads active PID from `~/.gemini/antigravity/.ide-proxy/state.json` or PID lock files.
- Integrates with the vendored desktop service engine (`vendor/antigravity-model-proxy/scripts/desktop-service.mjs`).

---

## 3. CLI & Bash Menu Integration

- **Python CLI Entry Point**: `bin/antigravity-models.py` -> `src/antigravity_suite/cli/models.py`.
- **Modular CLI Operations**: `src/antigravity_suite/cli/models_ops.py` and `models_proxy_ops.py`.
- **Bash Integration**: `bin/lib/sh/custom_models.sh` and `bin/lib/sh/models_menu.sh`.
- **Master Menu**: Added Option 39 `Custom Models (Multi-Provider, Discovery & Selection)` and CLI subcommand `manage-antigravity.sh models`.

---

## 4. Verification & Live Validation Results

### 4.1 Live Provider Discovery & Test on `api.example.com`
- Provider registered: `AIGateway` with Base URL `https://api.example.com/v1`.
- Discovery successfully fetched 36 models including `demo-model`, `cx/gpt-6.1-sol`, `ag/claude-sonnet-5-5`.
- Selective activation executed: `demo-model` and `ag/claude-sonnet-5-5` set to `[ON]`, remaining 34 models set to `[OFF]`.
- End-to-end latency benchmark on model `demo-model`: successfully returned response `pong` with 2815 ms latency.
- IDE configuration verified: `jetski.cloudCodeUrl` applied and verified in `settings.json`.

### 4.2 Strict Line Count Audit (All <= 100 lines)
```
   84 src/antigravity_suite/models/parser.py
   89 src/antigravity_suite/models/selector.py
   95 src/antigravity_suite/models/proxy_daemon.py
   69 src/antigravity_suite/models/__init__.py
   92 src/antigravity_suite/models/ide_adapter.py
   67 src/antigravity_suite/models/config.py
   78 src/antigravity_suite/models/tester.py
   59 src/antigravity_suite/models/discovery.py
   88 src/antigravity_suite/cli/models_ops.py
   84 src/antigravity_suite/cli/models_proxy_ops.py
   72 src/antigravity_suite/cli/models.py
   27 bin/antigravity-models.py
   72 bin/lib/sh/custom_models.sh
   87 bin/lib/sh/models_menu.sh
   61 tests/test_custom_models_cli.py
   54 tests/test_custom_models_config.py
   55 tests/test_custom_models_discovery.py
   50 tests/test_custom_models_ide_adapter.py
   54 tests/test_custom_models_parser.py
   59 tests/test_custom_models_proxy.py
   59 tests/test_custom_models.py
   50 tests/test_custom_models_selector.py
   48 tests/test_custom_models_tester.py
```
Maximum file length across the entire implementation: **95 lines**.

### 4.3 Automated Test Suite
- Executed `pytest`: **211 passed in 7.53s** (178 existing + 33 new tests).
- 100% test pass rate with zero warnings or regressions.
