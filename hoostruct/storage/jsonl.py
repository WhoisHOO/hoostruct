"""Default sink: per source, <first 16 chars of source_id>.records.jsonl + .manifest.json."""
from __future__ import annotations

import json
from pathlib import Path

from ..models import Manifest, Record, canonical_json
from .base import RecordSink


class JsonlSink(RecordSink):
    def __init__(self, out_dir: str):
        self.out_dir = Path(out_dir)
        self._fh = None
        self._prefix: str | None = None

    def open(self, source_id: str) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._prefix = source_id[:16]
        path = self.out_dir / f"{self._prefix}.records.jsonl"
        self._fh = path.open("w", encoding="utf-8")
        self.records_path = str(path)

    def write(self, record: Record) -> None:
        if self._fh is None:
            raise RuntimeError("call open() first")
        self._fh.write(canonical_json(record.to_dict()) + "\n")

    def finalize(self, manifest: Manifest) -> str:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
        manifest_path = self.out_dir / f"{self._prefix}.manifest.json"
        manifest_path.write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(manifest_path)
