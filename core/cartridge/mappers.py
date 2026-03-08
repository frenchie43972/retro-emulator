"""Compatibility exports for NES mapper implementations."""

from platforms.nes.mappers import Mapper0NROM, Mapper1MMC1, Mapper2UxROM, Mapper3CNROM, NESMapper, create_mapper

__all__ = [
    "NESMapper",
    "Mapper0NROM",
    "Mapper1MMC1",
    "Mapper2UxROM",
    "Mapper3CNROM",
    "create_mapper",
]
