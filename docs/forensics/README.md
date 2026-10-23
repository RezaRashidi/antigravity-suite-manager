# Antigravity Suite: Comprehensive Debugging & Forensics Guide

This document records the end-to-end diagnostic methodology, reverse-engineering techniques, root causes, and verification steps used to solve the Antigravity Suite conversation synchronization, empty sidebar, and profile disparity anomalies.

---


## Modular Index

- [1. Architectural Overview & Telemetry Chain](01_architectural_overview_telemetry_chain.md)
- [2. Issue 1: Empty Sidebar (0 Chats Rendered) — The Protobuf Tag 20 Gate](02_empty_sidebar_0_chats_rendered_the_protobuf_t.md)
- [3. Issue 2: Account 1 "Flash & Collapse" (Visible for 2s, Then Only Old Chats)](03_account_1_flash_collapse_visible_for_2s_then.md)
- [4. Issue 3: Rogue Symlink Causing Schema Version Crash](04_rogue_symlink_causing_schema_version_crash.md)
- [5. Issue 4: Metadata Inode Stagnation in Fast-Path Caching](05_metadata_inode_stagnation_in_fast_path_cachin.md)
- [7. Issue 5: User Prompt Leaking into Conversation Titles & Bubbles](06_user_prompt_leaking_into_conversation_titles.md)
- [8. Issue 6: App (Hub) Showing IDE Chats & Disappearing on Click](07_app_hub_showing_ide_chats_disappearing_on_cli.md)
- [9. Issue 7: Hardcoded Prompt Maps & Privacy Violations](08_hardcoded_prompt_maps_privacy_violations.md)
- [10. Issue 8: Audit Trail Deficit & Daemon Race Conditions](09_audit_trail_deficit_daemon_race_conditions.md)
- [11. Issue 9: Pinned Chats Displaying "2027y" (Year-1 / Epoch 0 Timestamp Bug)](10_pinned_chats_displaying_2027y_year_1_epoch_0.md)
- [12. Issue 10: Asymmetric Chat Deletion & Infinite Loading Spinner](11_asymmetric_chat_deletion_infinite_loading_spi.md)
- [13. Issue 11: IDE vs. App Title Discrepancy (Language Server Checkpoint Step 23)](12_ide_vs_app_title_discrepancy_language_server.md)
- [14. Issue 12: Orphaned Ghost Conversations Cleanup](13_orphaned_ghost_conversations_cleanup.md)
- [15. Issue 13: Antigravity 1 White System Tray Icon Disparity](14_antigravity_1_white_system_tray_icon_disparit.md)
- [16. Issue 14: Dynamic Workspace Discovery & Elimination of Static Container Assumptions](15_dynamic_workspace_discovery_elimination_of_st.md)
- [17. Issue 15: Decoupling Hardcoded System Paths: Default `/opt/*`, Account 2 Profile, Chromium Tray Temp Cache](16_decoupling_hardcoded_system_paths_default_opt.md)
- [18. Issue 16: F5 Backend Reload Failure (Stale Handler, Empty Try Block, and Patch Skip Guard)](17_f5_reload_stale_handler_empty_try_patch_skip.md)
- [19. Issue 17: Systemic 2027y Timestamp Distortion & Go time.Time Zero-Value Wire Format](19_systemic_2027y_timestamp_distortion_and_go_zero_value_wire_format.md)
- [20. Issue 18: Watcher Daemon Self-Trigger Loop (app_storage.json & WAL) and Physical DB Deletion Guard](20_watcher_daemon_self_trigger_loop_and_physical_db_deletion_guard.md)
- [21. Issue 19: Antigravity IDE Corruption Dialog & VS Code Checksum Integrity Synchronization](21_ide_installation_corrupt_checksum_integrity_fix.md)
- [22. Issue 20: Elimination of Hardcoded Account Scripts & Dynamic Multi-Instance Architecture](22_elimination_of_hardcoded_account_scripts_and_unified_dynamic_launchers.md)
- [23. Issue 21: Self-Update Engine & Background Service Orchestration](23_self_update_engine_and_background_service_orchestration.md)
- [24. Issue 22: Mid-Session Title Mutation & Test Suite Isolation Leak](24_mid_session_title_mutation_and_test_isolation_leak.md)
- [25. Issue 23: Consumer vs. Enterprise OAuth Client ID Collision & "NO LICENSE" Denial](25_consumer_vs_enterprise_oauth_client_id_collision_and_license_denial.md)
- [26. Issue 24: Cross-Conversation Session Splicing & Transcript Reconstitution](26_cross_conversation_session_leakage_and_transcript_splicer.md)
- [27. Issue 25: Workspace Fallback Title Collision & Multilingual Prompt Synthesis](27_workspace_fallback_title_collision_and_multilingual_prompt_synthesis.md)
- [28. Issue 26: Native "Open in IDE" Titlebar Button Discovery, Reverse Engineering & Independent Patch](28_native_open_in_ide_button_restoration_and_patch.md)
- [29. Issue 27: GNOME Keyring Unlock Prompt Regression, Phantom Account 2 Isolation & IDE URI Routing](29_keyring_unlock_prompt_regression_phantom_account2_and_ide_uri_routing.md)
- [30. Summary Checklist for Future Diagnostics](18_summary_checklist_for_future_diagnostics.md)
