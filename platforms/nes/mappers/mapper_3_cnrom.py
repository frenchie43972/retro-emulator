"""Mapper 3 (CNROM) implementation."""

from __future__ import annotations

from .mapper_base import MapperCPURegion, NESMapper


class Mapper3CNROM(NESMapper):
    def __init__(self) -> None:
        self._chr_bank = 0

    def cpu_mappings(self, cartridge):
        mappings = []
        if cartridge.ram is not None:
            mappings.append((0x6000, 0x7FFF, MapperCPURegion(cartridge, 0x6000)))
        mappings.append((0x8000, 0xFFFF, MapperCPURegion(cartridge, 0x8000)))
        return mappings

    def cpu_read(self, cartridge, address: int) -> int:
        if 0x6000 <= address <= 0x7FFF and cartridge.ram is not None:
            return cartridge.ram[address - 0x6000]
        if 0x8000 <= address <= 0xFFFF:
            local = address - 0x8000
            if len(cartridge.prg_rom) == 0x4000:
                local %= 0x4000
            return cartridge.prg_rom[local]
        raise KeyError(f"Mapper3 read out of range: {address:#06x}")

    def cpu_write(self, cartridge, address: int, value: int) -> None:
        value &= 0xFF
        if 0x6000 <= address <= 0x7FFF and cartridge.ram is not None:
            cartridge.ram[address - 0x6000] = value
            return
        if 0x8000 <= address <= 0xFFFF:
            self._chr_bank = value & 0x03
            return
        raise KeyError(f"Mapper3 write out of range: {address:#06x}")

    def ppu_read(self, cartridge, address: int) -> int:
        if cartridge.chr_rom:
            bank_count = max(1, len(cartridge.chr_rom) // 0x2000)
            bank = self._chr_bank % bank_count
            return cartridge.chr_rom[bank * 0x2000 + (address & 0x1FFF)]
        return cartridge.chr_ram[address % len(cartridge.chr_ram)]

    def ppu_write(self, cartridge, address: int, value: int) -> None:
        if cartridge.chr_rom:
            return
        cartridge.chr_ram[address % len(cartridge.chr_ram)] = value & 0xFF

    def serialize_state(self) -> dict:
        return {"chr_bank": self._chr_bank}

    def deserialize_state(self, state: dict) -> None:
        self._chr_bank = int(state["chr_bank"])
