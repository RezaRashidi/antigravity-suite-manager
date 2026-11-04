# Autonomous Subagent Delegation & Multi-Account Swarm

You have access to parallel autonomous subagents powered by multi-account capacity.

## Core Principles
1. **Reason First in Main Thread:**
   - Always perform thorough internal thinking, reasoning, and architectural analysis in the main conversation first.
   - Do not prematurely delegate simple tasks, code analysis, single-file edits, or direct user questions.

2. **Autonomous Delegation for Parallel Tasks:**
   - For broad codebase searches across disconnected modules, you may dispatch `DeepInvestigator` or `research` via `invoke_subagent(TypeName='DeepInvestigator'|'research', ...)`.
   - For parallel implementations of decoupled files or tests, you may dispatch `DeepCoder` or `self` via `invoke_subagent(TypeName='DeepCoder'|'self', ...)`.

3. **Subagent Completion & Parent Notification Protocol:**
   - Always instruct every dispatched subagent: "Upon completing your mission, deliver your final structured summary/findings back to the parent conversation using send_message."
   - When executing as a spawned subagent, deliver final status and results to the parent conversation via `send_message(Recipient=<parent_conversation_id>, Message=...)`.
