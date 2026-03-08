"""Audio mixing helpers for TurboGrafx-16 PSG channels."""

from __future__ import annotations

from collections.abc import Iterable


def mix_channel_samples(samples: Iterable[float]) -> float:
    values = list(samples)
    if not values:
        return 0.0

    mixed = sum(values) / len(values)
    return max(-1.0, min(1.0, mixed))
