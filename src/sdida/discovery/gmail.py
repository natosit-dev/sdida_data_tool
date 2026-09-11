from __future__ import annotations

import base64
from uuid import uuid4

from sdida.fingerprint import sha256_bytes
from sdida.models import ArtifactRecord


def _decode_base64url(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _iter_parts(part: dict):
    yield part
    for child in part.get("parts", []) or []:
        yield from _iter_parts(child)


def discover_gmail_attachments(service, seed_index: dict[str, list[str]]) -> list[ArtifactRecord]:
    """Find exact seed matches among Gmail attachments.

    Read-only: attachments are streamed through memory and never written to disk.
    """
    records: list[ArtifactRecord] = []
    page_token = None

    while True:
        response = service.users().messages().list(
            userId="me",
            q="has:attachment",
            pageToken=page_token,
            maxResults=500,
        ).execute()

        for item in response.get("messages", []):
            message_id = item["id"]
            message = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full",
            ).execute()

            payload = message.get("payload", {})
            for part in _iter_parts(payload):
                filename = part.get("filename") or ""
                if not filename:
                    continue

                body = part.get("body", {})
                data = body.get("data")
                attachment_id = body.get("attachmentId")

                if attachment_id:
                    attachment = service.users().messages().attachments().get(
                        userId="me",
                        messageId=message_id,
                        id=attachment_id,
                    ).execute()
                    data = attachment.get("data")

                if not data:
                    continue

                raw = _decode_base64url(data)
                digest = sha256_bytes(raw)
                roots = seed_index.get(digest, [])
                if not roots:
                    continue

                records.append(
                    ArtifactRecord(
                        artifact_id=f"G-{uuid4().hex[:12]}",
                        root_id=roots[0],
                        source_type="gmail_attachment",
                        location=f"gmail://{message_id}/{filename}",
                        filename=filename,
                        sha256=digest,
                        match_method="sha256_exact",
                        match_score=1.0,
                        classification="EXACT_COPY",
                        notes=(
                            "same content matches multiple seed roots: " + ",".join(roots)
                            if len(roots) > 1
                            else None
                        ),
                    )
                )

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return records
