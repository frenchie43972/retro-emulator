"""Programmable waveform RAM for TurboGrafx-16 PSG channels."""

from __future__ import annotations

from dataclasses import dataclass, field

WAVEFORM_LENGTH = 32


@dataclass
class WaveformMemory:
    """Small per-channel waveform table with CPU write/read access."""

    table: list[int] = field(default_factory=lambda: [16] * WAVEFORM_LENGTH)

    def write(self, index: int, value: int) -> None:
        self.table[index % WAVEFORM_LENGTH] = value & 0x1F

    def read(self, index: int) -> int:
        return self.table[index % WAVEFORM_LENGTH]

    def amplitude(self, phase: float) -> float:
        sample = self.table[int(phase) % WAVEFORM_LENGTH]
        return (sample - 16.0) / 16.0
