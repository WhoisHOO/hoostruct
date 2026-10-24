"""Source registration: hash (source_id) plus metadata probing.

Uses ffprobe when available, falls back to OpenCV, and records size only
when neither is present.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .integrity import sha256_file
from .models import SourceMeta, utcnow


def probe(path: Path) -> dict:
    return _probe_ffprobe(path) or _probe_cv2(path)


def _probe_cv2(path: Path) -> dict:
    try:
        from ._cv import require_cv2

        cv2 = require_cv2()
    except RuntimeError:
        return {}
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            return {}
        meta: dict = {}
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if fps and fps > 0:
            meta["fps"] = round(fps, 3)
            if frames and frames > 0:
                meta["duration_s"] = round(frames / fps, 3)
        if width and height:
            meta["width"] = width
            meta["height"] = height
        return meta
    finally:
        cap.release()


def _probe_ffprobe(path: Path) -> dict:
    if not shutil.which("ffprobe"):
        return {}
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,avg_frame_rate:format=duration",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return {}
    try:
        data = json.loads(proc.stdout)
        stream = (data.get("streams") or [{}])[0]
        meta: dict = {}
        dur = (data.get("format") or {}).get("duration")
        if dur:
            meta["duration_s"] = float(dur)
        if stream.get("width"):
            meta["width"] = int(stream["width"])
            meta["height"] = int(stream["height"])
        rate = stream.get("avg_frame_rate", "")
        if "/" in rate:
            num, den = rate.split("/", 1)
            if float(den):
                meta["fps"] = round(float(num) / float(den), 3)
        return meta
    except (ValueError, KeyError, IndexError):
        return {}


def ingest(source_path: str, kind: str = "video", device_id: str | None = None) -> SourceMeta:
    path = Path(source_path)
    if not path.is_file():
        raise FileNotFoundError(source_path)
    return SourceMeta(
        source_id=sha256_file(path),
        source_path=str(path.resolve()),
        kind=kind,
        size_bytes=path.stat().st_size,
        ingested_at=utcnow(),
        device_id=device_id,
        **probe(path),
    )
