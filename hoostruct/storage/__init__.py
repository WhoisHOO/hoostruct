from .base import RecordSink
from .jsonl import JsonlSink


def get_sink(name: str, out_dir: str) -> RecordSink:
    if name == "jsonl":
        return JsonlSink(out_dir)
    raise ValueError(f"unknown sink: {name} (available: jsonl)")
