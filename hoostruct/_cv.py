"""Lazy OpenCV import. The mock engine and the verify command must work without cv2."""


def require_cv2():
    try:
        import cv2
    except ImportError as e:
        raise RuntimeError(
            "this feature requires opencv-python: pip install hoostruct[cv]"
        ) from e
    return cv2
