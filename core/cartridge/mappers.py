"""Mapper implementations.

Only NES Mapper 0 (NROM) is implemented initially. Additional mappers should
follow the same pattern by exposing bus mappings and read/write behavior.
"""

from __future__ import annotations

from emulator.interfaces import MemoryDevice

from .base import CartridgeMapper, LoadedCartridge


class _MapperRegion(MemoryDevice):
    def __init__(self, cartridge: LoadedCartridge, base_address: int) -> None:
        self._cartridge = cartridge
        self._base_address = base_address

    def read(self, address: int) -> int:
        return self._cartridge.read(self._base_address + address)

    def write(self, address: int, value: int) -> None:
        self._cartridge.write(self._base_address + address, value)


class Mapper0NROM(CartridgeMapper):
    """NES Mapper 0 (NROM) with fixed PRG mapping and optional PRG RAM."""

    def cpu_mappings(self, cartridge: LoadedCartridge) -> list[tuple[int, int, MemoryDevice]]:
        mappings: list[tuple[int, int, MemoryDevice]] = []
        if cartridge.ram is not None:
            mappings.append((0x6000, 0x7FFF, _MapperRegion(cartridge, 0x6000)))
        mappings.append((0x8000, 0xFFFF, _MapperRegion(cartridge, 0x8000)))
        return mappings

    def read(self, cartridge: LoadedCartridge, address: int) -> int:
        if 0x6000 <= address <= 0x7FFF and cartridge.ram is not None:
            return cartridge.ram[address - 0x6000]
        if 0x8000 <= address <= 0xFFFF:
            local = address - 0x8000
            if len(cartridge.prg_rom) == 0x4000:
                local %= 0x4000
            return cartridge.prg_rom[local]
        raise KeyError(f"Mapper0 read out of range: {address:#06x}")

    def write(self, cartridge: LoadedCartridge, address: int, value: int) -> None:
        if not 0 <= value <= 0xFF:
            raise ValueError("value must be a byte")
        if 0x6000 <= address <= 0x7FFF and cartridge.ram is not None:
            cartridge.ram[address - 0x6000] = value
            return
        if 0x8000 <= address <= 0xFFFF:
            raise PermissionError("Cannot write to NROM PRG ROM")
        raise KeyError(f"Mapper0 write out of range: {address:#06x}")
