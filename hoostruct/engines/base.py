from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Iterator

from ..models import Record, SourceMeta
from ..sampling import Window


class Extractor(ABC):
    """Source windows -> structured records. Implementations wrap a local CV
    model, a VLM, a rules-based analyzer, or a composition of those."""

    name: str
    version: str

    @abstractmethod
    def extract(self, source: SourceMeta, windows: Iterable[Window]) -> Iterator[Record]: ...
