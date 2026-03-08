"""Mapper 2 (UxROM) implementation."""

from __future__ import annotations

from .mapper_base import MapperCPURegion, NESMapper


class Mapper2UxROM(NESMapper):
    def __init__(self) -> None:
        self._selected_bank = 0

    def cpu_mappings(self, cartridge):
        mappings = []
        if cartridge.ram is not None:
            mappings.append((0x6000, 0x7FFF, MapperCPURegion(cartridge, 0x6000)))
        mappings.append((0x8000, 0xFFFF, MapperCPURegion(cartridge, 0x8000)))
        return mappings

    def cpu_read(self, cartridge, address: int) -> int:
        if 0x6000 <= address <= 0x7FFF and cartridge.ram is not None:
            return cartridge.ram[address - 0x6000]
        if 0x8000 <= address <= 0xBFFF:
            bank_count = max(1, len(cartridge.prg_rom) // 0x4000)
            bank = self._selected_bank % bank_count
            return cartridge.prg_rom[bank * 0x4000 + (address - 0x8000)]
        if 0xC000 <= address <= 0xFFFF:
            bank_count = max(1, len(cartridge.prg_rom) // 0x4000)
            bank = bank_count - 1
            return cartridge.prg_rom[bank * 0x4000 + (address - 0xC000)]
        raise KeyError(f"Mapper2 read out of range: {address:#06x}")

    def cpu_write(self, cartridge, address: int, value: int) -> None:
        value &= 0xFF
        if 0x6000 <= address <= 0x7FFF and cartridge.ram is not None:
            cartridge.ram[address - 0x6000] = value
            return
        if 0x8000 <= address <= 0xFFFF:
            self._selected_bank = value & 0x0F
            return
        raise KeyError(f"Mapper2 write out of range: {address:#06x}")

    def ppu_read(self, cartridge, address: int) -> int:
        if cartridge.chr_rom:
            return cartridge.chr_rom[address % len(cartridge.chr_rom)]
        return cartridge.chr_ram[address % len(cartridge.chr_ram)]

    def ppu_write(self, cartridge, address: int, value: int) -> None:
        if cartridge.chr_rom:
            return
        cartridge.chr_ram[address % len(cartridge.chr_ram)] = value & 0xFF

    def serialize_state(self) -> dict:
        return {"selected_bank": self._selected_bank}

    def deserialize_state(self, state: dict) -> None:
        self._selected_bank = int(state["selected_bank"])
