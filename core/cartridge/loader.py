"""ROM loading and format detection.

The loader uses a parser registry so future cartridge formats can be added
without changing emulator runtime code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .base import CartridgeMetadata, LoadedCartridge
from .mappers import create_mapper


class CartridgeLoadError(ValueError):
    """Raised when cartridge bytes are malformed or unsupported."""


class CartridgeParser(Protocol):
    """Parser contract for one cartridge/ROM format."""

    def can_parse(self, rom_bytes: bytes) -> bool: ...

    def parse(self, rom_bytes: bytes) -> LoadedCartridge: ...


class INESParser:
    """Parser for the classic iNES NES file format."""

    def can_parse(self, rom_bytes: bytes) -> bool:
        return len(rom_bytes) >= 16 and rom_bytes[:4] == b"NES\x1A"

    def parse(self, rom_bytes: bytes) -> LoadedCartridge:
        if len(rom_bytes) < 16:
            raise CartridgeLoadError("ROM too small to contain iNES header")

        header = rom_bytes[:16]
        if header[:4] != b"NES\x1A":
            raise CartridgeLoadError("Invalid iNES magic header")

        prg_banks = header[4]
        chr_banks = header[5]
        flags6 = header[6]
        flags7 = header[7]

        mapper = (flags7 & 0xF0) | (flags6 >> 4)

        trainer_size = 512 if (flags6 & 0x04) else 0
        has_battery_ram = bool(flags6 & 0x02)
        mirroring = "vertical" if (flags6 & 0x01) else "horizontal"

        prg_size = prg_banks * 0x4000
        chr_size = chr_banks * 0x2000
        cursor = 16 + trainer_size
        expected_size = cursor + prg_size + chr_size
        if len(rom_bytes) < expected_size:
            raise CartridgeLoadError(
                "Malformed iNES ROM: file is smaller than header-declared PRG/CHR sizes"
            )

        prg_rom = rom_bytes[cursor : cursor + prg_size]
        cursor += prg_size
        chr_rom = rom_bytes[cursor : cursor + chr_size]

        metadata = CartridgeMetadata(
            format_name="iNES",
            mapper=mapper,
            prg_rom_size=prg_size,
            chr_rom_size=chr_size,
            has_battery_ram=has_battery_ram,
            mirroring=mirroring,
        )

        return LoadedCartridge(
            metadata=metadata,
            prg_rom=prg_rom,
            chr_rom=chr_rom,
            mapper=_create_mapper_or_error(mapper),
            ram_size=0x2000,
        )


class CartridgeLoader:
    """Detects ROM formats and returns normalized cartridge objects."""

    def __init__(self) -> None:
        self._parsers: list[CartridgeParser] = [INESParser()]

    def register_parser(self, parser: CartridgeParser) -> None:
        self._parsers.insert(0, parser)

    def load_bytes(self, rom_bytes: bytes) -> LoadedCartridge:
        for parser in self._parsers:
            if parser.can_parse(rom_bytes):
                return parser.parse(rom_bytes)
        raise CartridgeLoadError("Unsupported ROM format")

    def load_file(self, path: str | Path) -> LoadedCartridge:
        rom_path = Path(path)
        try:
            rom_bytes = rom_path.read_bytes()
        except OSError as exc:
            raise CartridgeLoadError(f"Could not read ROM file '{rom_path}': {exc}") from exc
        return self.load_bytes(rom_bytes)


def _create_mapper_or_error(mapper_number: int):
    try:
        return create_mapper(mapper_number)
    except ValueError as exc:
        raise CartridgeLoadError(str(exc)) from exc
