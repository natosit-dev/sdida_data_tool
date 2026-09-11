from __future__ import annotations

from pathlib import Path

from googleapiclient.discovery import build

from .discover import load_seed_index
from .discovery.drive import discover_drive_files
from .discovery.gmail import discover_gmail_attachments
from .google_auth import get_google_credentials
from .manifest import write_jsonl


def run_google_discover(
    seed_manifest: Path,
    account: str,
    credentials_file: Path,
    output: Path,
    *,
    force: bool = False,
) -> int:
    seed_index = load_seed_index(seed_manifest)
    creds = get_google_credentials(credentials_file, account)

    gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
    profile = gmail.users().getProfile(userId="me").execute()
    actual_email = str(profile.get("emailAddress", ""))
    if actual_email.casefold() != account.casefold():
        raise ValueError(
            f"Authenticated Gmail account is {actual_email!r}, expected {account!r}. "
            "Delete the cached token under ~/.sdida/google and authenticate again."
        )

    drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    gmail_records = discover_gmail_attachments(gmail, seed_index)
    drive_records = discover_drive_files(drive, seed_index)
    records = gmail_records + drive_records

    write_jsonl(output, records, force=force)
    print(
        f"Discovered {len(records)} Google exact matches "
        f"({len(gmail_records)} Gmail attachments, {len(drive_records)} Drive files) -> {output}"
    )
    return 0
