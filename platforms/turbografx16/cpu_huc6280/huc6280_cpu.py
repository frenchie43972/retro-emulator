"""HuC6280 CPU implementation for the TurboGrafx-16 platform."""

from __future__ import annotations

from emulator.interfaces import MemoryBus
from platforms.nes.cpu_6502.cpu import MOS6502CPU

from .bank_registers import HuC6280BankRegisters
from .instruction_decoder import HuC6280InstructionDecoder


class _HuC6280MappedBus(MemoryBus):
    """Translates HuC6280 logical addresses to physical bus addresses."""

    def __init__(self, backing_bus: MemoryBus, bank_registers: HuC6280BankRegisters) -> None:
        self._backing_bus = backing_bus
        self._bank_registers = bank_registers

    def attach(self, backing_bus: MemoryBus) -> None:
        self._backing_bus = backing_bus

    def read(self, address: int) -> int:
        physical = self._bank_registers.map_logical(address)
        return self._backing_bus.read(physical)

    def write(self, address: int, value: int) -> None:
        physical = self._bank_registers.map_logical(address)
        self._backing_bus.write(physical, value)


class HuC6280CPU(HuC6280InstructionDecoder, MOS6502CPU):
    """HuC6280 implementation that reuses the base 6502 instruction core."""

    def __init__(self, bus: MemoryBus, *, debug: bool = False) -> None:
        self.bank_registers = HuC6280BankRegisters()
        self._mapped_bus = _HuC6280MappedBus(bus, self.bank_registers)
        self._backing_bus = bus
        super().__init__(self._mapped_bus, debug=debug)

    def attach_bus(self, bus: MemoryBus) -> None:
        self._backing_bus = bus
        self._mapped_bus.attach(bus)

    def reset(self) -> None:
        self.bank_registers.reset()
        self._mapped_bus.attach(self._backing_bus)
        super().reset()

    def step(self, bus: MemoryBus) -> int:
        self.attach_bus(bus)
        return super().step(self._mapped_bus)

    def _instruction_set(self) -> dict[int, callable]:
        instruction_set = super()._instruction_set()
        instruction_set.update(self.extension_handlers())
        return instruction_set
