"""NES controller register interface at $4016/$4017."""

from __future__ import annotations

from dataclasses import dataclass, field

from emulator.interfaces import MemoryDevice

from .nes_controller import NESController


@dataclass
class ControllerRegisters(MemoryDevice):
    """Implements serial reads for controller ports."""

    controller1: NESController
    _latched_state_p1: tuple[int, ...] = field(default_factory=tuple)
    _read_index_p1: int = 0
    _strobe: int = 0

    def read(self, address: int) -> int:
        if address == 0:
            return self._read_port1()
        if address == 1:
            return 0
        return 0

    def write(self, address: int, value: int) -> None:
        if address != 0:
            return
        self._strobe = value & 0x01
        if self._strobe:
            self._latched_state_p1 = self.controller1.snapshot()
            self._read_index_p1 = 0

    def _read_port1(self) -> int:
        if self._strobe:
            self._latched_state_p1 = self.controller1.snapshot()
            self._read_index_p1 = 0
            value = self._latched_state_p1[0]
            print("[controller] read", value)
            return value

        if self._read_index_p1 >= len(self._latched_state_p1):
            print("[controller] read", 1)
            return 1

        value = self._latched_state_p1[self._read_index_p1]
        self._read_index_p1 += 1
        print("[controller] read", value)
        return value


    def serialize_state(self) -> dict:
        return {
            "latched_state_p1": list(self._latched_state_p1),
            "read_index_p1": self._read_index_p1,
            "strobe": self._strobe,
        }

    def deserialize_state(self, state: dict) -> None:
        self._latched_state_p1 = tuple(int(v) for v in state["latched_state_p1"])
        self._read_index_p1 = int(state["read_index_p1"])
        self._strobe = int(state.get("strobe", 0)) & 0x01
