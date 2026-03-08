"""MOS 6502 CPU core with NES-oriented behavior and bus integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from emulator.interfaces import CPU, MemoryBus

FLAG_CARRY = 0x01
FLAG_ZERO = 0x02
FLAG_INTERRUPT_DISABLE = 0x04
FLAG_DECIMAL = 0x08
FLAG_BREAK = 0x10
FLAG_UNUSED = 0x20
FLAG_OVERFLOW = 0x40
FLAG_NEGATIVE = 0x80


@dataclass
class _AddressingResult:
    address: int
    page_crossed: bool = False


class MOS6502CPU(CPU):
    """Core MOS 6502 CPU implementation used by the NES platform."""

    def __init__(self, bus: MemoryBus, *, debug: bool = False) -> None:
        self.bus = bus
        self.debug = debug
        self._logger = logging.getLogger("platforms.nes.cpu")
        self.cycles = 0
        self.a = 0
        self.x = 0
        self.y = 0
        self.stack_pointer = 0xFD
        self.program_counter = 0
        self.status = FLAG_UNUSED | FLAG_INTERRUPT_DISABLE

    def reset(self) -> None:
        self.a = 0
        self.x = 0
        self.y = 0
        self.stack_pointer = 0xFD
        self.status = FLAG_UNUSED | FLAG_INTERRUPT_DISABLE
        self.program_counter = self._read_u16(0xFFFC)
        self.cycles = 7

    def step(self, bus: MemoryBus) -> int:
        self.bus = bus
        opcode_address = self.program_counter
        opcode = self._fetch_byte()

        if self.debug:
            self._logger.debug(
                "pc=$%04X opcode=$%02X A=$%02X X=$%02X Y=$%02X SP=$%02X P=$%02X",
                opcode_address,
                opcode,
                self.a,
                self.x,
                self.y,
                self.stack_pointer,
                self.status,
            )

        handler = self._instruction_set().get(opcode)
        if handler is None:
            raise NotImplementedError(f"Unsupported opcode {opcode:#04x}")

        consumed = handler()
        self.cycles += consumed
        return consumed

    def serialize_state(self) -> dict:
        return {
            "cycles": self.cycles,
            "a": self.a,
            "x": self.x,
            "y": self.y,
            "stack_pointer": self.stack_pointer,
            "program_counter": self.program_counter,
            "status": self.status,
        }

    def deserialize_state(self, state: dict) -> None:
        self.cycles = int(state["cycles"])
        self.a = int(state["a"])
        self.x = int(state["x"])
        self.y = int(state["y"])
        self.stack_pointer = int(state["stack_pointer"])
        self.program_counter = int(state["program_counter"])
        self.status = int(state["status"])

    def _instruction_set(self) -> dict[int, callable]:
        return {
            0xEA: lambda: 2,
            # LDA
            0xA9: lambda: self._lda(self._immediate(), 2),
            0xA5: lambda: self._lda(self._zero_page(), 3),
            0xB5: lambda: self._lda(self._zero_page_x(), 4),
            0xAD: lambda: self._lda(self._absolute(), 4),
            0xBD: lambda: self._lda(self._absolute_x(), 4, add_page_cycle=True),
            0xB9: lambda: self._lda(self._absolute_y(), 4, add_page_cycle=True),
            0xA1: lambda: self._lda(self._indexed_indirect(), 6),
            0xB1: lambda: self._lda(self._indirect_indexed(), 5, add_page_cycle=True),
            # LDX
            0xA2: lambda: self._ldx(self._immediate(), 2),
            0xA6: lambda: self._ldx(self._zero_page(), 3),
            0xB6: lambda: self._ldx(self._zero_page_y(), 4),
            0xAE: lambda: self._ldx(self._absolute(), 4),
            0xBE: lambda: self._ldx(self._absolute_y(), 4, add_page_cycle=True),
            # LDY
            0xA0: lambda: self._ldy(self._immediate(), 2),
            0xA4: lambda: self._ldy(self._zero_page(), 3),
            0xB4: lambda: self._ldy(self._zero_page_x(), 4),
            0xAC: lambda: self._ldy(self._absolute(), 4),
            0xBC: lambda: self._ldy(self._absolute_x(), 4, add_page_cycle=True),
            # STA/STX/STY
            0x85: lambda: self._sta(self._zero_page(), 3),
            0x95: lambda: self._sta(self._zero_page_x(), 4),
            0x8D: lambda: self._sta(self._absolute(), 4),
            0x9D: lambda: self._sta(self._absolute_x(), 5),
            0x99: lambda: self._sta(self._absolute_y(), 5),
            0x81: lambda: self._sta(self._indexed_indirect(), 6),
            0x91: lambda: self._sta(self._indirect_indexed(), 6),
            0x86: lambda: self._stx(self._zero_page(), 3),
            0x96: lambda: self._stx(self._zero_page_y(), 4),
            0x8E: lambda: self._stx(self._absolute(), 4),
            0x84: lambda: self._sty(self._zero_page(), 3),
            0x94: lambda: self._sty(self._zero_page_x(), 4),
            0x8C: lambda: self._sty(self._absolute(), 4),
            # ADC
            0x69: lambda: self._adc(self._immediate(), 2),
            0x65: lambda: self._adc(self._zero_page(), 3),
            0x75: lambda: self._adc(self._zero_page_x(), 4),
            0x6D: lambda: self._adc(self._absolute(), 4),
            0x7D: lambda: self._adc(self._absolute_x(), 4, add_page_cycle=True),
            0x79: lambda: self._adc(self._absolute_y(), 4, add_page_cycle=True),
            0x61: lambda: self._adc(self._indexed_indirect(), 6),
            0x71: lambda: self._adc(self._indirect_indexed(), 5, add_page_cycle=True),
            # SBC
            0xE9: lambda: self._sbc(self._immediate(), 2),
            0xE5: lambda: self._sbc(self._zero_page(), 3),
            0xF5: lambda: self._sbc(self._zero_page_x(), 4),
            0xED: lambda: self._sbc(self._absolute(), 4),
            0xFD: lambda: self._sbc(self._absolute_x(), 4, add_page_cycle=True),
            0xF9: lambda: self._sbc(self._absolute_y(), 4, add_page_cycle=True),
            0xE1: lambda: self._sbc(self._indexed_indirect(), 6),
            0xF1: lambda: self._sbc(self._indirect_indexed(), 5, add_page_cycle=True),
            # AND/ORA/EOR
            0x29: lambda: self._and(self._immediate(), 2),
            0x25: lambda: self._and(self._zero_page(), 3),
            0x35: lambda: self._and(self._zero_page_x(), 4),
            0x2D: lambda: self._and(self._absolute(), 4),
            0x3D: lambda: self._and(self._absolute_x(), 4, add_page_cycle=True),
            0x39: lambda: self._and(self._absolute_y(), 4, add_page_cycle=True),
            0x21: lambda: self._and(self._indexed_indirect(), 6),
            0x31: lambda: self._and(self._indirect_indexed(), 5, add_page_cycle=True),
            0x09: lambda: self._ora(self._immediate(), 2),
            0x05: lambda: self._ora(self._zero_page(), 3),
            0x15: lambda: self._ora(self._zero_page_x(), 4),
            0x0D: lambda: self._ora(self._absolute(), 4),
            0x1D: lambda: self._ora(self._absolute_x(), 4, add_page_cycle=True),
            0x19: lambda: self._ora(self._absolute_y(), 4, add_page_cycle=True),
            0x01: lambda: self._ora(self._indexed_indirect(), 6),
            0x11: lambda: self._ora(self._indirect_indexed(), 5, add_page_cycle=True),
            0x49: lambda: self._eor(self._immediate(), 2),
            0x45: lambda: self._eor(self._zero_page(), 3),
            0x55: lambda: self._eor(self._zero_page_x(), 4),
            0x4D: lambda: self._eor(self._absolute(), 4),
            0x5D: lambda: self._eor(self._absolute_x(), 4, add_page_cycle=True),
            0x59: lambda: self._eor(self._absolute_y(), 4, add_page_cycle=True),
            0x41: lambda: self._eor(self._indexed_indirect(), 6),
            0x51: lambda: self._eor(self._indirect_indexed(), 5, add_page_cycle=True),
            # BIT
            0x24: lambda: self._bit(self._zero_page(), 3),
            0x2C: lambda: self._bit(self._absolute(), 4),
            # Transfers
            0xAA: lambda: self._tax(),
            0xA8: lambda: self._tay(),
            0x8A: lambda: self._txa(),
            0x98: lambda: self._tya(),
            0xBA: lambda: self._tsx(),
            0x9A: lambda: self._txs(),
            # INC/DEC
            0xE6: lambda: self._inc(self._zero_page(), 5),
            0xF6: lambda: self._inc(self._zero_page_x(), 6),
            0xEE: lambda: self._inc(self._absolute(), 6),
            0xFE: lambda: self._inc(self._absolute_x(), 7),
            0xE8: lambda: self._inx(),
            0xC8: lambda: self._iny(),
            0xC6: lambda: self._dec(self._zero_page(), 5),
            0xD6: lambda: self._dec(self._zero_page_x(), 6),
            0xCE: lambda: self._dec(self._absolute(), 6),
            0xDE: lambda: self._dec(self._absolute_x(), 7),
            0xCA: lambda: self._dex(),
            0x88: lambda: self._dey(),
            # Flow
            0x4C: lambda: self._jmp_absolute(),
            0x6C: lambda: self._jmp_indirect(),
            0x20: lambda: self._jsr(),
            0x60: lambda: self._rts(),
            0x00: lambda: self._brk(),
            0x40: lambda: self._rti(),
            # Branches
            0xF0: lambda: self._branch(self._get_flag(FLAG_ZERO)),
            0xD0: lambda: self._branch(not self._get_flag(FLAG_ZERO)),
            0x90: lambda: self._branch(not self._get_flag(FLAG_CARRY)),
            0xB0: lambda: self._branch(self._get_flag(FLAG_CARRY)),
            0x30: lambda: self._branch(self._get_flag(FLAG_NEGATIVE)),
            0x10: lambda: self._branch(not self._get_flag(FLAG_NEGATIVE)),
            0x50: lambda: self._branch(not self._get_flag(FLAG_OVERFLOW)),
            0x70: lambda: self._branch(self._get_flag(FLAG_OVERFLOW)),
            # Flag controls
            0x18: lambda: self._set_flag_instr(FLAG_CARRY, False),
            0x38: lambda: self._set_flag_instr(FLAG_CARRY, True),
            0x58: lambda: self._set_flag_instr(FLAG_INTERRUPT_DISABLE, False),
            0x78: lambda: self._set_flag_instr(FLAG_INTERRUPT_DISABLE, True),
            0xB8: lambda: self._set_flag_instr(FLAG_OVERFLOW, False),
            0xD8: lambda: self._set_flag_instr(FLAG_DECIMAL, False),
            0xF8: lambda: self._set_flag_instr(FLAG_DECIMAL, True),
        }

    # Addressing helpers
    def _immediate(self) -> _AddressingResult:
        address = self.program_counter
        self.program_counter = (self.program_counter + 1) & 0xFFFF
        return _AddressingResult(address)

    def _zero_page(self) -> _AddressingResult:
        return _AddressingResult(self._fetch_byte())

    def _zero_page_x(self) -> _AddressingResult:
        return _AddressingResult((self._fetch_byte() + self.x) & 0xFF)

    def _zero_page_y(self) -> _AddressingResult:
        return _AddressingResult((self._fetch_byte() + self.y) & 0xFF)

    def _absolute(self) -> _AddressingResult:
        return _AddressingResult(self._fetch_u16())

    def _absolute_x(self) -> _AddressingResult:
        base = self._fetch_u16()
        address = (base + self.x) & 0xFFFF
        return _AddressingResult(address, page_crossed=(base & 0xFF00) != (address & 0xFF00))

    def _absolute_y(self) -> _AddressingResult:
        base = self._fetch_u16()
        address = (base + self.y) & 0xFFFF
        return _AddressingResult(address, page_crossed=(base & 0xFF00) != (address & 0xFF00))

    def _indexed_indirect(self) -> _AddressingResult:
        zp = (self._fetch_byte() + self.x) & 0xFF
        low = self.bus.read(zp)
        high = self.bus.read((zp + 1) & 0xFF)
        return _AddressingResult((high << 8) | low)

    def _indirect_indexed(self) -> _AddressingResult:
        zp = self._fetch_byte()
        low = self.bus.read(zp)
        high = self.bus.read((zp + 1) & 0xFF)
        base = (high << 8) | low
        address = (base + self.y) & 0xFFFF
        return _AddressingResult(address, page_crossed=(base & 0xFF00) != (address & 0xFF00))

    def _indirect(self) -> _AddressingResult:
        pointer = self._fetch_u16()
        low = self.bus.read(pointer)
        high_addr = (pointer & 0xFF00) | ((pointer + 1) & 0x00FF)
        high = self.bus.read(high_addr)
        return _AddressingResult((high << 8) | low)

    # Instruction helpers
    def _lda(self, addr: _AddressingResult, cycles: int, add_page_cycle: bool = False) -> int:
        self.a = self.bus.read(addr.address)
        self._set_zn(self.a)
        return cycles + (1 if add_page_cycle and addr.page_crossed else 0)

    def _ldx(self, addr: _AddressingResult, cycles: int, add_page_cycle: bool = False) -> int:
        self.x = self.bus.read(addr.address)
        self._set_zn(self.x)
        return cycles + (1 if add_page_cycle and addr.page_crossed else 0)

    def _ldy(self, addr: _AddressingResult, cycles: int, add_page_cycle: bool = False) -> int:
        self.y = self.bus.read(addr.address)
        self._set_zn(self.y)
        return cycles + (1 if add_page_cycle and addr.page_crossed else 0)

    def _sta(self, addr: _AddressingResult, cycles: int) -> int:
        self.bus.write(addr.address, self.a)
        return cycles

    def _stx(self, addr: _AddressingResult, cycles: int) -> int:
        self.bus.write(addr.address, self.x)
        return cycles

    def _sty(self, addr: _AddressingResult, cycles: int) -> int:
        self.bus.write(addr.address, self.y)
        return cycles

    def _adc(self, addr: _AddressingResult, cycles: int, add_page_cycle: bool = False) -> int:
        value = self.bus.read(addr.address)
        carry_in = 1 if self._get_flag(FLAG_CARRY) else 0
        result = self.a + value + carry_in
        self._set_flag(FLAG_CARRY, result > 0xFF)
        result8 = result & 0xFF
        overflow = (~(self.a ^ value) & (self.a ^ result8) & 0x80) != 0
        self._set_flag(FLAG_OVERFLOW, overflow)
        self.a = result8
        self._set_zn(self.a)
        return cycles + (1 if add_page_cycle and addr.page_crossed else 0)

    def _sbc(self, addr: _AddressingResult, cycles: int, add_page_cycle: bool = False) -> int:
        value = self.bus.read(addr.address) ^ 0xFF
        carry_in = 1 if self._get_flag(FLAG_CARRY) else 0
        result = self.a + value + carry_in
        self._set_flag(FLAG_CARRY, result > 0xFF)
        result8 = result & 0xFF
        overflow = (~(self.a ^ value) & (self.a ^ result8) & 0x80) != 0
        self._set_flag(FLAG_OVERFLOW, overflow)
        self.a = result8
        self._set_zn(self.a)
        return cycles + (1 if add_page_cycle and addr.page_crossed else 0)

    def _and(self, addr: _AddressingResult, cycles: int, add_page_cycle: bool = False) -> int:
        self.a &= self.bus.read(addr.address)
        self._set_zn(self.a)
        return cycles + (1 if add_page_cycle and addr.page_crossed else 0)

    def _ora(self, addr: _AddressingResult, cycles: int, add_page_cycle: bool = False) -> int:
        self.a |= self.bus.read(addr.address)
        self._set_zn(self.a)
        return cycles + (1 if add_page_cycle and addr.page_crossed else 0)

    def _eor(self, addr: _AddressingResult, cycles: int, add_page_cycle: bool = False) -> int:
        self.a ^= self.bus.read(addr.address)
        self._set_zn(self.a)
        return cycles + (1 if add_page_cycle and addr.page_crossed else 0)

    def _bit(self, addr: _AddressingResult, cycles: int) -> int:
        value = self.bus.read(addr.address)
        self._set_flag(FLAG_ZERO, (self.a & value) == 0)
        self._set_flag(FLAG_NEGATIVE, (value & 0x80) != 0)
        self._set_flag(FLAG_OVERFLOW, (value & 0x40) != 0)
        return cycles

    def _tax(self) -> int:
        self.x = self.a
        self._set_zn(self.x)
        return 2

    def _tay(self) -> int:
        self.y = self.a
        self._set_zn(self.y)
        return 2

    def _txa(self) -> int:
        self.a = self.x
        self._set_zn(self.a)
        return 2

    def _tya(self) -> int:
        self.a = self.y
        self._set_zn(self.a)
        return 2

    def _tsx(self) -> int:
        self.x = self.stack_pointer
        self._set_zn(self.x)
        return 2

    def _txs(self) -> int:
        self.stack_pointer = self.x
        return 2

    def _inc(self, addr: _AddressingResult, cycles: int) -> int:
        value = (self.bus.read(addr.address) + 1) & 0xFF
        self.bus.write(addr.address, value)
        self._set_zn(value)
        return cycles

    def _inx(self) -> int:
        self.x = (self.x + 1) & 0xFF
        self._set_zn(self.x)
        return 2

    def _iny(self) -> int:
        self.y = (self.y + 1) & 0xFF
        self._set_zn(self.y)
        return 2

    def _dec(self, addr: _AddressingResult, cycles: int) -> int:
        value = (self.bus.read(addr.address) - 1) & 0xFF
        self.bus.write(addr.address, value)
        self._set_zn(value)
        return cycles

    def _dex(self) -> int:
        self.x = (self.x - 1) & 0xFF
        self._set_zn(self.x)
        return 2

    def _dey(self) -> int:
        self.y = (self.y - 1) & 0xFF
        self._set_zn(self.y)
        return 2

    def _jmp_absolute(self) -> int:
        self.program_counter = self._fetch_u16()
        return 3

    def _jmp_indirect(self) -> int:
        self.program_counter = self._indirect().address
        return 5

    def _jsr(self) -> int:
        target = self._fetch_u16()
        return_address = (self.program_counter - 1) & 0xFFFF
        self._push((return_address >> 8) & 0xFF)
        self._push(return_address & 0xFF)
        self.program_counter = target
        return 6

    def _rts(self) -> int:
        low = self._pop()
        high = self._pop()
        self.program_counter = (((high << 8) | low) + 1) & 0xFFFF
        return 6

    def _brk(self) -> int:
        self.program_counter = (self.program_counter + 1) & 0xFFFF
        self._push((self.program_counter >> 8) & 0xFF)
        self._push(self.program_counter & 0xFF)
        self._push(self.status | FLAG_BREAK | FLAG_UNUSED)
        self._set_flag(FLAG_INTERRUPT_DISABLE, True)
        self.program_counter = self._read_u16(0xFFFE)
        return 7

    def _rti(self) -> int:
        self.status = self._pop() | FLAG_UNUSED
        self.status &= ~FLAG_BREAK
        low = self._pop()
        high = self._pop()
        self.program_counter = (high << 8) | low
        return 6

    def _branch(self, condition: bool) -> int:
        offset = self._fetch_byte()
        cycles = 2
        if condition:
            cycles += 1
            old_pc = self.program_counter
            if offset & 0x80:
                offset -= 0x100
            self.program_counter = (self.program_counter + offset) & 0xFFFF
            if (old_pc & 0xFF00) != (self.program_counter & 0xFF00):
                cycles += 1
        return cycles

    def _set_flag_instr(self, flag: int, enabled: bool) -> int:
        self._set_flag(flag, enabled)
        return 2

    # Utility helpers
    def _fetch_byte(self) -> int:
        value = self.bus.read(self.program_counter)
        self.program_counter = (self.program_counter + 1) & 0xFFFF
        return value

    def _fetch_u16(self) -> int:
        low = self._fetch_byte()
        high = self._fetch_byte()
        return (high << 8) | low

    def _read_u16(self, address: int) -> int:
        low = self.bus.read(address)
        high = self.bus.read((address + 1) & 0xFFFF)
        return (high << 8) | low

    def _push(self, value: int) -> None:
        self.bus.write(0x0100 + self.stack_pointer, value & 0xFF)
        self.stack_pointer = (self.stack_pointer - 1) & 0xFF

    def _pop(self) -> int:
        self.stack_pointer = (self.stack_pointer + 1) & 0xFF
        return self.bus.read(0x0100 + self.stack_pointer)

    def _set_flag(self, flag: int, enabled: bool) -> None:
        if enabled:
            self.status |= flag
        else:
            self.status &= ~flag
        self.status |= FLAG_UNUSED

    def _get_flag(self, flag: int) -> bool:
        return (self.status & flag) != 0

    def _set_zn(self, value: int) -> None:
        self._set_flag(FLAG_ZERO, (value & 0xFF) == 0)
        self._set_flag(FLAG_NEGATIVE, (value & 0x80) != 0)
