# Protobuf Wire Specifications & Go Struct Reflection

Extracted from compiled Go ELF binary `/opt/antigravity2/resources/bin/language_server` (string tables and type descriptors).

### 5.1 `CascadeTrajectorySummary` Go Reflection

```go
// Extracted from Go runtime type reflection: package exa.language_server_pb
type CascadeTrajectorySummary struct {
    Summary                 string                     `protobuf:"bytes,1,opt,name=summary,proto3"`
    StepCount               uint32                     `protobuf:"varint,2,opt,name=step_count,json=stepCount,proto3"`
    LastModifiedTime        *timestamppb.Timestamp     `protobuf:"bytes,3,opt,name=last_modified_time,json=lastModifiedTime,proto3"`
    TrajectoryId            string                     `protobuf:"bytes,4,opt,name=trajectory_id,json=trajectoryId,proto3"`
    Status                  CascadeRunStatus           `protobuf:"varint,5,opt,name=status,proto3"`
    CreatedTime             *timestamppb.Timestamp     `protobuf:"bytes,7,opt,name=created_time,json=createdTime,proto3"`
    Workspaces              []*CortexWorkspaceMetadata `protobuf:"bytes,9,rep,name=workspaces,proto3"`
    LastUserInputTime       *timestamppb.Timestamp     `protobuf:"bytes,10,opt,name=last_user_input_time,json=lastUserInputTime,proto3"`
    Annotations             *ConversationAnnotations   `protobuf:"bytes,15,opt,name=annotations,proto3"`
    LastUserInputStepIndex  uint32                     `protobuf:"varint,16,opt,name=last_user_input_step_index,json=lastUserInputStepIndex,proto3"`
    TrajectoryMetadata      *CortexTrajectoryMetadata  `protobuf:"bytes,17,opt,name=trajectory_metadata,json=trajectoryMetadata,proto3"`
    Source                  CortexTrajectorySource     `protobuf:"varint,20,opt,name=source,proto3"`
    Killed                  bool                       `protobuf:"varint,23,opt,name=killed,proto3"`
}
```

### 5.2 `ConversationAnnotations` Go Reflection

```go
// Extracted from Go runtime type reflection: package exa.language_server_pb
type ConversationAnnotations struct {
    Title                   string                     `protobuf:"bytes,1,opt,name=title,proto3"`
    Archived                bool                       `protobuf:"varint,4,opt,name=archived,proto3"`
    Starred                 bool                       `protobuf:"varint,6,opt,name=starred,proto3"`
    Pinned                  bool                       `protobuf:"varint,12,opt,name=pinned,proto3"`
}
```

---
