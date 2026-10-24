"""Source retention policy.

The default is keep: the original is never touched. Deletion runs only when
explicitly requested and only after the manifest has been written, so records
never become the sole evidence before they are safely stored.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path


class RetentionAction(str, Enum):
    KEEP = "keep"
    DELETE = "delete"


def apply(action: RetentionAction, source_path: str, manifest_written: bool) -> str:
    """Apply the policy and return the action actually performed."""
    if action is RetentionAction.DELETE:
        if not manifest_written:
            raise RuntimeError("refusing to delete the source before the manifest is written")
        Path(source_path).unlink()
        return RetentionAction.DELETE.value
    return RetentionAction.KEEP.value
