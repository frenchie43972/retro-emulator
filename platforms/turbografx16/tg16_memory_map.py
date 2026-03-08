"""TurboGrafx-16 physical memory map and placeholder hardware registers."""

from __future__ import annotations

from dataclasses import dataclass

from emulator.bus import MappedMemoryBus
from emulator.interfaces import MemoryDevice

from .hucard_loader import LoadedHuCard
from .tg16_ram import TG16RAM


class TG16HardwareRegisters(MemoryDevice):
    """Placeholder VDC/VCE/PSG register block."""

    def __init__(self) -> None:
        self._data = bytearray(0x400)

    def read(self, address: int) -> int:
        return self._data[address & 0x3FF]

    def write(self, address: int, value: int) -> None:
        self._data[address & 0x3FF] = value & 0xFF


class HuCardROMDevice(MemoryDevice):
    """Maps HuCard bytes into TurboGrafx physical ROM space."""

    def __init__(self) -> None:
        self._loaded: LoadedHuCard | None = None

    def load(self, loaded: LoadedHuCard) -> None:
        self._loaded = loaded

    def read(self, address: int) -> int:
        if self._loaded is None:
            return 0xFF
        return self._loaded.read_physical(address)

    def write(self, address: int, value: int) -> None:
        _ = address, value


@dataclass
class TG16MemoryMap:
    """Owns and attaches the TurboGrafx-16 physical memory ranges."""

    bus: MappedMemoryBus
    rom: HuCardROMDevice
    ram: TG16RAM
    registers: TG16HardwareRegisters

    @classmethod
    def create(cls, bus: MappedMemoryBus) -> "TG16MemoryMap":
        instance = cls(
            bus=bus,
            rom=HuCardROMDevice(),
            ram=TG16RAM(),
            registers=TG16HardwareRegisters(),
        )
        instance.attach()
        return instance

    def attach(self) -> None:
        # ROM with holes for RAM and hardware register windows.
        self.bus.register(0x000000, 0x1EFFFF, self.rom)
        self.bus.register(0x1F2000, 0x1FDFFF, self.rom)
        self.bus.register(0x1FE400, 0x1FFFFF, self.rom)

        # Internal RAM and I/O windows.
        self.bus.register(0x1F0000, 0x1F1FFF, self.ram)
        self.bus.register(0x1FE000, 0x1FE3FF, self.registers)
