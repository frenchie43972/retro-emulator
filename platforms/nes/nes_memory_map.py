"""NES CPU memory map devices and bus wiring."""

from __future__ import annotations

import logging

from emulator.bus import MappedMemoryBus
from emulator.interfaces import MemoryDevice

from .nes_ram import NESRAM
from .ppu import NESPPU


class NESMemoryBus(MappedMemoryBus):
    """Mapped bus with optional debug logging for memory access tracing."""

    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        self.debug = debug
        self._logger = logging.getLogger("platforms.nes.bus")

    def read(self, address: int) -> int:
        value = super().read(address)
        if self.debug:
            self._logger.debug("read  $%04X -> $%02X", address, value)
        return value

    def write(self, address: int, value: int) -> None:
        if self.debug:
            self._logger.debug("write $%04X <- $%02X", address, value)
        super().write(address, value)


class _MirroredRegisterDevice(MemoryDevice):
    def __init__(self, register_count: int) -> None:
        self._registers = bytearray(register_count)
        self._register_count = register_count

    def read(self, address: int) -> int:
        return self._registers[address % self._register_count]

    def write(self, address: int, value: int) -> None:
        self._registers[address % self._register_count] = value & 0xFF


class APUIORegisterPlaceholder(_MirroredRegisterDevice):
    """Placeholder for NES APU/I-O registers ($4000-$4017)."""

    def __init__(self) -> None:
        super().__init__(register_count=0x18)


class DisabledRegisterPlaceholder(MemoryDevice):
    """Placeholder for disabled/test register range ($4018-$401F)."""

    def read(self, address: int) -> int:
        return 0

    def write(self, address: int, value: int) -> None:
        _ = (address, value)


class OpenBusPlaceholder(MemoryDevice):
    """Open bus area in cartridge space before PRG RAM/ROM mapping."""

    def read(self, address: int) -> int:
        _ = address
        return 0

    def write(self, address: int, value: int) -> None:
        _ = (address, value)


class NESMemoryMap:
    """Configures NES CPU-visible memory layout on the emulator bus."""

    def __init__(self, bus: NESMemoryBus, ppu: NESPPU) -> None:
        self.bus = bus
        self.ram = NESRAM()
        self.ppu = ppu
        self.apu_io = APUIORegisterPlaceholder()
        self.disabled = DisabledRegisterPlaceholder()
        self.open_bus = OpenBusPlaceholder()

    def attach(self) -> None:
        self.bus.register(0x0000, 0x1FFF, self.ram)
        self.bus.register(0x2000, 0x3FFF, self.ppu)
        self.bus.register(0x4000, 0x4017, self.apu_io)
        self.bus.register(0x4018, 0x401F, self.disabled)
        self.bus.register(0x4020, 0x5FFF, self.open_bus)

    def reset(self) -> None:
        self.ram.reset()
