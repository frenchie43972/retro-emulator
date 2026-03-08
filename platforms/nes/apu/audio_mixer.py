"""Simple audio mixer for NES APU channels."""

from __future__ import annotations


def mix_channels(*, pulse1: float, pulse2: float, triangle: float, noise: float, dmc: float) -> float:
    pulse_mix = 0.00752 * (pulse1 + pulse2)
    tnd_mix = 0.00851 * triangle + 0.00494 * noise + 0.00335 * dmc
    mixed = pulse_mix + tnd_mix
    return max(-1.0, min(1.0, mixed * 4.0 - 1.0))
