"""HuC6280 memory page register (MPR) bank mapping support."""

from __future__ import annotations


class HuC6280BankRegisters:
    """Tracks HuC6280 MPR registers used to map logical to physical memory."""

    PAGE_SIZE = 0x2000
    REGISTER_COUNT = 8

    def __init__(self) -> None:
        self._registers = [index for index in range(self.REGISTER_COUNT)]

    def reset(self) -> None:
        self._registers = [index for index in range(self.REGISTER_COUNT)]

    def set_register(self, index: int, value: int) -> None:
        if not 0 <= index < self.REGISTER_COUNT:
            raise ValueError("MPR index out of range")
        self._registers[index] = value & 0xFF

    def get_register(self, index: int) -> int:
        if not 0 <= index < self.REGISTER_COUNT:
            raise ValueError("MPR index out of range")
        return self._registers[index]

    def set_masked(self, mask: int, value: int) -> None:
        for index in range(self.REGISTER_COUNT):
            if mask & (1 << index):
                self.set_register(index, value)

    def get_masked(self, mask: int) -> int:
        for index in range(self.REGISTER_COUNT - 1, -1, -1):
            if mask & (1 << index):
                return self.get_register(index)
        return 0

    def map_logical(self, address: int) -> int:
        logical = address & 0xFFFF
        bank_index = logical >> 13
        offset = logical & (self.PAGE_SIZE - 1)
        bank = self._registers[bank_index]
        return (bank * self.PAGE_SIZE) + offset

    def snapshot(self) -> tuple[int, ...]:
        return tuple(self._registers)
