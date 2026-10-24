"""Record and metadata schema.

Only the common envelope is fixed here. Engine-specific fields live in the
record ``payload`` dict, so new engines never require a schema migration.
Bump SCHEMA_VERSION when the envelope itself changes.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "0.1"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_json(obj: Any) -> str:
    """Canonical serialization used for hashing: same content, same bytes."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass
class SourceMeta:
    """The unstructured source file being refined (video today; audio/logs later)."""

    source_id: str  # sha256 of the source file; pins record provenance after disposal
    source_path: str
    kind: str  # "video", "audio", ...
    size_bytes: int
    ingested_at: str  # ISO8601 UTC
    duration_s: float | None = None
    fps: float | None = None
    width: int | None = None
    height: int | None = None
    device_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Record:
    record_id: str
    source_id: str
    t_start: float  # seconds into the source
    t_end: float
    event_type: str
    payload: dict  # engine-specific fields
    engine: str
    engine_version: str
    created_at: str
    confidence: float | None = None
    schema_version: str = SCHEMA_VERSION
    prev_record_hash: str | None = None
    record_hash: str | None = None

    def body_dict(self) -> dict:
        """The hashed body: everything except record_hash itself."""
        d = asdict(self)
        d.pop("record_hash")
        return d

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Manifest:
    """Summary of one source's run. Once the source is disposed of, this file
    and the records are the only remaining evidence."""

    source: SourceMeta
    engine: str
    record_count: int
    chain_head: str | None  # hash of the last record; represents the whole chain
    records_path: str
    started_at: str
    finished_at: str
    retention_action: str
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return asdict(self)
