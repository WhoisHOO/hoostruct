"""Source and record integrity.

- Source file: sha256 -> source_id.
- Records: a sha256 chain where each body includes the previous record's hash,
  so edits, deletions, and insertions are detectable after the fact.
Key-based signing can be layered on top later.
"""
from __future__ import annotations

import hashlib
from typing import Iterable, Iterator

from .models import Record, canonical_json

_CHUNK = 1024 * 1024


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def hash_record(record: Record) -> str:
    return hashlib.sha256(canonical_json(record.body_dict()).encode("utf-8")).hexdigest()


def chain(records: Iterable[Record], prev: str | None = None) -> Iterator[Record]:
    """Fill in the hash chain and yield records in order.

    ``prev`` is the last hash of a previous batch, if continuing one.
    """
    for r in records:
        r.prev_record_hash = prev
        r.record_hash = hash_record(r)
        prev = r.record_hash
        yield r


def verify_chain(dicts: Iterable[dict]) -> tuple[int, list[str]]:
    """Verify record dicts read back from storage. Returns (count, errors)."""
    errors: list[str] = []
    prev: str | None = None
    n = 0
    for i, d in enumerate(dicts):
        if d.get("prev_record_hash") != prev:
            errors.append(f"record {i}: prev_record_hash mismatch")
        body = {k: v for k, v in d.items() if k != "record_hash"}
        actual = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
        if actual != d.get("record_hash"):
            errors.append(f"record {i}: record_hash mismatch")
        prev = d.get("record_hash")
        n += 1
    return n, errors
