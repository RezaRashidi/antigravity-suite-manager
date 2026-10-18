# High-Level Architecture & Process Mapping

Antigravity runs as two distinct Electron applications backed by a compiled Go language server runtime:

```mermaid
graph TD
    subgraph Antigravity Hub (Desktop App)
        HubUI["Electron Webview & React UI (/opt/antigravity2)"]
        HubStore["app_storage.json (~/.config/Antigravity)"]
        HubLS["Go Language Server (/opt/antigravity2/resources/bin/language_server)"]
        HubUI <--> HubStore
        HubUI <-->|"Loopback HTTPS ConnectRPC"| HubLS
    end

    subgraph Antigravity IDE (VS Code Fork)
        IDEUI["Monaco Editor & Workbench (/opt/antigravity/antigravity-ide)"]
        IDEvscdb["state.vscdb (~/.config/Antigravity IDE/.../globalStorage)"]
        IDEExt["VS Code Extension Host (resources/app/extensions/antigravity)"]
        IDELS["Go Language Server (bin/language_server_linux_x64.bin)"]
        IDEUI <--> IDEvscdb
        IDEUI <--> IDEExt
        IDEExt <-->|"Loopback HTTPS ConnectRPC"| IDELS
    end

    subgraph "Persistent Storage Engine (~/.gemini or ~/.gemide)"
        CS_DB[("conversation_summaries.db (Master Index)")]
        ConvDBs[("conversations/<uuid>.db (Granular Trajectory Steps)")]
        Brain[("brain/<uuid>/ (Transcripts & Markdown Artifacts)")]
        ProtoFast["agyhub_summaries_proto.pb (Fast Binary Cache)"]
        Projects["config/projects/<id>.json (Project & Workspace Configs)"]
    end

    HubLS <--> CS_DB
    HubLS <--> ConvDBs
    HubLS <--> Brain
    HubLS <--> ProtoFast
    HubLS <--> Projects

    IDELS <--> CS_DB
    IDELS <--> ConvDBs
    IDELS <--> Brain
    IDELS <--> IDEvscdb
    IDELS <--> Projects
```

### Process & Path Inventory

| Component | Antigravity Hub (Desktop App) | Antigravity IDE (VS Code Fork) |
| :--- | :--- | :--- |
| **Main Binary** | `/opt/antigravity2/antigravity` | `/opt/antigravity/antigravity-ide` |
| **Language Server** | `/opt/antigravity2/resources/bin/language_server` | `/opt/antigravity/resources/app/extensions/antigravity/bin/language_server_linux_x64.bin` |
| **User Data Dir** | `~/.config/Antigravity/` | `~/.config/Antigravity IDE/` |
| **UI State File** | `~/.config/Antigravity/app_storage.json` | `~/.config/Antigravity IDE/User/globalStorage/state.vscdb` |
| **Default Root Dir**| `~/.gemini/antigravity/` | `~/.gemide/antigravity-ide/` (or `~/.gemini/antigravity/`) |

---
