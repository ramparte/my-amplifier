"""
Configuration for M365 Connector.

Loads from environment variables with secure defaults.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class M365Config:
    """M365 connector configuration."""

    # Authentication
    tenant_id: str
    client_id: str
    client_secret: str

    # Default team/channel for agent collaboration
    default_team_id: Optional[str] = None
    default_channel_id: Optional[str] = None

    # API settings
    graph_base_url: str = "https://graph.microsoft.com/v1.0"
    timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "M365Config":
        """Load configuration from environment variables."""
        # Try to load .env file if it exists
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            _load_dotenv(env_file)

        tenant_id = os.environ.get("M365_TENANT_ID")
        client_id = os.environ.get("M365_CLIENT_ID")
        client_secret = os.environ.get("M365_CLIENT_SECRET")

        if not all([tenant_id, client_id, client_secret]):
            missing = []
            if not tenant_id:
                missing.append("M365_TENANT_ID")
            if not client_id:
                missing.append("M365_CLIENT_ID")
            if not client_secret:
                missing.append("M365_CLIENT_SECRET")
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return cls(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            default_team_id=os.environ.get("M365_TEAM_ID"),
            default_channel_id=os.environ.get("M365_CHANNEL_ID"),
        )


def _load_dotenv(path: Path) -> None:
    """Simple .env file loader."""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:  # Don't override existing
                    os.environ[key] = value
