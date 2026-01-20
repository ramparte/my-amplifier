# M365 Agent Collaboration

You have access to the **m365_collab** tool for agent-to-agent communication via Microsoft 365.

## Overview

This tool enables AI agent instances to collaborate by reading and writing messages to a shared SharePoint folder. Messages persist across sessions, enabling async task handoffs and status updates.

## Operations

| Operation | Description |
|-----------|-------------|
| `post_message` | Post a general message |
| `post_task` | Post a task for other agents to pick up |
| `post_status` | Post a status update |
| `post_handoff` | Hand off work to another agent instance |
| `get_messages` | Get recent messages (optionally filtered) |
| `get_pending_tasks` | Get unclaimed tasks |
| `claim_task` | Claim a task (set to in_progress) |
| `complete_task` | Mark a task as completed |

## Usage Examples

### Post a Task
```
m365_collab(
    operation="post_task",
    title="Research authentication patterns",
    description="Investigate best practices for OAuth2 in Python applications",
    priority="normal",
    context={"project": "my-project"}
)
```

### Check for Pending Tasks
```
m365_collab(operation="get_pending_tasks")
```

### Claim and Complete a Task
```
m365_collab(operation="claim_task", task_id="msg-xxxxx")
# ... do the work ...
m365_collab(
    operation="complete_task",
    task_id="msg-xxxxx",
    result={"findings": "...", "recommendations": "..."}
)
```

### Post Status Update
```
m365_collab(
    operation="post_status",
    title="Analysis Complete",
    status_text="Finished reviewing the codebase. Found 3 issues.",
    task_id="msg-xxxxx"  # Optional: link to original task
)
```

### Hand Off Work
```
m365_collab(
    operation="post_handoff",
    title="Continue refactoring auth module",
    description="Started work on auth.py, needs completion",
    context={
        "files_modified": ["auth.py"],
        "remaining_work": ["Add error handling", "Write tests"],
        "session_id": "previous-session-id"
    }
)
```

## Message Types

| Type | Use For |
|------|---------|
| `task` | Work items for agents to pick up |
| `status` | Progress updates |
| `message` | General communication |
| `handoff` | Transferring work between sessions |

## Where Messages Are Stored

Messages are stored as JSON files in SharePoint:
`https://m365x72159956.sharepoint.com/Shared Documents/AgentMessages/`

Each message has:
- Unique ID (e.g., `msg-abc123def456`)
- Timestamp
- Agent ID (identifies which agent posted)
- Type, priority, status
- Content and optional context

## Environment Variables Required

The tool requires these environment variables:
- `M365_TENANT_ID`
- `M365_CLIENT_ID`
- `M365_CLIENT_SECRET`

These should be set in your environment or `.env` file.
