"""NES CPU memory map devices and bus wiring."""

from __future__ import annotations

import logging

from emulator.bus import MappedMemoryBus
from emulator.interfaces import MemoryDevice

from .apu import NESAPU
from .input.controller_registers import ControllerRegisters
from .input.nes_controller import NESController
from .nes_ram import NESRAM
from .ppu import NESPPU


class NESMemoryBus(MappedMemoryBus):
    """Mapped bus with optional debug logging for memory access tracing."""

    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        self.debug = debug
        self._logger = logging.getLogger("platforms.nes.bus")
        self._controller: NESController | None = None

    def set_controller(self, controller: "NESController") -> None:
        """Attach controller for direct $4016 CPU-bus access."""

        self._controller = controller

    def read(self, address: int) -> int:
        if address == 0x4016 and self._controller is not None:
            value = self._controller.read()
        else:
            value = super().read(address)
        if self.debug:
            self._logger.debug("read  $%04X -> $%02X", address, value)
        return value

    def write(self, address: int, value: int) -> None:
        if self.debug:
            self._logger.debug("write $%04X <- $%02X", address, value)
        if address == 0x4016 and self._controller is not None:
            self._controller.write(value)
            return
        super().write(address, value)


class IORegisterBridge(MemoryDevice):
    """Bridges $4016/$4017 behavior between controller and APU."""

    def __init__(self, controllers: ControllerRegisters, apu: NESAPU) -> None:
        self.controllers = controllers
        self.apu = apu

    def read(self, address: int) -> int:
        return self.controllers.read(address)

    def write(self, address: int, value: int) -> None:
        if address == 0:
            self.controllers.write(address, value)
            return
        if address == 1:
            self.apu.write_frame_counter(value)


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

    def __init__(self, bus: NESMemoryBus, ppu: NESPPU, controller1: NESController, apu: NESAPU) -> None:
        self.bus = bus
        self.ram = NESRAM()
        self.ppu = ppu
        self.apu = apu
        self.controllers = ControllerRegisters(controller1=controller1)
        self.bus.set_controller(controller1)
        self.io_registers = IORegisterBridge(controllers=self.controllers, apu=self.apu)
        self.disabled = DisabledRegisterPlaceholder()
        self.open_bus = OpenBusPlaceholder()

    def attach(self) -> None:
        self.bus.register(0x0000, 0x1FFF, self.ram)
        self.bus.register(0x2000, 0x3FFF, self.ppu)
        self.bus.register(0x4000, 0x4015, self.apu)
        self.bus.register(0x4016, 0x4017, self.io_registers)
        self.bus.register(0x4018, 0x401F, self.disabled)
        self.bus.register(0x4020, 0x5FFF, self.open_bus)

    def reset(self) -> None:
        self.ram.reset()


    def serialize_state(self) -> dict:
        return {
            "ram": self.ram.serialize_state(),
            "controllers": self.controllers.serialize_state(),
        }

    def deserialize_state(self, state: dict) -> None:
        self.ram.deserialize_state(state["ram"])
        self.controllers.deserialize_state(state["controllers"])
