"""Google OAuth authenticator with configurable scopes."""

import asyncio
import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


class GoogleAuth:
    """Manages OAuth credentials for Google API access with configurable scopes."""

    # Default scopes (Google Drive read-only for backward compatibility)
    DEFAULT_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    # Predefined scope sets for common use cases
    DRIVE_READONLY_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
    DRIVE_FULL_SCOPES = ["https://www.googleapis.com/auth/drive"]
    CALENDAR_SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
    ]

    def __init__(
        self,
        credentials_json: str | None = None,
        token_json: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
    ):
        """
        Initialize authenticator with OAuth credentials.

        Supports multiple credential formats:
        1. JSON strings (GDOC_CLIENT and GDOC_TOKEN env vars)
        2. Separate client_id and client_secret (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, etc.)
        3. Direct parameters

        Args:
            credentials_json: OAuth client configuration JSON (from GDOC_CLIENT env var)
            token_json: Serialized token JSON (from GDOC_TOKEN env var)
            client_id: OAuth client ID (alternative to JSON)
            client_secret: OAuth client secret (alternative to JSON)
            scopes: List of OAuth scopes to request (defaults to Drive read-only)

        Raises:
            ValueError: If credentials are missing or invalid
        """
        # Store scopes (use default if not provided)
        self.scopes = scopes or self.DEFAULT_SCOPES

        # Try to get credentials from various sources
        self.credentials_json = credentials_json or os.getenv("GDOC_CLIENT")
        self.token_json = token_json or os.getenv("GDOC_TOKEN")

        # Try common env var names for client_id and client_secret
        self.client_id = (
            client_id or os.getenv("GOOGLE_CLIENT_ID") or os.getenv("CLIENT_ID_GOOGLE_LOGIN")
        )
        self.client_secret = (
            client_secret
            or os.getenv("GOOGLE_CLIENT_SECRET")
            or os.getenv("CLIENT_SECRET_GOOGLE_LOGIN")
        )

        # If we have JSON format, use that
        if self.credentials_json and self.token_json:
            self.creds = self._load_credentials_from_json()
        # Otherwise, try to construct from client_id/client_secret
        elif self.client_id and self.client_secret:
            self.creds = self._load_credentials_from_separate()
        else:
            raise ValueError(
                "Missing Google Drive credentials. Set either:\n"
                "  - GDOC_CLIENT and GDOC_TOKEN (JSON format), or\n"
                "  - GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET (separate values)"
            )

    def _load_credentials_from_json(self) -> Credentials:
        """Load and refresh OAuth credentials from JSON strings."""
        try:
            token_data = json.loads(self.token_json)
            creds = Credentials(
                token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes", self.scopes),
            )

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

            return creds
        except Exception as e:
            raise ValueError(f"Failed to load Google Drive credentials from JSON: {e}")

    def _load_credentials_from_separate(self) -> Credentials:
        """Load credentials from separate client_id and client_secret."""
        try:
            # Try to load existing token from env var
            token_json = self.token_json or os.getenv("GDOC_TOKEN")

            if token_json:
                # We have a token, use it
                token_data = json.loads(token_json)
                creds = Credentials(
                    token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    scopes=self.scopes,
                )

                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())

                return creds
            # No token yet - user needs to authenticate
            # For now, create credentials without token (will need OAuth flow)
            raise ValueError(
                "Google Drive token not found. You need to authenticate first.\n"
                "Set GDOC_TOKEN with a valid OAuth token JSON, or run OAuth flow to obtain one."
            )
        except json.JSONDecodeError:
            raise ValueError("GDOC_TOKEN must be valid JSON if provided")
        except Exception as e:
            raise ValueError(f"Failed to load Google Drive credentials: {e}") from e

    def get_credentials(self) -> Credentials:
        """Return the loaded OAuth credentials."""
        return self.creds

    def refresh_if_needed(self) -> None:
        """Refresh credentials if they have expired."""
        if self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())

    async def refresh_if_needed_async(self) -> None:
        """Refresh credentials asynchronously if they have expired."""
        if self.creds.expired and self.creds.refresh_token:
            await asyncio.to_thread(self.creds.refresh, Request())


__all__ = ["GoogleAuth"]
