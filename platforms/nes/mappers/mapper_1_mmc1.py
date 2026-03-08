"""Mapper 1 (MMC1) implementation."""

from __future__ import annotations

from .mapper_base import MapperCPURegion, NESMapper


class Mapper1MMC1(NESMapper):
    def __init__(self) -> None:
        self._shift_register = 0x10
        self._control = 0x0C
        self._chr_bank0 = 0
        self._chr_bank1 = 0
        self._prg_bank = 0

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
            return self._read_prg(cartridge, address)
        raise KeyError(f"Mapper1 read out of range: {address:#06x}")

    def cpu_write(self, cartridge, address: int, value: int) -> None:
        value &= 0xFF
        if 0x6000 <= address <= 0x7FFF and cartridge.ram is not None:
            cartridge.ram[address - 0x6000] = value
            return
        if not (0x8000 <= address <= 0xFFFF):
            raise KeyError(f"Mapper1 write out of range: {address:#06x}")

        if value & 0x80:
            self._shift_register = 0x10
            self._control |= 0x0C
            return

        complete = (self._shift_register & 0x01) == 0x01
        self._shift_register >>= 1
        self._shift_register |= (value & 0x01) << 4

        if complete:
            data = self._shift_register & 0x1F
            if 0x8000 <= address <= 0x9FFF:
                self._control = data
            elif 0xA000 <= address <= 0xBFFF:
                self._chr_bank0 = data
            elif 0xC000 <= address <= 0xDFFF:
                self._chr_bank1 = data
            else:
                self._prg_bank = data & 0x0F
            self._shift_register = 0x10

    def ppu_read(self, cartridge, address: int) -> int:
        if cartridge.chr_rom:
            return self._read_chr_rom(cartridge, address & 0x1FFF)
        return cartridge.chr_ram[address % len(cartridge.chr_ram)]

    def ppu_write(self, cartridge, address: int, value: int) -> None:
        if cartridge.chr_rom:
            return
        cartridge.chr_ram[address % len(cartridge.chr_ram)] = value & 0xFF

    def mirroring(self, cartridge) -> str:
        mode = self._control & 0x03
        if mode == 0:
            return "single0"
        if mode == 1:
            return "single1"
        if mode == 2:
            return "vertical"
        return "horizontal"

    def _read_prg(self, cartridge, address: int) -> int:
        bank_count = max(1, len(cartridge.prg_rom) // 0x4000)
        mode = (self._control >> 2) & 0x03

        if mode in (0, 1):
            base = ((self._prg_bank & 0x0E) % bank_count) * 0x4000
            return cartridge.prg_rom[base + (address - 0x8000)]
        if mode == 2:
            if address < 0xC000:
                return cartridge.prg_rom[address - 0x8000]
            bank = self._prg_bank % bank_count
            return cartridge.prg_rom[bank * 0x4000 + (address - 0xC000)]

        # mode == 3
        if address < 0xC000:
            bank = self._prg_bank % bank_count
            return cartridge.prg_rom[bank * 0x4000 + (address - 0x8000)]
        last_bank = bank_count - 1
        return cartridge.prg_rom[last_bank * 0x4000 + (address - 0xC000)]

    def _read_chr_rom(self, cartridge, address: int) -> int:
        chr_mode = (self._control >> 4) & 0x01
        if chr_mode == 0:
            bank_count = max(1, len(cartridge.chr_rom) // 0x2000)
            bank = (self._chr_bank0 & 0x1E) % bank_count
            return cartridge.chr_rom[bank * 0x2000 + address]

        bank4k_count = max(1, len(cartridge.chr_rom) // 0x1000)
        if address < 0x1000:
            bank = self._chr_bank0 % bank4k_count
            return cartridge.chr_rom[bank * 0x1000 + address]
        bank = self._chr_bank1 % bank4k_count
        return cartridge.chr_rom[bank * 0x1000 + (address - 0x1000)]
