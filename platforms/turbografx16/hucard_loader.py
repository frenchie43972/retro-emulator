"""HuCard cartridge loading and ROM access helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.cartridge import CartridgeMetadata


@dataclass(frozen=True)
class LoadedHuCard:
    """Loaded TurboGrafx-16 HuCard ROM image."""

    metadata: CartridgeMetadata
    rom: bytes

    def read_physical(self, address: int) -> int:
        if not self.rom:
            return 0xFF
        return self.rom[address % len(self.rom)]


class HuCardLoadError(ValueError):
    """Raised when HuCard data is malformed or unsupported."""


class HuCardLoader:
    """Loads raw TurboGrafx-16 HuCard ROM files."""

    MAX_SIZE = 0x200000

    def load_bytes(self, rom_bytes: bytes) -> LoadedHuCard:
        if not rom_bytes:
            raise HuCardLoadError("Empty HuCard ROM")
        if len(rom_bytes) > self.MAX_SIZE:
            raise HuCardLoadError("HuCard ROM exceeds 2MB addressable space")

        metadata = CartridgeMetadata(
            format_name="HuCard",
            mapper=0,
            prg_rom_size=len(rom_bytes),
            chr_rom_size=0,
            has_battery_ram=False,
            mirroring="none",
        )
        return LoadedHuCard(metadata=metadata, rom=rom_bytes)

    def load_file(self, path: str | Path) -> LoadedHuCard:
        rom_path = Path(path)
        try:
            return self.load_bytes(rom_path.read_bytes())
        except OSError as exc:
            raise HuCardLoadError(f"Could not read HuCard ROM file '{rom_path}': {exc}") from exc
