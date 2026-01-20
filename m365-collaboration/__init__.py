"""M365 Collaboration - Agent-to-agent communication via SharePoint."""

from .auth import AuthConfig, M365Auth, TokenResult
from .collaboration import AgentCollaboration, AgentMessage, execute
from .config import M365Config
from .graph_client import GraphClient, GraphResponse

__all__ = [
    "AuthConfig",
    "M365Auth",
    "TokenResult",
    "M365Config",
    "GraphClient",
    "GraphResponse",
    "AgentCollaboration",
    "AgentMessage",
    "execute",
]

__version__ = "0.1.0"
