from __future__ import annotations

import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _safe_account(account: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", account)


def default_token_path(account: str) -> Path:
    return Path.home() / ".sdida" / "google" / f"{_safe_account(account)}_token.json"


def get_google_credentials(
    credentials_file: Path,
    account: str,
    token_file: Path | None = None,
) -> Credentials:
    """Return cached or newly authorized read-only Google credentials.

    The OAuth token is stored outside the repository under ~/.sdida by default.
    """
    credentials_file = credentials_file.expanduser().resolve()
    if not credentials_file.exists():
        raise FileNotFoundError(f"Google OAuth credentials file does not exist: {credentials_file}")

    token_path = (token_file or default_token_path(account)).expanduser()
    token_path.parent.mkdir(parents=True, exist_ok=True)

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent")

    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds
