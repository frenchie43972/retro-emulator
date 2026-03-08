"""HuC6270 VRAM model used by the TurboGrafx-16 VDC."""

from __future__ import annotations


class VDCVRAM:
    """Simple 64KB VRAM backing storage."""

    SIZE = 0x10000

    def __init__(self) -> None:
        self._data = bytearray(self.SIZE)

    def reset(self) -> None:
        self._data = bytearray(self.SIZE)

    def read(self, address: int) -> int:
        return self._data[address & 0xFFFF]

    def write(self, address: int, value: int) -> None:
        self._data[address & 0xFFFF] = value & 0xFF

    def read_u16(self, address: int) -> int:
        low = self.read(address)
        high = self.read(address + 1)
        return low | (high << 8)
