"""
Agent Collaboration Tool via SharePoint.

Enables AI agent instances to communicate by reading/writing
JSON messages to a shared SharePoint folder.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from auth import AuthConfig, M365Auth

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    """A message in the agent collaboration system."""

    id: str
    timestamp: str
    agent_id: str
    message_type: str  # task, status, message, handoff, query, response
    title: str
    content: str
    priority: str = "normal"  # high, normal, low
    status: str = "pending"  # pending, in_progress, completed, failed
    context: dict = field(default_factory=dict)
    in_reply_to: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "message_type": self.message_type,
            "title": self.title,
            "content": self.content,
            "priority": self.priority,
            "status": self.status,
            "context": self.context,
            "in_reply_to": self.in_reply_to,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            agent_id=data["agent_id"],
            message_type=data["message_type"],
            title=data["title"],
            content=data["content"],
            priority=data.get("priority", "normal"),
            status=data.get("status", "pending"),
            context=data.get("context", {}),
            in_reply_to=data.get("in_reply_to"),
        )


class AgentCollaboration:
    """
    SharePoint-based agent collaboration system.

    Agents communicate by posting JSON messages to a shared folder.
    Messages can be tasks, status updates, queries, or handoffs.
    """

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    FOLDER_NAME = "AgentMessages"

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        agent_id: Optional[str] = None,
        site_path: str = "root",  # or "sites/sitename"
    ):
        config = AuthConfig(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        self.auth = M365Auth(config)
        self.auth.authenticate(allow_interactive=False)

        self.agent_id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        self.site_path = site_path
        self._http = httpx.Client(timeout=30.0)
        self._drive_id: Optional[str] = None

    @classmethod
    def from_env(cls, agent_id: Optional[str] = None) -> "AgentCollaboration":
        """Create from environment variables."""
        from config import M365Config

        cfg = M365Config.from_env()
        return cls(
            tenant_id=cfg.tenant_id,
            client_id=cfg.client_id,
            client_secret=cfg.client_secret,
            agent_id=agent_id,
        )

    @property
    def drive_id(self) -> str:
        """Get the drive ID, fetching if needed."""
        if self._drive_id is None:
            response = self._request("GET", f"/sites/{self.site_path}/drive")
            if response.status_code == 200:
                self._drive_id = response.json()["id"]
            else:
                raise RuntimeError(f"Failed to get drive: {response.text}")
        return self._drive_id

    def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[dict] = None,
        content: Optional[bytes] = None,
        content_type: str = "application/json",
    ) -> httpx.Response:
        """Make authenticated request to Graph API."""
        url = f"{self.GRAPH_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {self.auth.get_token()}",
            "Content-Type": content_type,
        }

        if content is not None:
            return self._http.request(method, url, headers=headers, content=content)
        elif json_data is not None:
            return self._http.request(method, url, headers=headers, json=json_data)
        else:
            return self._http.request(method, url, headers=headers)

    def _ensure_folder(self) -> None:
        """Ensure the AgentMessages folder exists."""
        response = self._request(
            "POST",
            f"/drives/{self.drive_id}/root/children",
            json_data={
                "name": self.FOLDER_NAME,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "fail",
            },
        )
        # 201 = created, 409 = already exists - both are fine
        if response.status_code not in (200, 201, 409):
            logger.warning(f"Folder creation returned {response.status_code}")

    # === Core Operations ===

    def post_message(
        self,
        title: str,
        content: str,
        message_type: str = "message",
        priority: str = "normal",
        context: Optional[dict] = None,
        in_reply_to: Optional[str] = None,
    ) -> AgentMessage:
        """
        Post a message to the collaboration space.

        Returns the created message with its ID.
        """
        self._ensure_folder()

        msg = AgentMessage(
            id=f"msg-{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_id=self.agent_id,
            message_type=message_type,
            title=title,
            content=content,
            priority=priority,
            status="pending" if message_type == "task" else "completed",
            context=context or {},
            in_reply_to=in_reply_to,
        )

        filename = f"{msg.id}.json"
        file_content = json.dumps(msg.to_dict(), indent=2).encode()

        response = self._request(
            "PUT",
            f"/drives/{self.drive_id}/root:/{self.FOLDER_NAME}/{filename}:/content",
            content=file_content,
        )

        if response.status_code not in (200, 201):
            raise RuntimeError(f"Failed to post message: {response.text}")

        logger.info(f"Posted message: {msg.id}")
        return msg

    def get_messages(
        self,
        message_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[AgentMessage]:
        """
        Get messages from the collaboration space.

        Optionally filter by type and status.
        """
        response = self._request(
            "GET",
            f"/drives/{self.drive_id}/root:/{self.FOLDER_NAME}:/children"
            f"?$top={limit}&$orderby=lastModifiedDateTime desc",
        )

        if response.status_code != 200:
            logger.warning(f"Failed to list messages: {response.text}")
            return []

        messages = []
        for item in response.json().get("value", []):
            if not item["name"].endswith(".json"):
                continue

            # Download the file content
            download_url = item.get("@microsoft.graph.downloadUrl")
            if download_url:
                content_response = self._http.get(download_url)
                if content_response.status_code == 200:
                    try:
                        data = content_response.json()
                        msg = AgentMessage.from_dict(data)

                        # Apply filters
                        if message_type and msg.message_type != message_type:
                            continue
                        if status and msg.status != status:
                            continue

                        messages.append(msg)
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Skipping invalid message {item['name']}: {e}")

        return messages

    def get_message(self, message_id: str) -> Optional[AgentMessage]:
        """Get a specific message by ID."""
        filename = f"{message_id}.json" if not message_id.endswith(".json") else message_id

        response = self._request(
            "GET",
            f"/drives/{self.drive_id}/root:/{self.FOLDER_NAME}/{filename}:/content",
        )

        if response.status_code == 200:
            return AgentMessage.from_dict(response.json())
        return None

    def update_message_status(
        self, message_id: str, status: str, context_update: Optional[dict] = None
    ) -> Optional[AgentMessage]:
        """Update the status of a message (e.g., claim a task)."""
        msg = self.get_message(message_id)
        if not msg:
            return None

        msg.status = status
        msg.timestamp = datetime.now(timezone.utc).isoformat()
        if context_update:
            msg.context.update(context_update)

        filename = f"{message_id}.json" if not message_id.endswith(".json") else message_id
        file_content = json.dumps(msg.to_dict(), indent=2).encode()

        response = self._request(
            "PUT",
            f"/drives/{self.drive_id}/root:/{self.FOLDER_NAME}/{filename}:/content",
            content=file_content,
        )

        if response.status_code in (200, 201):
            return msg
        return None

    # === Convenience Methods ===

    def post_task(
        self,
        title: str,
        description: str,
        priority: str = "normal",
        context: Optional[dict] = None,
    ) -> AgentMessage:
        """Post a task for other agents to pick up."""
        return self.post_message(
            title=title,
            content=description,
            message_type="task",
            priority=priority,
            context=context,
        )

    def post_status(
        self,
        title: str,
        status_text: str,
        task_id: Optional[str] = None,
    ) -> AgentMessage:
        """Post a status update."""
        return self.post_message(
            title=title,
            content=status_text,
            message_type="status",
            in_reply_to=task_id,
        )

    def post_handoff(
        self,
        title: str,
        description: str,
        context: dict,
        target_agent: Optional[str] = None,
    ) -> AgentMessage:
        """Post a task handoff to another agent."""
        ctx = context.copy()
        if target_agent:
            ctx["target_agent"] = target_agent
        return self.post_message(
            title=title,
            content=description,
            message_type="handoff",
            priority="high",
            context=ctx,
        )

    def get_pending_tasks(self) -> list[AgentMessage]:
        """Get all pending tasks."""
        return self.get_messages(message_type="task", status="pending")

    def claim_task(self, task_id: str) -> Optional[AgentMessage]:
        """Claim a task (set status to in_progress)."""
        return self.update_message_status(
            task_id,
            "in_progress",
            {"claimed_by": self.agent_id, "claimed_at": datetime.now(timezone.utc).isoformat()},
        )

    def complete_task(self, task_id: str, result: Optional[dict] = None) -> Optional[AgentMessage]:
        """Mark a task as completed."""
        return self.update_message_status(
            task_id,
            "completed",
            {"completed_by": self.agent_id, "result": result or {}},
        )

    def close(self):
        """Close HTTP client."""
        self._http.close()


# === Amplifier Tool Interface ===

def execute(operation: str, **kwargs) -> dict[str, Any]:
    """
    Amplifier tool entry point.

    Operations:
    - post_message: Post a message to the collaboration space
    - post_task: Post a task for other agents
    - post_status: Post a status update
    - post_handoff: Hand off work to another agent
    - get_messages: Get recent messages
    - get_pending_tasks: Get unclaimed tasks
    - claim_task: Claim a task
    - complete_task: Mark task completed
    """
    collab = AgentCollaboration.from_env(agent_id=kwargs.pop("agent_id", None))

    try:
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
            return {"success": True, "messages": [m.to_dict() for m in messages]}

        elif operation == "get_pending_tasks":
            tasks = collab.get_pending_tasks()
            return {"success": True, "tasks": [t.to_dict() for t in tasks]}

        elif operation == "claim_task":
            msg = collab.claim_task(kwargs["task_id"])
            if msg:
                return {"success": True, "task": msg.to_dict()}
            return {"success": False, "error": "Task not found"}

        elif operation == "complete_task":
            msg = collab.complete_task(kwargs["task_id"], kwargs.get("result"))
            if msg:
                return {"success": True, "task": msg.to_dict()}
            return {"success": False, "error": "Task not found"}

        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    except Exception as e:
        logger.exception(f"Operation {operation} failed")
        return {"success": False, "error": str(e)}

    finally:
        collab.close()
