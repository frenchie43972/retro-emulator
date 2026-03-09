"""NES controller register interface at $4016/$4017."""

from __future__ import annotations

from dataclasses import dataclass

from emulator.interfaces import MemoryDevice

from .nes_controller import NESController


@dataclass
class ControllerRegisters(MemoryDevice):
    """Implements serial reads for controller ports."""

    controller1: NESController
    def read(self, address: int) -> int:
        if address == 0:
            return self.controller1.read()
        if address == 1:
            return 0
        return 0

    def write(self, address: int, value: int) -> None:
        if address != 0:
            return
        self.controller1.write(value)


    def serialize_state(self) -> dict:
        return {}

    def deserialize_state(self, state: dict) -> None:
        _ = state
