# Two-Way Synchronization Engine (`antigravity-suite-manager`)

To ensure bidirectional consistency between Desktop App and IDE without data loss:

1. **Ingest Phase (`vscdb_sync.py`)**:
   - Scans all discovered `state.vscdb` files across IDE profiles.
   - Extracts binary `CascadeTrajectorySummary` records from `ItemTable`.
   - Ingests new conversations (`u_id not in all_summaries`) into master `conversation_summaries.db`.
   - Refreshes authentic LLM-generated titles (Tag 1 `summary`) over user prompt fallbacks.
2. **Reconciliation Phase (`replicate_projects_order`)**:
   - Collects project UUIDs from all `app_storage.json` profiles and `config/projects/*.json`.
   - Propagates merged `projectsOrder` to every `app_storage.json` profile, neutralizing the `w.has(ta)` double-elimination filter.
3. **Distribution Phase (`distribution_pipeline.py`)**:
   - Writes consolidated summaries to `conversation_summaries.db`.
   - Generates and writes `agyhub_summaries_proto.pb`.
   - Encodes and writes unified state into all IDE `state.vscdb` databases.
   - Replicates atomic symlinks to all secondary instance profiles.
