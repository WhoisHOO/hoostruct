"""Sampling: split a source into time windows handed to the extraction engine.

Event-driven samplers (scene change, audio level, ...) can be added as
further Sampler implementations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator


@dataclass
class Window:
    t_start: float
    t_end: float
    frames: list | None = None  # decoded frames; filled only when an engine asks


class Sampler(ABC):
    name: str

    @abstractmethod
    def windows(self, source_path: str, duration_s: float | None) -> Iterator[Window]: ...


class FixedIntervalSampler(Sampler):
    """Fixed-interval windows. Does not decode frames."""

    name = "fixed"

    def __init__(self, interval_s: float = 60.0):
        if interval_s <= 0:
            raise ValueError("interval_s must be positive")
        self.interval_s = interval_s

    def windows(self, source_path: str, duration_s: float | None) -> Iterator[Window]:
        total = duration_s if duration_s else self.interval_s  # unknown length: one window
        t = 0.0
        while t < total:
            end = min(t + self.interval_s, total)
            yield Window(t_start=t, t_end=end)
            t = end
