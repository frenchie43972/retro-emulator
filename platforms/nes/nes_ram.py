"""NES internal RAM device with hardware mirroring behavior."""

from __future__ import annotations

from emulator.interfaces import MemoryDevice


class NESRAM(MemoryDevice):
    """2KB internal RAM mirrored through $0000-$1FFF."""

    def __init__(self) -> None:
        self._data = bytearray(0x0800)

    def reset(self) -> None:
        self._data = bytearray(0x0800)

    def read(self, address: int) -> int:
        return self._data[address % 0x0800]

    def write(self, address: int, value: int) -> None:
        self._data[address % 0x0800] = value & 0xFF


    def serialize_state(self) -> dict:
        return {"data": bytes(self._data)}

    def deserialize_state(self, state: dict) -> None:
        data = state["data"]
        if len(data) != len(self._data):
            raise ValueError("NES RAM size mismatch in save state")
        self._data[:] = data
