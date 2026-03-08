"""Simplified placeholder NES DMC channel synthesis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DMCChannel:
    enabled: bool = False
    output_level: int = 0

    def write_control(self, value: int) -> None:
        _ = value

    def write_direct_load(self, value: int) -> None:
        self.output_level = value & 0x7F

    def write_sample_address(self, value: int) -> None:
        _ = value

    def write_sample_length(self, value: int) -> None:
        _ = value

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def sample(self, sample_rate: int) -> float:
        _ = sample_rate
        if not self.enabled:
            return 0.0
        return self.output_level / 127.0


    def serialize_state(self) -> dict:
        return {"enabled": self.enabled, "output_level": self.output_level}

    def deserialize_state(self, state: dict) -> None:
        self.enabled = bool(state["enabled"])
        self.output_level = int(state["output_level"])
