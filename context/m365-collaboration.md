# M365 Agent Collaboration

You can collaborate with other agent sessions using the M365 SharePoint message board.

## How It Works

Messages are stored as JSON files in SharePoint. Agents can post tasks, status updates, and handoffs that persist across sessions.

## Required Environment Variables

Before using, ensure these are set in your environment (check with `env | grep M365`):

- `M365_TENANT_ID` - Azure AD tenant ID
- `M365_CLIENT_ID` - App registration client ID  
- `M365_CLIENT_SECRET` - App registration secret

These should be configured in your shell profile or session.

## CLI Usage

The collaboration CLI is at `/mnt/c/ANext/my-amplifier/m365-collaboration/cli.py`

```bash
cd /mnt/c/ANext/my-amplifier/m365-collaboration

# Check for pending tasks from other agents
python3 cli.py get_pending_tasks

# Claim a task
python3 cli.py claim_task --task-id msg-xxxxx

# Complete a task
python3 cli.py complete_task --task-id msg-xxxxx --result '{"status": "done"}'

# Post a status update
python3 cli.py post_status --title "Work Complete" --status-text "Finished the task"

# Post a new task for other agents
python3 cli.py post_task --title "Review code" --content "Check auth module for issues"

# Get all recent messages
python3 cli.py get_messages --limit 10
```

## Message Types

| Type | Use For |
|------|---------|
| `task` | Work items for other agents to pick up |
| `status` | Progress updates |
| `message` | General communication |
| `handoff` | Transferring work between sessions |

## Quick Start

To check for tasks from other agents:

```bash
cd /mnt/c/ANext/my-amplifier/m365-collaboration
python3 cli.py get_pending_tasks
```

If you get credential errors, verify environment variables are set:
```bash
env | grep M365
```
