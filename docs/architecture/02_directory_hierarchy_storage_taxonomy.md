# Directory Hierarchy & Storage Taxonomy

All conversational state, session histories, code reasoning logs, and authentication tokens reside inside the target Gemini configuration directory:

```
~/.gemini/ (or ~/.gemide/)
├── jetski-standalone-oauth-token          # Primary Google OAuth2 credential cache
├── oauth_credentials.json                 # Google OAuth client ID and secrets
├── google_accounts.json                   # Account profiles metadata
├── config/
│   └── projects/                          # Workspace & Project mappings
│       └── <project-uuid>.json            # Maps workspace folderUri -> project UUID
├── cache/
│   └── antigravity-keyring-unavailable   # Sentinel forcing file-based credentials
└── antigravity/ (or antigravity-ide/)
    ├── conversation_summaries.db          # Master SQLite relational index
    ├── conversation_summaries.db-wal      # SQLite Write-Ahead Log
    ├── conversation_summaries.db-shm      # SQLite Shared Memory index
    ├── agyhub_summaries_proto.pb          # Protobuf binary conversation cache
    ├── jetbox_summaries.pb                # Secondary Protobuf binary index
    ├── conversations/                     # Granular trajectory SQLite databases
    │   ├── <conv-uuid-1>.db
    │   └── <conv-uuid-2>.db
    ├── brain/                             # Conversation artifacts, transcripts, scratchpads
    │   └── <conv-uuid>/
    │       ├── *.md                       # Markdown artifacts generated during chat
    │       ├── scratch/                   # Scratch scripts and temporary files
    │       └── .system_generated/
    │           ├── logs/
    │           │   ├── transcript.jsonl      # Compact conversation transcript
    │           │   └── transcript_full.jsonl # Complete un-truncated conversation log
    │           └── tasks/                 # Background task execution logs
    └── annotations/                       # Human-edited titles and flags
        └── <conv-uuid>.pbtxt              # Protobuf text format annotations
```

---
