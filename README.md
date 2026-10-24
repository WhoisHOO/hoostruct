# HooStruct

Turn unstructured data into structured, verifiable records. Video is the first supported source.

## Why

Unstructured data like camera footage is too large to keep, but the information inside it is
needed long after the raw file is gone: operations, analytics, audits, evidence. HooStruct
extracts that information into compact structured records, proves the records haven't been
tampered with, and only then lets you dispose of the original.

```
source (video) ─> sampling ─> extraction engine(s) ─> records (JSONL) + manifest
                                                   └> retention policy (keep / delete original)
```

## How it works

1. **Ingest**: the source file is hashed (sha256 becomes its `source_id`) and probed for metadata,
   so every record stays traceable to its origin even after the file is deleted.
2. **Sampling**: the source is split into time windows.
3. **Extraction**: engines turn windows into records.
   - `motion` - OpenCV frame differencing; an activity index per window. No model, no training.
   - `vlm` - representative frames go to a local [Ollama](https://ollama.com) vision model
     (default `gemma4:12b`); the response is forced into a JSON schema, never free-form prose.
   - `motion+vlm` (default) - two-stage gating: every window gets a motion record, and only
     windows above an activity threshold are sent to the VLM. Inference cost scales with how
     much actually happens, not with footage length.
   - `mock` - wiring tests.
4. **Integrity**: records form a sha256 hash chain (each record's hash covers the previous one),
   and the manifest pins the chain head. `hoostruct verify` re-computes the chain and detects
   any edit, deletion, or insertion.
5. **Retention**: the original is kept by default. `--delete-source` deletes it only after the
   records and manifest are safely written.

## Quickstart

```bash
pip install hoostruct[cv]        # or: pip install opencv-python
ollama pull gemma4:12b           # any Ollama vision model works

hoostruct refine footage.mp4 --out data/records
hoostruct verify data/records/<id>.records.jsonl
```

Useful flags: `--engine mock|motion|vlm|motion+vlm`, `--interval 60` (window seconds),
`--gate-threshold 0.02`, `--vlm-model`, `--frames-per-window`, `--delete-source`.
Also usable as `python -m hoostruct ...` without installing.

Example record (`vlm.observation`):

```json
{
  "source_id": "0ac1bbbf...", "t_start": 0.0, "t_end": 60.0,
  "event_type": "vlm.observation",
  "payload": {"summary": "...", "events": [{"type": "...", "description": "..."}], "frame_times": [30.0]},
  "engine": "vlm", "engine_version": "gemma4:12b",
  "prev_record_hash": "...", "record_hash": "..."
}
```

## Extending

Every stage is an interface: implement `Extractor` for a new model or domain, `Sampler` for a
different windowing strategy, `RecordSink` for a database or an existing system. The record
envelope is fixed; engine-specific fields live in `payload`, so new engines need no schema change.
Domain-specific prompts can be passed to the VLM engine (`VlmExtractor(prompt=...)`).

Only permissively licensed dependencies are accepted (Apache-2.0/MIT); the core has none beyond
optional OpenCV.

## Development

```bash
python -m unittest discover -s tests
```

## License

Apache License 2.0. See [LICENSE](LICENSE).
