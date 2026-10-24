"""Motion engine: per-window activity index via OpenCV frame differencing.

Needs no training and runs on modest hardware. In the gated engine it decides
which windows are worth sending to the VLM. Default thresholds are starting
points; calibrate them on your own footage.
"""
from __future__ import annotations

import uuid
from typing import Iterable, Iterator

from .._cv import require_cv2
from ..models import Record, SourceMeta, utcnow
from ..sampling import Window
from .base import Extractor


class MotionExtractor(Extractor):
    name = "motion"
    version = "0.1"

    def __init__(
        self,
        sample_fps: float = 2.0,
        pixel_threshold: int = 25,
        frame_active_threshold: float = 0.01,
        resize_width: int = 320,
    ):
        self.sample_fps = sample_fps
        self.pixel_threshold = pixel_threshold
        self.frame_active_threshold = frame_active_threshold
        self.resize_width = resize_width

    def extract(self, source: SourceMeta, windows: Iterable[Window]) -> Iterator[Record]:
        cv2 = require_cv2()
        wins = sorted(windows, key=lambda w: w.t_start)
        if not wins:
            return
        activities: list[list[float]] = [[] for _ in wins]

        cap = cv2.VideoCapture(source.source_path)
        try:
            if not cap.isOpened():
                raise RuntimeError(f"cannot open source: {source.source_path}")
            fps = cap.get(cv2.CAP_PROP_FPS)
            if not fps or fps <= 0:
                fps = source.fps or 30.0
            step = max(1, round(fps / self.sample_fps))
            prev = None
            frame_idx = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if frame_idx % step == 0:
                    t = frame_idx / fps
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    h, w = gray.shape
                    if w > self.resize_width:
                        gray = cv2.resize(gray, (self.resize_width, int(h * self.resize_width / w)))
                    if prev is not None and prev.shape == gray.shape:
                        diff = cv2.absdiff(gray, prev)
                        activity = float((diff > self.pixel_threshold).mean())
                        wi = self._window_index(wins, t)
                        if wi is not None:
                            activities[wi].append(activity)
                    prev = gray
                frame_idx += 1
        finally:
            cap.release()

        for window, acts in zip(wins, activities):
            yield self._record(source, window, acts)

    @staticmethod
    def _window_index(wins: list[Window], t: float) -> int | None:
        for i, w in enumerate(wins):
            if w.t_start <= t < w.t_end:
                return i
        return None

    def _record(self, source: SourceMeta, window: Window, acts: list[float]) -> Record:
        n = len(acts)
        payload = {
            "activity_mean": round(sum(acts) / n, 4) if n else 0.0,
            "activity_max": round(max(acts), 4) if n else 0.0,
            "active_frame_ratio": round(
                sum(1 for a in acts if a >= self.frame_active_threshold) / n, 4
            ) if n else 0.0,
            "frames_analyzed": n,
            "sample_fps": self.sample_fps,
        }
        return Record(
            record_id=str(uuid.uuid4()),
            source_id=source.source_id,
            t_start=window.t_start,
            t_end=window.t_end,
            event_type="motion.activity",
            payload=payload,
            engine=self.name,
            engine_version=self.version,
            created_at=utcnow(),
        )
