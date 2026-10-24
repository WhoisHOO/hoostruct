from .base import Extractor
from .gated import GatedExtractor
from .mock import MockExtractor
from .motion import MotionExtractor
from .vlm import VlmExtractor

_ENGINES: dict[str, type[Extractor]] = {
    cls.name: cls for cls in (MockExtractor, MotionExtractor, VlmExtractor, GatedExtractor)
}


def get_engine(name: str, **kwargs) -> Extractor:
    try:
        cls = _ENGINES[name]
    except KeyError:
        raise ValueError(
            f"unknown engine: {name} (available: {', '.join(sorted(_ENGINES))})"
        ) from None
    return cls(**kwargs)
