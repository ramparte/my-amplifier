"""
Amplifier Tool wrapper for M365 Collaboration.

This module provides the tool interface that Amplifier expects.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Lazy-loaded collaboration instance
_collab = None


def _get_collab():
    """Get or create the collaboration instance."""
    global _collab
    if _collab is None:
        from .collaboration import AgentCollaboration

        # Get credentials from environment
        tenant_id = os.environ.get("M365_TENANT_ID")
        client_id = os.environ.get("M365_CLIENT_ID")
        client_secret = os.environ.get("M365_CLIENT_SECRET")

        if not all([tenant_id, client_id, client_secret]):
            raise ValueError(
                "M365 credentials required. Set M365_TENANT_ID, M365_CLIENT_ID, M365_CLIENT_SECRET"
            )

        _collab = AgentCollaboration(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            agent_id=os.environ.get("AMPLIFIER_AGENT_ID", f"amplifier-{os.getpid()}"),
        )
    return _collab


def execute(operation: str, **kwargs: Any) -> dict[str, Any]:
    """
    Amplifier tool entry point for M365 collaboration.

    Operations:
    - post_message: Post a message (title, content, message_type?, priority?, context?)
    - post_task: Post a task (title, description, priority?, context?)
    - post_status: Post status update (title, status_text, task_id?)
    - post_handoff: Hand off work (title, description, context, target_agent?)
    - get_messages: Get messages (message_type?, status?, limit?)
    - get_pending_tasks: Get unclaimed tasks
    - claim_task: Claim a task (task_id)
    - complete_task: Complete a task (task_id, result?)
    """
    try:
        collab = _get_collab()

        if operation == "post_message":
            msg = collab.post_message(**kwargs)
            return {"success": True, "message": msg.to_dict()}

        elif operation == "post_task":
            msg = collab.post_task(**kwargs)
            return {"success": True, "task": msg.to_dict()}

        elif operation == "post_status":
            msg = collab.post_status(**kwargs)
            return {"success": True, "status": msg.to_dict()}

        elif operation == "post_handoff":
            msg = collab.post_handoff(**kwargs)
            return {"success": True, "handoff": msg.to_dict()}

        elif operation == "get_messages":
            messages = collab.get_messages(**kwargs)
            return {"success": True, "messages": [m.to_dict() for m in messages], "count": len(messages)}

        elif operation == "get_pending_tasks":
            tasks = collab.get_pending_tasks()
            return {"success": True, "tasks": [t.to_dict() for t in tasks], "count": len(tasks)}

        elif operation == "claim_task":
            task_id = kwargs.get("task_id")
            if not task_id:
                return {"success": False, "error": "task_id required"}
            msg = collab.claim_task(task_id)
            if msg:
                return {"success": True, "task": msg.to_dict()}
            return {"success": False, "error": "Task not found"}

        elif operation == "complete_task":
            task_id = kwargs.get("task_id")
            if not task_id:
                return {"success": False, "error": "task_id required"}
            msg = collab.complete_task(task_id, kwargs.get("result"))
            if msg:
                return {"success": True, "task": msg.to_dict()}
            return {"success": False, "error": "Task not found"}

        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    except Exception as e:
        logger.exception(f"M365 collaboration operation {operation} failed")
        return {"success": False, "error": str(e)}


# Tool metadata for Amplifier
TOOL_SPEC = {
    "name": "m365_collab",
    "description": """Agent collaboration via M365 SharePoint.

Enables AI agents to communicate across sessions by posting and reading messages
to a shared SharePoint folder. Supports tasks, status updates, and work handoffs.

Operations:
- post_task: Post a task for other agents (title, description, priority?, context?)
- get_pending_tasks: Get unclaimed tasks
- claim_task: Claim a task (task_id)
- complete_task: Mark task done (task_id, result?)
- post_status: Post status update (title, status_text, task_id?)
- post_handoff: Hand off work (title, description, context)
- get_messages: Get recent messages (message_type?, status?, limit?)
- post_message: Post general message (title, content)

Example: Post a task
  m365_collab(operation="post_task", title="Review auth module", description="Check for security issues")

Example: Check for tasks
  m365_collab(operation="get_pending_tasks")
""",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Operation to perform",
                "enum": [
                    "post_message",
                    "post_task", 
                    "post_status",
                    "post_handoff",
                    "get_messages",
                    "get_pending_tasks",
                    "claim_task",
                    "complete_task",
                ],
            },
            "title": {"type": "string", "description": "Message/task title"},
            "content": {"type": "string", "description": "Message content"},
            "description": {"type": "string", "description": "Task description"},
            "status_text": {"type": "string", "description": "Status update text"},
            "task_id": {"type": "string", "description": "Task ID to claim/complete"},
            "priority": {"type": "string", "enum": ["high", "normal", "low"]},
            "message_type": {"type": "string", "enum": ["task", "status", "message", "handoff"]},
            "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "failed"]},
            "context": {"type": "object", "description": "Additional context data"},
            "result": {"type": "object", "description": "Task completion result"},
            "limit": {"type": "integer", "description": "Max messages to return"},
        },
        "required": ["operation"],
    },
}
