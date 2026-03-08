"""Simplified NES noise channel synthesis."""

from __future__ import annotations

from dataclasses import dataclass

CPU_CLOCK_HZ = 1_789_773

_NOISE_PERIOD_TABLE = (
    4,
    8,
    16,
    32,
    64,
    96,
    128,
    160,
    202,
    254,
    380,
    508,
    762,
    1016,
    2034,
    4068,
)

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
class NoiseChannel:
    enabled: bool = False
    volume: int = 0
    mode: int = 0
    period_index: int = 0
    length_counter: int = 0
    shift_register: int = 1
    phase: float = 0.0

    def write_control(self, value: int) -> None:
        self.volume = value & 0x0F

    def write_period(self, value: int) -> None:
        self.mode = (value >> 7) & 0x01
        self.period_index = value & 0x0F

    def write_length(self, value: int) -> None:
        self.length_counter = _LENGTH_TABLE[(value >> 3) & 0x1F]

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self.length_counter = 0

    def sample(self, sample_rate: int) -> float:
        if not self.enabled or self.length_counter == 0:
            return 0.0

        period = _NOISE_PERIOD_TABLE[self.period_index]
        frequency = CPU_CLOCK_HZ / period
        self.phase += frequency / sample_rate
        while self.phase >= 1.0:
            self.phase -= 1.0
            tap = 6 if self.mode else 1
            feedback = (self.shift_register ^ (self.shift_register >> tap)) & 0x01
            self.shift_register = (self.shift_register >> 1) | (feedback << 14)

        if self.shift_register & 0x01:
            return 0.0
        return self.volume / 15.0
