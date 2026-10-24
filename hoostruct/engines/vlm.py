"""VLM engine: sends representative frames to a local Ollama vision model and
gets back structured observations.

Output is forced into a JSON schema (no free-form prose), so every response
lands directly in the record payload as queryable fields. Works with any
Ollama vision model; pass a domain-specific prompt for better results.
"""
from __future__ import annotations

import base64
import json
import urllib.request
import uuid
from typing import Iterable, Iterator

from .._cv import require_cv2
from ..models import Record, SourceMeta, utcnow
from ..sampling import Window
from .base import Extractor

DEFAULT_PROMPT = (
    "These are frames sampled from a video. Describe only what is visible; "
    "do not guess or infer beyond the frames. Put a short scene summary in "
    "'summary' and each distinct observed event in 'events'."
)

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "description": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["type", "description"],
            },
        },
    },
    "required": ["summary", "events"],
}


def _post_json(url: str, payload: dict, timeout_s: float) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


class VlmExtractor(Extractor):
    name = "vlm"

    def __init__(
        self,
        model: str = "gemma4:12b",
        base_url: str = "http://localhost:11434",
        frames_per_window: int = 2,
        jpeg_quality: int = 80,
        timeout_s: float = 300.0,
        prompt: str | None = None,
    ):
        self.model = model
        self.version = model  # engine_version records which model produced each record
        self.base_url = base_url.rstrip("/")
        self.frames_per_window = frames_per_window
        self.jpeg_quality = jpeg_quality
        self.timeout_s = timeout_s
        self.prompt = prompt or DEFAULT_PROMPT

    def extract(self, source: SourceMeta, windows: Iterable[Window]) -> Iterator[Record]:
        cv2 = require_cv2()
        cap = cv2.VideoCapture(source.source_path)
        try:
            if not cap.isOpened():
                raise RuntimeError(f"cannot open source: {source.source_path}")
            for w in windows:
                images, frame_times = self._grab_frames(cv2, cap, w)
                if not images:
                    continue
                payload = self._ask(images)
                payload["frame_times"] = frame_times
                yield Record(
                    record_id=str(uuid.uuid4()),
                    source_id=source.source_id,
                    t_start=w.t_start,
                    t_end=w.t_end,
                    event_type="vlm.observation",
                    payload=payload,
                    engine=self.name,
                    engine_version=self.version,
                    created_at=utcnow(),
                )
        finally:
            cap.release()

    def _grab_frames(self, cv2, cap, window: Window) -> tuple[list[str], list[float]]:
        n = self.frames_per_window
        span = window.t_end - window.t_start
        times = [window.t_start + span * (i + 0.5) / n for i in range(n)]
        images: list[str] = []
        used: list[float] = []
        for t in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ok, frame = cap.read()
            if not ok:
                continue
            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
            if ok:
                images.append(base64.b64encode(buf.tobytes()).decode("ascii"))
                used.append(round(t, 3))
        return images, used

    def _ask(self, images: list[str]) -> dict:
        body = {
            "model": self.model,
            "stream": False,
            "format": RESPONSE_SCHEMA,
            "options": {"temperature": 0},
            "messages": [{"role": "user", "content": self.prompt, "images": images}],
        }
        resp = _post_json(f"{self.base_url}/api/chat", body, self.timeout_s)
        content = (resp.get("message") or {}).get("content", "")
        try:
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError
        except (ValueError, TypeError):
            return {"raw": content, "parse_error": True}
        return parsed
