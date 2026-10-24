"""Two-stage gated engine: only windows whose motion activity clears a
threshold are sent to the VLM.

VLM inference is where all the cost is, so filtering out still windows is what
determines operating cost. Every window keeps its motion.activity record;
active windows additionally get a vlm.observation record.
"""
from __future__ import annotations

from typing import Iterable, Iterator

from ..models import Record, SourceMeta
from ..sampling import Window
from .base import Extractor
from .motion import MotionExtractor
from .vlm import VlmExtractor


class GatedExtractor(Extractor):
    name = "motion+vlm"

    def __init__(
        self,
        gate_threshold: float = 0.02,
        sample_fps: float = 2.0,
        motion: Extractor | None = None,
        vlm: Extractor | None = None,
        **vlm_kwargs,
    ):
        self.gate_threshold = gate_threshold
        self.motion = motion or MotionExtractor(sample_fps=sample_fps)
        self.vlm = vlm or VlmExtractor(**vlm_kwargs)
        self.version = f"{self.motion.version}+{self.vlm.version}"

    def extract(self, source: SourceMeta, windows: Iterable[Window]) -> Iterator[Record]:
        wins = sorted(windows, key=lambda w: w.t_start)
        active: list[Window] = []
        # MotionExtractor yields exactly one record per window, in window order
        for window, record in zip(wins, self.motion.extract(source, iter(wins))):
            yield record
            if record.payload.get("activity_mean", 0.0) >= self.gate_threshold:
                active.append(window)
        yield from self.vlm.extract(source, active)
