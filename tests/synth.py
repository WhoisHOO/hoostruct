"""Synthetic test video: a rectangle moves for the first part, then holds still."""
from __future__ import annotations


def make_synthetic_video(
    path: str,
    seconds: float = 6.0,
    fps: int = 10,
    size: tuple[int, int] = (160, 120),
    moving_until: float = 3.0,
) -> None:
    import cv2
    import numpy as np

    w, h = size
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    try:
        for i in range(int(seconds * fps)):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            t = i / fps
            if t < moving_until:
                x = int((i * 7) % (w - 30))
                cv2.rectangle(frame, (x, 40), (x + 30, 70), (255, 255, 255), -1)
            else:
                cv2.rectangle(frame, (60, 40), (90, 70), (255, 255, 255), -1)
            writer.write(frame)
    finally:
        writer.release()
