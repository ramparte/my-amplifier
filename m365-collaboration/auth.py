"""
M365 Authentication Module with ROPC Support.

Supports:
- ROPC (Resource Owner Password Credentials) for test scenarios
- Service Principal for production
- Device Code flow as fallback
"""

import logging
from dataclasses import dataclass
from typing import Optional

import msal

logger = logging.getLogger(__name__)

# Well-known public client app IDs that often work with ROPC
AZURE_CLI_APP_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
GRAPH_CLI_APP_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"  # Microsoft Graph CLI


@dataclass
class TokenResult:
    """Result of token acquisition."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    scope: str = ""
    refresh_token: Optional[str] = None


@dataclass
class AuthConfig:
    """Authentication configuration."""

    tenant_id: str
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scopes: Optional[list[str]] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ["https://graph.microsoft.com/.default"]


class M365Auth:
    """
    Flexible M365 authentication supporting multiple flows.

    Tries flows in order of preference based on available credentials.
    """

    def __init__(self, config: AuthConfig):
        self.config = config
        self._cached_token: Optional[TokenResult] = None

    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.config.tenant_id}"

    def _try_ropc(self, client_id: str) -> Optional[TokenResult]:
        """
        Try Resource Owner Password Credentials flow.

        This flow uses username/password directly. Works for test tenants
        where the app allows public client flows.
        """
        if not self.config.username or not self.config.password:
            return None

        logger.info(f"Attempting ROPC flow with client_id: {client_id[:8]}...")

        app = msal.PublicClientApplication(
            client_id=client_id,
            authority=self.authority,
        )

        result = app.acquire_token_by_username_password(
            username=self.config.username,
            password=self.config.password,
            scopes=self.config.scopes,
        )

        if "access_token" in result:
            logger.info("ROPC authentication successful")
            return TokenResult(
                access_token=result["access_token"],
                token_type=result.get("token_type", "Bearer"),
                expires_in=result.get("expires_in", 3600),
                scope=result.get("scope", ""),
                refresh_token=result.get("refresh_token"),
            )

        error = result.get("error", "unknown")
        error_desc = result.get("error_description", "No description")
        logger.warning(f"ROPC failed with {client_id[:8]}: {error} - {error_desc}")
        return None

    def _try_client_credentials(self) -> Optional[TokenResult]:
        """
        Try Client Credentials (service principal) flow.

        Requires client_id and client_secret.
        """
        if not self.config.client_id or not self.config.client_secret:
            return None

        logger.info("Attempting client credentials flow...")

        app = msal.ConfidentialClientApplication(
            client_id=self.config.client_id,
            client_credential=self.config.client_secret,
            authority=self.authority,
        )

        result = app.acquire_token_for_client(scopes=self.config.scopes)

        if "access_token" in result:
            logger.info("Client credentials authentication successful")
            return TokenResult(
                access_token=result["access_token"],
                token_type=result.get("token_type", "Bearer"),
                expires_in=result.get("expires_in", 3600),
                scope=result.get("scope", ""),
            )

        error = result.get("error", "unknown")
        logger.warning(f"Client credentials failed: {error}")
        return None

    def _try_device_code(self, client_id: str) -> Optional[TokenResult]:
        """
        Try Device Code flow (interactive).

        User authenticates in browser, enters code displayed here.
        Works with MFA-enabled accounts.
        """
        logger.info(f"Attempting Device Code flow with client_id: {client_id[:8]}...")

        app = msal.PublicClientApplication(
            client_id=client_id,
            authority=self.authority,
        )

        flow = app.initiate_device_flow(scopes=self.config.scopes)

        if "user_code" not in flow:
            logger.warning(f"Device code flow initiation failed: {flow.get('error')}")
            return None

        # Display instructions to user
        print("\n" + "=" * 60)
        print("DEVICE CODE AUTHENTICATION")
        print("=" * 60)
        print(f"\n{flow['message']}\n")
        print("=" * 60 + "\n")

        # Wait for user to complete authentication
        result = app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            logger.info("Device Code authentication successful")
            return TokenResult(
                access_token=result["access_token"],
                token_type=result.get("token_type", "Bearer"),
                expires_in=result.get("expires_in", 3600),
                scope=result.get("scope", ""),
                refresh_token=result.get("refresh_token"),
            )

        error = result.get("error", "unknown")
        error_desc = result.get("error_description", "No description")
        logger.warning(f"Device code failed: {error} - {error_desc}")
        return None

    def authenticate(self, allow_interactive: bool = True) -> TokenResult:
        """
        Authenticate using the best available method.

        Tries in order:
        1. Client credentials (if client_id and secret provided)
        2. ROPC with provided client_id
        3. ROPC with Azure CLI app ID
        4. Device Code flow (interactive, if allowed)
        """
        # Try client credentials first if available
        if self.config.client_id and self.config.client_secret:
            result = self._try_client_credentials()
            if result:
                self._cached_token = result
                return result

        # Try ROPC with various client IDs
        client_ids_to_try = []

        if self.config.client_id:
            client_ids_to_try.append(self.config.client_id)

        # Add well-known public apps
        client_ids_to_try.extend([AZURE_CLI_APP_ID, GRAPH_CLI_APP_ID])

        for client_id in client_ids_to_try:
            result = self._try_ropc(client_id)
            if result:
                self._cached_token = result
                return result

        # Try Device Code flow if interactive is allowed
        if allow_interactive:
            logger.info("ROPC failed (likely MFA enabled). Trying Device Code flow...")
            result = self._try_device_code(AZURE_CLI_APP_ID)
            if result:
                self._cached_token = result
                return result

        raise RuntimeError(
            "All authentication methods failed. "
            "For ROPC: ensure no MFA requirement. "
            "For Device Code: run interactively and complete browser auth."
        )

    def get_token(self) -> str:
        """Get access token, authenticating if needed."""
        if self._cached_token is None:
            self.authenticate()
        return self._cached_token.access_token


def create_auth_from_env() -> M365Auth:
    """Create auth from environment variables."""
    import os

    config = AuthConfig(
        tenant_id=os.environ.get("M365_TENANT_ID", ""),
        username=os.environ.get("M365_USERNAME"),
        password=os.environ.get("M365_PASSWORD"),
        client_id=os.environ.get("M365_CLIENT_ID"),
        client_secret=os.environ.get("M365_CLIENT_SECRET"),
    )

    if not config.tenant_id:
        raise ValueError("M365_TENANT_ID environment variable required")

    return M365Auth(config)
