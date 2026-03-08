"""HuC6280 instruction decoding extensions built on top of the 6502 core."""

from __future__ import annotations

from .addressing_modes import decode_block_transfer


class HuC6280InstructionDecoder:
    """Provides HuC6280-specific opcode handlers."""

    TIMER_CONTROL_PORTS = (0x1FF0, 0x1FF1, 0x1FF2)

    def extension_handlers(self) -> dict[int, callable]:
        return {
            # Transfer Accumulator to Memory Page Registers
            0x53: self._tam,
            # Transfer Memory Page Register to Accumulator
            0x43: self._tma,
            # Block transfer family
            0x73: self._tii,
            0xC3: self._tdd,
            0xD3: self._tin,
            0xE3: self._tia,
            0xF3: self._tai,
            # Timer/control register immediate store helpers
            0x03: lambda: self._store_timer_port(0),
            0x13: lambda: self._store_timer_port(1),
            0x23: lambda: self._store_timer_port(2),
        }

    def _tam(self) -> int:
        mask = self._fetch_byte()
        self.bank_registers.set_masked(mask, self.a)
        return 5

    def _tma(self) -> int:
        mask = self._fetch_byte()
        self.a = self.bank_registers.get_masked(mask)
        self._set_zn(self.a)
        return 5

    def _tii(self) -> int:
        operands = decode_block_transfer(self._fetch_u16)
        for offset in range(operands.length):
            value = self.bus.read((operands.source + offset) & 0xFFFF)
            self.bus.write((operands.destination + offset) & 0xFFFF, value)
        return 17 + (6 * operands.length)

    def _tdd(self) -> int:
        operands = decode_block_transfer(self._fetch_u16)
        for offset in range(operands.length):
            value = self.bus.read((operands.source - offset) & 0xFFFF)
            self.bus.write((operands.destination - offset) & 0xFFFF, value)
        return 17 + (6 * operands.length)

    def _tin(self) -> int:
        operands = decode_block_transfer(self._fetch_u16)
        for offset in range(operands.length):
            value = self.bus.read((operands.source + offset) & 0xFFFF)
            self.bus.write(operands.destination & 0xFFFF, value)
        return 17 + (6 * operands.length)

    def _tia(self) -> int:
        operands = decode_block_transfer(self._fetch_u16)
        for offset in range(operands.length):
            value = self.bus.read((operands.source + offset) & 0xFFFF)
            destination = (operands.destination + (offset & 0x01)) & 0xFFFF
            self.bus.write(destination, value)
        return 17 + (6 * operands.length)

    def _tai(self) -> int:
        operands = decode_block_transfer(self._fetch_u16)
        for offset in range(operands.length):
            source = (operands.source + (offset & 0x01)) & 0xFFFF
            value = self.bus.read(source)
            self.bus.write((operands.destination + offset) & 0xFFFF, value)
        return 17 + (6 * operands.length)

    def _store_timer_port(self, index: int) -> int:
        value = self._fetch_byte()
        self.bus.write(self.TIMER_CONTROL_PORTS[index], value)
        return 4
