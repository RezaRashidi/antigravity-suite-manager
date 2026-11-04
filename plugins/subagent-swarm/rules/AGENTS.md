# Autonomous Subagent Delegation & Multi-Account Swarm

You are equipped with parallel autonomous subagent execution powered by a dedicated multi-account allocator. Always prioritize concurrency, delegation, and specialization over sequential single-thread execution:

## Mandatory Delegation Protocol
1. **Multi-File Tasks & Architectural Changes:**
   - Whenever a task touches more than 1 file or has independent sub-tasks, decompose into components.
   - Dispatch parallel subagents using `invoke_subagent` with `Workspace='inherit'` or `Workspace='share'`.
   - Never implement separate files sequentially in the main thread when subagents can run concurrently.

2. **Investigation, Search & Diagnostics:**
   - Keep main context clean: do not run massive grep or broad file reads in the main conversation.
   - Dispatch `DeepInvestigator` or `research` via `invoke_subagent(TypeName='DeepInvestigator'|'research', ...)` to locate symbols and report line citations.

3. **Parallel Coding & Verification:**
   - Dispatch `DeepCoder` or `self` via `invoke_subagent(TypeName='DeepCoder'|'self', ...)` to write code and verify tests.
   - Run up to 4 subagents in parallel to fully utilize available multi-account idle capacity.

4. **Subagent Completion & Parent Notification Protocol:**
   - Always instruct every dispatched subagent prompt: "Upon completing your mission, deliver your final structured summary/findings back to the parent conversation using send_message."
   - When executing as a spawned subagent, do not stop at plain-text output; transmit completion status and results to the parent conversation via `send_message(Recipient=<parent_conversation_id>, Message=...)`.
