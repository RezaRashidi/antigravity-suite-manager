# Antigravity Hub & IDE: Storage Architecture & Reverse-Engineered Code Catalog

This technical specification and engineering reference documents the complete data storage mechanisms, file hierarchies, database schemas, Protobuf wire formats, reverse-engineered source components, and synchronization pipelines for **Google Antigravity Hub** (Desktop App) and **Antigravity IDE** (VS Code edition).

---

## Table of Contents
1. [High-Level Architecture & Process Mapping](#1-high-level-architecture--process-mapping)
2. [Directory Hierarchy & Storage Taxonomy](#2-directory-hierarchy--storage-taxonomy)
3. [Individual Conversation Storage (`<uuid>.db`)](#3-individual-conversation-storage-uuiddb)
   - [3.1 SQLite Schema](#31-sqlite-schema)
   - [3.2 Protobuf `step_payload` Wire Architecture](#32-protobuf-step_payload-wire-architecture)
   - [3.3 Raw Wire Hex & Decoded Payloads](#33-raw-wire-hex--decoded-payloads)
4. [Master Relational Index (`conversation_summaries.db`)](#4-master-relational-index-conversation_summariesdb)
   - [4.1 Database Schema & Indices](#41-database-schema--indices)
   - [4.2 Unread / "New" ("تازه") Badge Mechanics](#42-unread--new-تازه-badge-mechanics)
5. [Protobuf Wire Specifications & Go Struct Reflection](#5-protobuf-wire-specifications--go-struct-reflection)
   - [5.1 `CascadeTrajectorySummary` Go Reflection](#51-cascadetrajectorysummary-go-reflection)
   - [5.2 `ConversationAnnotations` Go Reflection](#52-conversationannotations-go-reflection)
6. [IDE VS Code Storage Engine (`state.vscdb`)](#6-ide-vs-code-storage-engine-statevscdb)
   - [6.1 `ItemTable` SQLite Schema & Keys](#61-itemtable-sqlite-schema--keys)
   - [6.2 Extension Host Topic Synchronization (`extension.js`)](#62-extension-host-topic-synchronization-extensionjs)
7. [Desktop App Storage & React UI Filtering (`app_storage.json`)](#7-desktop-app-storage--react-ui-filtering-app_storagejson)
   - [7.1 The React Double-Elimination Filter (`w.has(ta)`)](#71-the-react-double-elimination-filter-whasta)
   - [7.2 Pinned and Archived Membership Predicates](#72-pinned-and-archived-membership-predicates)
8. [Desktop App Electron Supervisor (`dist/languageServer.js`)](#8-desktop-app-electron-supervisor-distlanguageserverjs)
   - [8.1 Process Lifecycle & Auto-Restart Mechanics](#81-process-lifecycle--auto-restart-mechanics)
9. [Live ConnectRPC Loopback Protocol](#9-live-connectrpc-loopback-protocol)
   - [9.1 Zero-Restart Live Annotation Script](#91-zero-restart-live-annotation-script)
10. [Data Flow Lifecycle: Message Creation to Storage](#10-data-flow-lifecycle-message-creation-to-storage)
11. [Two-Way Synchronization Engine (`antigravity-suite-manager`)](#11-two-way-synchronization-engine-antigravity-suite-manager)
12. [Multi-Account Selector Architecture & Router Subsystem](12_multi_account_selector_architecture.md)

---


## Modular Index

- [1. High-Level Architecture & Process Mapping](01_high_level_architecture_process_mapping.md)
- [2. Directory Hierarchy & Storage Taxonomy](02_directory_hierarchy_storage_taxonomy.md)
- [3. Individual Conversation Storage (`<uuid>.db`)](03_individual_conversation_storage_uuid_db.md)
- [4. Master Relational Index (`conversation_summaries.db`)](04_master_relational_index_conversation_summarie.md)
- [5. Protobuf Wire Specifications & Go Struct Reflection](05_protobuf_wire_specifications_go_struct_reflec.md)
- [6. IDE VS Code Storage Engine (`state.vscdb`)](06_ide_vs_code_storage_engine_state_vscdb.md)
- [7. Desktop App Storage & React UI Filtering (`app_storage.json`)](07_desktop_app_storage_react_ui_filtering_app_st.md)
- [8. Desktop App Electron Supervisor (`dist/languageServer.js`)](08_desktop_app_electron_supervisor_dist_language.md)
- [9. Live ConnectRPC Loopback Protocol](09_live_connectrpc_loopback_protocol.md)
- [10. Data Flow Lifecycle: Message Creation to Storage](10_data_flow_lifecycle_message_creation_to_stora.md)
- [11. Two-Way Synchronization Engine (`antigravity-suite-manager`)](11_two_way_synchronization_engine_antigravity_su.md)
- [12. Multi-Account Selector Architecture & Router Subsystem](12_multi_account_selector_architecture.md)
