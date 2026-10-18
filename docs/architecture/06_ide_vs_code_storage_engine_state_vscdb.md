# IDE VS Code Storage Engine (`state.vscdb`)

Antigravity IDE stores state inside SQLite LevelDB replacements (`state.vscdb`) at:
- **Global Storage**: `~/.config/Antigravity IDE/User/globalStorage/state.vscdb`
- **Workspace Storage**: `~/.config/Antigravity IDE/User/workspaceStorage/<workspace-hash>/state.vscdb`

### 6.1 `ItemTable` SQLite Schema & Keys

```sql
CREATE TABLE `ItemTable` (
    `key`   TEXT PRIMARY KEY,
    `value` TEXT -- Base64 encoded protobuf or JSON string
);
```

#### Critical Keys in `ItemTable`
1. **`antigravityUnifiedStateSync.trajectorySummaries`**:
   - Contains a Base64-encoded Protobuf `Topic` message:
     ```
     Topic (Message)
       Tag 1: repeated DataEntry data = 1
         Tag 1: key (string = conversation_uuid)
         Tag 2: value (Row message)
           Tag 1: value (string = base64-encoded CascadeTrajectorySummary bytes)
           Tag 2: e_tag (int64 = 0 or timestamp)
     ```
   - Antigravity IDE parses this key directly upon launch to populate the chat sidebar.
2. **`antigravityUnifiedStateSync`**:
   - Contains `UssState` message grouping topics (`trajectorySummaries`, `userStatus`, `models`).
3. **`antigravityUnifiedStateSync.sidebarWorkspaces`**:
   - JSON array associating project UUIDs with recent workspace paths.

---

### 6.2 Extension Host Topic Synchronization (`extension.js`)

Extracted from `/opt/antigravity/resources/app/extensions/antigravity/dist/extension.js`. The Antigravity extension binds directly to Electron's IPC bus to stream state topics into `state.vscdb`:

```javascript
// Source: extensions/antigravity/dist/extension.js (Topic Synchronization Engine)
async function syncTopic(topicContainer, cancellationToken) {
    const topicName = topicContainer.topic; // e.g. "trajectorySummaries", "userStatus"
    
    // 1. Initialize IPC subscription to native Go LS service
    const sub = await vscode.antigravityUnifiedStateSync.initIPCSubscription(topicName);
    let currentValue = (0, decodeProto.P2)(sub.initialValue);
    
    // 2. Listen to async state update stream
    for await (const updateEvent of (0, asyncIter.V)(
        vscode.antigravityUnifiedStateSync.onDidUpdateTopicIPC, 
        cancellationToken.signal
    )) {
        if (updateEvent.topic === topicName) {
            // 3. Serialize and push updated Protobuf blob into VS Code ItemTable in state.vscdb
            await vscode.antigravityUnifiedStateSync.pushSerializedUpdateIPC(
                (0, encodeProto.q9)(ProtobufSchema.Topic, updateEvent.payload)
            );
        }
    }
}
```

---
