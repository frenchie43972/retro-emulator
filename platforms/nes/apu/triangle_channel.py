"""Simplified NES triangle channel synthesis."""

from __future__ import annotations

from dataclasses import dataclass

CPU_CLOCK_HZ = 1_789_773

_LENGTH_TABLE = (
    10,
    254,
    20,
    2,
    40,
    4,
    80,
    6,
    160,
    8,
    60,
    10,
    14,
    12,
    26,
    14,
    12,
    16,
    24,
    18,
    48,
    20,
    96,
    22,
    192,
    24,
    72,
    26,
    16,
    28,
    32,
    30,
)


@dataclass
class TriangleChannel:
    enabled: bool = False
    timer_period: int = 0
    length_counter: int = 0
    phase: float = 0.0

    def write_linear_control(self, value: int) -> None:
        _ = value

    def write_timer_low(self, value: int) -> None:
        self.timer_period = (self.timer_period & 0x700) | (value & 0xFF)

    def write_timer_high(self, value: int) -> None:
        self.timer_period = (self.timer_period & 0xFF) | ((value & 0x07) << 8)
        self.length_counter = _LENGTH_TABLE[(value >> 3) & 0x1F]

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self.length_counter = 0

    def sample(self, sample_rate: int) -> float:
        if not self.enabled or self.length_counter == 0 or self.timer_period < 2:
            return 0.0

        frequency = CPU_CLOCK_HZ / (32.0 * (self.timer_period + 1))
        self.phase = (self.phase + (frequency / sample_rate)) % 1.0
        pos = self.phase * 32.0
        if pos < 16:
            return pos / 15.0
        return (31.0 - pos) / 15.0
