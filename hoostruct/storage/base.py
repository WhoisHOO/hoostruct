from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Manifest, Record


class RecordSink(ABC):
    """Where records go. Implement this to write to a database or an existing system."""

    records_path: str | None = None  # must be set before finalize

    @abstractmethod
    def open(self, source_id: str) -> None: ...

    @abstractmethod
    def write(self, record: Record) -> None: ...

    @abstractmethod
    def finalize(self, manifest: Manifest) -> str:
        """Persist the manifest and return its location."""
