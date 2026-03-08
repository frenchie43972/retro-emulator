"""Base classes for NES cartridge mappers."""

from __future__ import annotations

from emulator.interfaces import MemoryDevice

if False:  # pragma: no cover
    from core.cartridge.base import LoadedCartridge


class MapperCPURegion(MemoryDevice):
    """Memory bus adapter that routes CPU accesses to a mapper."""

    def __init__(self, cartridge: "LoadedCartridge", base_address: int) -> None:
        self._cartridge = cartridge
        self._base_address = base_address

    def read(self, address: int) -> int:
        return self._cartridge.read(self._base_address + address)

    def write(self, address: int, value: int) -> None:
        self._cartridge.write(self._base_address + address, value)


class NESMapper:
    """Contract for NES mapper behavior across CPU and PPU buses."""

    def cpu_mappings(self, cartridge: "LoadedCartridge") -> list[tuple[int, int, MemoryDevice]]:  # pragma: no cover
        raise NotImplementedError

    def cpu_read(self, cartridge: "LoadedCartridge", address: int) -> int:  # pragma: no cover
        raise NotImplementedError

    def cpu_write(self, cartridge: "LoadedCartridge", address: int, value: int) -> None:  # pragma: no cover
        raise NotImplementedError

    def ppu_read(self, cartridge: "LoadedCartridge", address: int) -> int:  # pragma: no cover
        raise NotImplementedError

    def ppu_write(self, cartridge: "LoadedCartridge", address: int, value: int) -> None:  # pragma: no cover
        raise NotImplementedError

    def mirroring(self, cartridge: "LoadedCartridge") -> str:
        return cartridge.metadata.mirroring

    def serialize_state(self) -> dict:
        return {}

    def deserialize_state(self, state: dict) -> None:
        _ = state
