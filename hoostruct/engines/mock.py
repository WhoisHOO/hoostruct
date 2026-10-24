"""Mock engine for wiring tests. Never opens the source; emits one record per window."""
from __future__ import annotations

import uuid
from typing import Iterable, Iterator

from ..models import Record, SourceMeta, utcnow
from ..sampling import Window
from .base import Extractor


class MockExtractor(Extractor):
    name = "mock"
    version = "0"

    def extract(self, source: SourceMeta, windows: Iterable[Window]) -> Iterator[Record]:
        for w in windows:
            yield Record(
                record_id=str(uuid.uuid4()),
                source_id=source.source_id,
                t_start=w.t_start,
                t_end=w.t_end,
                event_type="mock.window",
                payload={"note": "placeholder record for pipeline testing"},
                engine=self.name,
                engine_version=self.version,
                created_at=utcnow(),
            )
