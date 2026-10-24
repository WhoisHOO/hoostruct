"""CLI.

  hoostruct refine <video> [--engine motion+vlm] [--out data/records]
  hoostruct verify <records.jsonl>
"""
from __future__ import annotations

import argparse
import json
import sys

from .integrity import verify_chain
from .pipeline import run
from .retention import RetentionAction
from .sampling import FixedIntervalSampler
from .storage import get_sink


def _engine_kwargs(args) -> dict:
    vlm = {
        "model": args.vlm_model,
        "base_url": args.vlm_url,
        "frames_per_window": args.frames_per_window,
    }
    if args.engine == "motion":
        return {"sample_fps": args.sample_fps}
    if args.engine == "vlm":
        return vlm
    if args.engine == "motion+vlm":
        return {"gate_threshold": args.gate_threshold, "sample_fps": args.sample_fps, **vlm}
    return {}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="hoostruct",
        description="Turn unstructured data into structured, verifiable records.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("refine", help="refine one source file into records")
    pr.add_argument("source", help="path to the source file (video)")
    pr.add_argument("--engine", default="motion+vlm", choices=["mock", "motion", "vlm", "motion+vlm"])
    pr.add_argument("--sink", default="jsonl")
    pr.add_argument("--out", default="data/records", help="output directory for records")
    pr.add_argument("--interval", type=float, default=60.0, help="window length in seconds")
    pr.add_argument("--device-id", default=None, help="camera/device identifier to record")
    pr.add_argument("--sample-fps", type=float, default=2.0, help="motion analysis sampling fps")
    pr.add_argument("--gate-threshold", type=float, default=0.02, help="min activity to send a window to the VLM")
    pr.add_argument("--vlm-model", default="gemma4:12b", help="Ollama vision model name")
    pr.add_argument("--vlm-url", default="http://localhost:11434", help="Ollama base URL")
    pr.add_argument("--frames-per-window", type=int, default=2, help="frames sent to the VLM per window")
    pr.add_argument(
        "--delete-source",
        action="store_true",
        help="delete the source after records and manifest are written (default: keep)",
    )

    pv = sub.add_parser("verify", help="verify a record hash chain")
    pv.add_argument("records", help="path to *.records.jsonl")

    args = p.parse_args(argv)

    if args.cmd == "refine":
        retention = RetentionAction.DELETE if args.delete_source else RetentionAction.KEEP
        manifest = run(
            args.source,
            sink=get_sink(args.sink, args.out),
            engine_name=args.engine,
            engine_kwargs=_engine_kwargs(args),
            sampler=FixedIntervalSampler(args.interval),
            retention=retention,
            device_id=args.device_id,
        )
        print(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "verify":
        with open(args.records, encoding="utf-8") as f:
            dicts = [json.loads(line) for line in f if line.strip()]
        n, errors = verify_chain(dicts)
        if errors:
            print(f"FAIL: {len(errors)} error(s) across {n} record(s)", file=sys.stderr)
            for e in errors:
                print(" -", e, file=sys.stderr)
            return 1
        print(f"OK: {n} record(s), chain intact")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
