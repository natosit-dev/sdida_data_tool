from __future__ import annotations

import io
from uuid import uuid4

from googleapiclient.http import MediaIoBaseDownload

from sdida.fingerprint import sha256_bytes
from sdida.models import ArtifactRecord

_GOOGLE_NATIVE_PREFIX = "application/vnd.google-apps."


def discover_drive_files(service, seed_index: dict[str, list[str]]) -> list[ArtifactRecord]:
    """Find exact seed matches among non-Google-native Drive files.

    Read-only: file bytes are streamed through memory and never written to disk.
    """
    records: list[ArtifactRecord] = []
    page_token = None

    while True:
        response = service.files().list(
            q="trashed = false",
            spaces="drive",
            fields="nextPageToken, files(id,name,mimeType,size,modifiedTime)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()

        for item in response.get("files", []):
            mime_type = item.get("mimeType", "")
            if mime_type.startswith(_GOOGLE_NATIVE_PREFIX):
                continue

            request = service.files().get_media(fileId=item["id"])
            handle = io.BytesIO()
            downloader = MediaIoBaseDownload(handle, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            digest = sha256_bytes(handle.getvalue())
            roots = seed_index.get(digest, [])
            if not roots:
                continue

            filename = item.get("name") or item["id"]
            records.append(
                ArtifactRecord(
                    artifact_id=f"D-{uuid4().hex[:12]}",
                    root_id=roots[0],
                    source_type="google_drive",
                    location=f"gdrive://{item['id']}/{filename}",
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
