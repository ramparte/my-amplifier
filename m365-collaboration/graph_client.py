"""
Microsoft Graph API Client.

Simple client for making Graph API requests with authenticated tokens.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from auth import M365Auth

logger = logging.getLogger(__name__)

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


@dataclass
class GraphResponse:
    """Response from Graph API."""

    success: bool
    status_code: int
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class GraphClient:
    """
    Simple Microsoft Graph API client.

    Handles authentication and request/response patterns.
    """

    def __init__(self, auth: M365Auth):
        self.auth = auth
        self._http: Optional[httpx.Client] = None

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=30.0)
        return self._http

    def _headers(self) -> dict[str, str]:
        """Get request headers with auth token."""
        token = self.auth.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def get(self, path: str, params: Optional[dict] = None) -> GraphResponse:
        """Make GET request to Graph API."""
        url = f"{GRAPH_BASE_URL}{path}"
        try:
            response = self.http.get(url, headers=self._headers(), params=params)
            return self._parse_response(response)
        except Exception as e:
            logger.exception(f"Graph GET {path} failed")
            return GraphResponse(success=False, status_code=0, error=str(e))

    def post(self, path: str, json_data: dict[str, Any]) -> GraphResponse:
        """Make POST request to Graph API."""
        url = f"{GRAPH_BASE_URL}{path}"
        try:
            response = self.http.post(url, headers=self._headers(), json=json_data)
            return self._parse_response(response)
        except Exception as e:
            logger.exception(f"Graph POST {path} failed")
            return GraphResponse(success=False, status_code=0, error=str(e))

    def _parse_response(self, response: httpx.Response) -> GraphResponse:
        """Parse Graph API response."""
        if response.status_code in (200, 201, 204):
            data = response.json() if response.content else {}
            return GraphResponse(success=True, status_code=response.status_code, data=data)

        # Parse error
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", response.text)
        except Exception:
            error_msg = response.text[:500]

        return GraphResponse(
            success=False,
            status_code=response.status_code,
            error=error_msg,
        )

    def close(self):
        """Close HTTP client."""
        if self._http:
            self._http.close()
            self._http = None

    # Convenience methods

    def get_me(self) -> GraphResponse:
        """Get current user profile."""
        return self.get("/me")

    def get_organization(self) -> GraphResponse:
        """Get organization info."""
        return self.get("/organization")

    def list_teams(self) -> GraphResponse:
        """List teams the user is a member of."""
        return self.get("/me/joinedTeams")

    def list_users(self, top: int = 10) -> GraphResponse:
        """List users in the organization."""
        return self.get("/users", params={"$top": top})

    def send_channel_message(
        self, team_id: str, channel_id: str, content: str
    ) -> GraphResponse:
        """Send a message to a Teams channel."""
        return self.post(
            f"/teams/{team_id}/channels/{channel_id}/messages",
            {"body": {"contentType": "text", "content": content}},
        )
