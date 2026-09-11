from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ArtifactState(str, Enum):
    DISCOVERED = "DISCOVERED"
    REVIEWED = "REVIEWED"
    QUARANTINED = "QUARANTINED"
    APPROVED_FOR_DESTRUCTION = "APPROVED_FOR_DESTRUCTION"
    DESTROYED = "DESTROYED"
    VERIFIED_ABSENT = "VERIFIED_ABSENT"
    UNRESOLVED = "UNRESOLVED"
    EXCLUDED = "EXCLUDED"
    PRESERVED = "PRESERVED"
    ERROR = "ERROR"


@dataclass(slots=True)
class ArtifactRecord:
    artifact_id: str
    root_id: str | None
    source_type: str
    location: str
    filename: str | None = None
    sha256: str | None = None
    text_fingerprint: str | None = None
    parent_artifact_id: str | None = None
    match_method: str | None = None
    match_score: float | None = None
    classification: str = "UNRESOLVED"
    state: ArtifactState = ArtifactState.DISCOVERED
    discovered_at: str = ""
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.discovered_at:
            self.discovered_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_path(
        cls,
        *,
        artifact_id: str,
        path: Path,
        sha256: str,
        root_id: str | None = None,
        match_method: str = "sha256",
    ) -> "ArtifactRecord":
        return cls(
            artifact_id=artifact_id,
            root_id=root_id,
            source_type="filesystem",
            location=str(path.resolve()),
            filename=path.name,
            sha256=sha256,
            match_method=match_method,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data
