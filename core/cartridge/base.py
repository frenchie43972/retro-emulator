"""Generic cartridge abstractions.

The :class:`LoadedCartridge` type stores normalized cartridge data and delegates
memory behavior to a mapper implementation. Mapper classes can be swapped to
add support for additional memory layouts without changing ROM parsers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from emulator.bus import MappedMemoryBus
from emulator.interfaces import MemoryDevice


@dataclass(frozen=True)
class CartridgeMetadata:
    """Metadata extracted from a cartridge image."""

    format_name: str
    mapper: int
    prg_rom_size: int
    chr_rom_size: int
    has_battery_ram: bool
    mirroring: str


class LoadedCartridge:
    """A loaded cartridge image and mapper-backed memory behavior."""

    def __init__(
        self,
        *,
        metadata: CartridgeMetadata,
        prg_rom: bytes,
        chr_rom: bytes,
        mapper: "CartridgeMapper",
        ram_size: int = 0,
    ) -> None:
        self.metadata = metadata
        self.prg_rom = prg_rom
        self.chr_rom = chr_rom
        self.mapper = mapper
        self.ram = bytearray(ram_size) if ram_size else None

    def read(self, address: int) -> int:
        """Read from a cartridge CPU address in mapper space."""
        return self.mapper.read(self, address)

    def write(self, address: int, value: int) -> None:
        """Write to a cartridge CPU address in mapper space."""
        self.mapper.write(self, address, value)

    def attach_to_bus(self, bus: MappedMemoryBus) -> None:
        """Register mapper-provided regions on the memory bus."""
        for start, end, device in self.mapper.cpu_mappings(self):
            bus.register(start, end, device)

    def save_ram(self, path: Path) -> None:
        """Persist battery RAM contents to disk when RAM is present."""
        if self.ram is None:
            return
        path.write_bytes(bytes(self.ram))

    def load_ram(self, path: Path) -> None:
        """Load battery RAM contents from disk if the save file exists."""
        if self.ram is None or not path.exists():
            return
        data = path.read_bytes()
        if len(data) != len(self.ram):
            raise ValueError(
                f"Save RAM size mismatch: expected {len(self.ram)} bytes, got {len(data)}"
            )
        self.ram[:] = data


class CartridgeMapper:
    """Mapper contract for converting cartridge data into bus-visible regions."""

    def cpu_mappings(
        self, cartridge: LoadedCartridge
    ) -> list[tuple[int, int, MemoryDevice]]:  # pragma: no cover - interface method
        raise NotImplementedError

    def read(self, cartridge: LoadedCartridge, address: int) -> int:  # pragma: no cover
        raise NotImplementedError

    def write(self, cartridge: LoadedCartridge, address: int, value: int) -> None:  # pragma: no cover
        raise NotImplementedError
