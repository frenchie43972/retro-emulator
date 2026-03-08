"""Memory bus implementation and reusable memory mapped devices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .interfaces import MemoryBus, MemoryDevice


@dataclass(frozen=True)
class AddressRange:
    """A closed, inclusive address range mapped to one memory device."""

    start: int
    end: int

    def contains(self, address: int) -> bool:
        return self.start <= address <= self.end

    def to_local(self, address: int) -> int:
        return address - self.start


class MappedMemoryBus(MemoryBus):
    """Memory bus that routes reads/writes to registered address ranges."""

    def __init__(self) -> None:
        self._mappings: list[tuple[AddressRange, MemoryDevice]] = []
        self._read_patcher: ReadPatcher | None = None

    def set_read_patcher(self, patcher: "ReadPatcher | None") -> None:
        """Install an optional read patcher (e.g. cheat device)."""
        self._read_patcher = patcher

    def register(self, start: int, end: int, device: MemoryDevice) -> None:
        """Map a device into an inclusive [start, end] address range."""
        if start > end:
            raise ValueError("start must be <= end")

        proposed = AddressRange(start=start, end=end)
        for existing, _device in self._mappings:
            if not (proposed.end < existing.start or proposed.start > existing.end):
                raise ValueError(
                    f"Address range {start:#06x}-{end:#06x} overlaps with "
                    f"{existing.start:#06x}-{existing.end:#06x}"
                )

        self._mappings.append((proposed, device))

    def read(self, address: int) -> int:
        mapped = self._resolve(address)
        value = mapped[1].read(mapped[0].to_local(address))
        if self._read_patcher is not None:
            return self._read_patcher.patch_read(address, value)
        return value

    def write(self, address: int, value: int) -> None:
        if not 0 <= value <= 0xFF:
            raise ValueError("value must be a byte")
        mapped = self._resolve(address)
        mapped[1].write(mapped[0].to_local(address), value)

    def _resolve(self, address: int) -> tuple[AddressRange, MemoryDevice]:
        for address_range, device in self._mappings:
            if address_range.contains(address):
                return address_range, device
        raise KeyError(f"Address not mapped on bus: {address:#06x}")


class RAM(MemoryDevice):
    """Simple read/write memory block."""

    def __init__(self, size: int) -> None:
        self._data = bytearray(size)

    def read(self, address: int) -> int:
        return self._data[address]

    def write(self, address: int, value: int) -> None:
        self._data[address] = value


class ROM(MemoryDevice):
    """Simple read-only memory block."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self, address: int) -> int:
        return self._data[address]

    def write(self, address: int, value: int) -> None:
        raise PermissionError("Cannot write to ROM")


class ReadPatcher(Protocol):
    """Interface for systems that alter bus read results."""

    def patch_read(self, address: int, actual_value: int) -> int:
        """Return patched read value for one bus address."""
