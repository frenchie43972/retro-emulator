"""PPU memory model for pattern/name/attribute/palette regions."""

from __future__ import annotations

from core.cartridge.base import LoadedCartridge


class PPUMemory:
    def __init__(self) -> None:
        self._cartridge: LoadedCartridge | None = None
        self._chr_ram = bytearray(0x2000)
        self._nametables = bytearray(0x800)
        self._palette_ram = bytearray(0x20)

    def set_cartridge(self, cartridge: LoadedCartridge | None) -> None:
        self._cartridge = cartridge
        if cartridge is not None and not cartridge.chr_rom:
            self._chr_ram = bytearray(0x2000)

    def read(self, address: int) -> int:
        local = address & 0x3FFF
        if local < 0x2000:
            return self._read_pattern(local)
        if local < 0x3F00:
            return self._nametables[self._map_nametable_address(local)]
        return self._palette_ram[self._map_palette_address(local)]

    def write(self, address: int, value: int) -> None:
        value &= 0xFF
        local = address & 0x3FFF
        if local < 0x2000:
            self._write_pattern(local, value)
            return
        if local < 0x3F00:
            if 0x2000 <= local <= 0x23FF:
                print("[ppu] write", hex(local), value)
            self._nametables[self._map_nametable_address(local)] = value
            return
        self._palette_ram[self._map_palette_address(local)] = value

    def _read_pattern(self, address: int) -> int:
        if self._cartridge is not None:
            return self._cartridge.ppu_read(address)
        return self._chr_ram[address]

    def _write_pattern(self, address: int, value: int) -> None:
        if self._cartridge is not None:
            self._cartridge.ppu_write(address, value)
            return
        self._chr_ram[address] = value

    def _map_nametable_address(self, address: int) -> int:
        mirrored = (address - 0x2000) % 0x1000
        table = mirrored // 0x400
        offset = mirrored % 0x400
        mirroring = self._cartridge.mirroring() if self._cartridge is not None else "horizontal"
        if mirroring == "vertical":
            physical_table = table % 2
        elif mirroring == "single0":
            physical_table = 0
        elif mirroring == "single1":
            physical_table = 1
        else:
            physical_table = table // 2
        return physical_table * 0x400 + offset

    def _map_palette_address(self, address: int) -> int:
        local = (address - 0x3F00) % 0x20
        if local in {0x10, 0x14, 0x18, 0x1C}:
            local -= 0x10
        return local


    def serialize_state(self) -> dict:
        return {
            "chr_ram": bytes(self._chr_ram),
            "nametables": bytes(self._nametables),
            "palette_ram": bytes(self._palette_ram),
        }

    def deserialize_state(self, state: dict) -> None:
        for key, target in (("chr_ram", self._chr_ram), ("nametables", self._nametables), ("palette_ram", self._palette_ram)):
            incoming = state[key]
            if len(incoming) != len(target):
                raise ValueError(f"PPU {key} size mismatch in save state")
            target[:] = incoming
