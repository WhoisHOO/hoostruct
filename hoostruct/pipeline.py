"""Pipeline orchestrator: ingest -> sample -> extract -> hash chain -> store -> retention."""
from __future__ import annotations

from . import integrity
from .engines import get_engine
from .ingest import ingest
from .models import Manifest, utcnow
from .retention import RetentionAction
from .retention import apply as apply_retention
from .sampling import FixedIntervalSampler, Sampler
from .storage import RecordSink


def run(
    source_path: str,
    sink: RecordSink,
    engine_name: str = "mock",
    engine_kwargs: dict | None = None,
    sampler: Sampler | None = None,
    retention: RetentionAction = RetentionAction.KEEP,
    device_id: str | None = None,
) -> Manifest:
    started = utcnow()
    source = ingest(source_path, device_id=device_id)
    engine = get_engine(engine_name, **(engine_kwargs or {}))
    sampler = sampler or FixedIntervalSampler()

    sink.open(source.source_id)
    chain_head: str | None = None
    count = 0
    records = engine.extract(source, sampler.windows(source_path, source.duration_s))
    for record in integrity.chain(records):
        sink.write(record)
        chain_head = record.record_hash
        count += 1

    manifest = Manifest(
        source=source,
        engine=f"{engine.name}@{engine.version}",
        record_count=count,
        chain_head=chain_head,
        records_path=sink.records_path or "",
        started_at=started,
        finished_at=utcnow(),
        retention_action=retention.value,
    )
    manifest_path = sink.finalize(manifest)
    manifest.retention_action = apply_retention(
        retention, source_path, manifest_written=bool(manifest_path)
    )
    return manifest
