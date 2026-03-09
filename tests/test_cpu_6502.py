import unittest

from emulator.bus import MappedMemoryBus, RAM
from platforms.nes.cpu_6502.cpu import (
    FLAG_BREAK,
    FLAG_CARRY,
    FLAG_INTERRUPT_DISABLE,
    FLAG_NEGATIVE,
    FLAG_OVERFLOW,
    FLAG_ZERO,
    MOS6502CPU,
)


class MOS6502CPUTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = MappedMemoryBus()
        self.ram = RAM(0x10000)
        self.bus.register(0x0000, 0xFFFF, self.ram)

        # Reset vector -> 0x8000
        self.bus.write(0xFFFC, 0x00)
        self.bus.write(0xFFFD, 0x80)

        self.cpu = MOS6502CPU(self.bus)
        self.cpu.reset()

    def _load_program(self, program: list[int], start: int = 0x8000) -> None:
        for idx, byte in enumerate(program):
            self.bus.write(start + idx, byte)
        self.cpu.program_counter = start

    def test_reset_loads_vector_and_initializes_state(self):
        self.assertEqual(self.cpu.program_counter, 0x8000)
        self.assertEqual(self.cpu.stack_pointer, 0xFD)
        self.assertEqual(self.cpu.a, 0)
        self.assertEqual(self.cpu.x, 0)
        self.assertEqual(self.cpu.y, 0)
        self.assertTrue(self.cpu.status & FLAG_INTERRUPT_DISABLE)
        self.assertEqual(self.cpu.cycles, 7)

    def test_lda_immediate_and_flags(self):
        self._load_program([0xA9, 0x00, 0xA9, 0x80])

        self.assertEqual(self.cpu.step(self.bus), 2)
        self.assertEqual(self.cpu.a, 0x00)
        self.assertTrue(self.cpu.status & FLAG_ZERO)

        self.assertEqual(self.cpu.step(self.bus), 2)
        self.assertEqual(self.cpu.a, 0x80)
        self.assertTrue(self.cpu.status & FLAG_NEGATIVE)

    def test_adc_and_sbc(self):
        self._load_program([
            0xA9,
            0x10,  # LDA #$10
            0x18,  # CLC
            0x69,
            0x20,  # ADC #$20 => $30
            0x38,  # SEC
            0xE9,
            0x10,  # SBC #$10 => $20
        ])

        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.a, 0x30)
        self.assertEqual(self.cpu.status & FLAG_CARRY, 0)

        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.a, 0x20)


    def test_bit_updates_flags_and_preserves_accumulator_zero_page(self):
        self.bus.write(0x0010, 0xC0)
        self._load_program([
            0xA9,
            0x3F,  # LDA #$3F
            0x24,
            0x10,  # BIT $10
        ])

        self.cpu.step(self.bus)
        cycles = self.cpu.step(self.bus)

        self.assertEqual(cycles, 3)
        self.assertEqual(self.cpu.a, 0x3F)
        self.assertEqual(self.cpu.status & FLAG_ZERO, FLAG_ZERO)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, FLAG_NEGATIVE)
        self.assertEqual(self.cpu.status & FLAG_OVERFLOW, FLAG_OVERFLOW)

    def test_bit_absolute_updates_zero_negative_and_overflow_flags(self):
        self.bus.write(0x1234, 0x00)
        self._load_program([
            0xA9,
            0xFF,  # LDA #$FF
            0x2C,
            0x34,
            0x12,  # BIT $1234
        ])

        self.cpu.step(self.bus)
        cycles = self.cpu.step(self.bus)

        self.assertEqual(cycles, 4)
        self.assertEqual(self.cpu.a, 0xFF)
        self.assertEqual(self.cpu.status & FLAG_ZERO, FLAG_ZERO)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)
        self.assertEqual(self.cpu.status & FLAG_OVERFLOW, 0)

    def test_zero_page_indexed_addressing(self):
        self.bus.write(0x0042, 0xAB)
        self._load_program([
            0xA2,
            0x02,  # LDX #$02
            0xB5,
            0x40,  # LDA $40,X => $42
            0x95,
            0x50,  # STA $50,X => $52
        ])

        self.cpu.step(self.bus)
        cycles = self.cpu.step(self.bus)
        self.assertEqual(cycles, 4)
        self.assertEqual(self.cpu.a, 0xAB)

        self.cpu.step(self.bus)
        self.assertEqual(self.bus.read(0x0052), 0xAB)

    def test_indirect_modes_and_cycle_penalty(self):
        self.bus.write(0x0020, 0x34)
        self.bus.write(0x0021, 0x12)
        self.bus.write(0x1234, 0x77)

        self.bus.write(0x0030, 0xFF)
        self.bus.write(0x0031, 0x12)
        self.bus.write(0x1300, 0x66)

        self._load_program([
            0xA2,
            0x00,  # LDX #$00
            0xA1,
            0x20,  # LDA ($20,X) => $1234
            0xA0,
            0x01,  # LDY #$01
            0xB1,
            0x30,  # LDA ($30),Y => $1300 page-crossing
        ])

        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.a, 0x77)

        self.cpu.step(self.bus)
        cycles = self.cpu.step(self.bus)
        self.assertEqual(self.cpu.a, 0x66)
        self.assertEqual(cycles, 6)

    def test_branch_relative(self):
        self._load_program([
            0xA9,
            0x00,  # LDA #$00 (sets Z)
            0xF0,
            0x02,  # BEQ +2
            0xA9,
            0x01,  # skipped
            0xA9,
            0x02,  # executed
        ])

        self.cpu.step(self.bus)
        cycles = self.cpu.step(self.bus)
        self.assertEqual(cycles, 3)

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.a, 0x02)

    def test_jsr_and_rts(self):
        self._load_program([
            0x20,
            0x06,
            0x80,  # JSR $8006
            0xA9,
            0x03,  # LDA #$03
            0xEA,  # NOP
            0xA9,
            0x0A,  # subroutine: LDA #$0A
            0x60,  # RTS
        ])

        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.a, 0x0A)

        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.a, 0x03)

    def test_trigger_nmi_pushes_state_and_jumps_to_nmi_vector(self):
        self.bus.write(0xFFFA, 0x34)
        self.bus.write(0xFFFB, 0x12)
        self.cpu.program_counter = 0xC123
        self.cpu.status = FLAG_ZERO

        self.cpu.trigger_nmi()

        self.assertEqual(self.cpu.program_counter, 0x1234)
        self.assertTrue(self.cpu.status & FLAG_INTERRUPT_DISABLE)
        self.assertEqual(self.cpu.stack_pointer, 0xFA)
        self.assertEqual(self.bus.read(0x01FD), 0xC1)
        self.assertEqual(self.bus.read(0x01FC), 0x23)
        self.assertEqual(self.bus.read(0x01FB), FLAG_ZERO | 0x20)

    def test_cmp_immediate_updates_flags_and_preserves_accumulator(self):
        self._load_program([
            0xA9,
            0x50,  # LDA #$50
            0xC9,
            0x40,  # CMP #$40 (A > M)
            0xC9,
            0x50,  # CMP #$50 (A == M)
            0xC9,
            0x60,  # CMP #$60 (A < M)
        ])

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.a, 0x50)

        cycles = self.cpu.step(self.bus)
        self.assertEqual(cycles, 2)
        self.assertEqual(self.cpu.a, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_ZERO, 0)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.a, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_ZERO, FLAG_ZERO)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.a, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, 0)
        self.assertEqual(self.cpu.status & FLAG_ZERO, 0)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, FLAG_NEGATIVE)

    def test_cmp_addressing_modes_and_cycles(self):
        self.bus.write(0x0010, 0x20)
        self.bus.write(0x0012, 0x50)
        self.bus.write(0x1234, 0x10)
        self.bus.write(0x1300, 0x50)
        self.bus.write(0x1400, 0x10)

        self.bus.write(0x0020, 0x00)
        self.bus.write(0x0021, 0x14)

        self.bus.write(0x0030, 0xFF)
        self.bus.write(0x0031, 0x12)

        self._load_program([
            0xA9,
            0x50,  # LDA #$50
            0xA2,
            0x02,  # LDX #$02
            0xA0,
            0x01,  # LDY #$01
            0xC5,
            0x10,  # CMP $10
            0xD5,
            0x10,  # CMP $10,X => $12
            0xCD,
            0x34,
            0x12,  # CMP $1234
            0xDD,
            0xFF,
            0x12,  # CMP $12FF,X => $1301 page-crossing
            0xD9,
            0xFF,
            0x13,  # CMP $13FF,Y => $1400 page-crossing
            0xC1,
            0x1E,  # CMP ($1E,X) => ($20)
            0xD1,
            0x30,  # CMP ($30),Y => $1300 page-crossing
        ])

        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.cpu.step(self.bus)

        self.assertEqual(self.cpu.step(self.bus), 3)
        self.assertEqual(self.cpu.step(self.bus), 4)
        self.assertEqual(self.cpu.step(self.bus), 4)
        self.assertEqual(self.cpu.step(self.bus), 5)
        self.assertEqual(self.cpu.step(self.bus), 5)
        self.assertEqual(self.cpu.step(self.bus), 6)
        self.assertEqual(self.cpu.step(self.bus), 6)
        self.assertEqual(self.cpu.a, 0x50)

    def test_cpx_immediate_updates_flags_and_preserves_register(self):
        self._load_program([
            0xA2,
            0x50,  # LDX #$50
            0xE0,
            0x40,  # CPX #$40 (X > M)
            0xE0,
            0x50,  # CPX #$50 (X == M)
            0xE0,
            0x60,  # CPX #$60 (X < M)
        ])

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.x, 0x50)

        cycles = self.cpu.step(self.bus)
        self.assertEqual(cycles, 2)
        self.assertEqual(self.cpu.x, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_ZERO, 0)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.x, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_ZERO, FLAG_ZERO)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.x, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, 0)
        self.assertEqual(self.cpu.status & FLAG_ZERO, 0)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, FLAG_NEGATIVE)

    def test_cpx_zero_page_and_absolute_modes(self):
        self.bus.write(0x0010, 0x20)
        self.bus.write(0x1234, 0x60)

        self._load_program([
            0xA2,
            0x50,  # LDX #$50
            0xE4,
            0x10,  # CPX $10
            0xEC,
            0x34,
            0x12,  # CPX $1234
        ])

        self.cpu.step(self.bus)

        self.assertEqual(self.cpu.step(self.bus), 3)
        self.assertEqual(self.cpu.x, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

        self.assertEqual(self.cpu.step(self.bus), 4)
        self.assertEqual(self.cpu.x, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, 0)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, FLAG_NEGATIVE)

    def test_cpy_immediate_updates_flags_and_preserves_register(self):
        self._load_program([
            0xA0,
            0x50,  # LDY #$50
            0xC0,
            0x40,  # CPY #$40 (Y > M)
            0xC0,
            0x50,  # CPY #$50 (Y == M)
            0xC0,
            0x60,  # CPY #$60 (Y < M)
        ])

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.y, 0x50)

        cycles = self.cpu.step(self.bus)
        self.assertEqual(cycles, 2)
        self.assertEqual(self.cpu.y, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_ZERO, 0)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.y, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_ZERO, FLAG_ZERO)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.y, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, 0)
        self.assertEqual(self.cpu.status & FLAG_ZERO, 0)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, FLAG_NEGATIVE)

    def test_cpy_zero_page_and_absolute_modes(self):
        self.bus.write(0x0010, 0x20)
        self.bus.write(0x1234, 0x60)

        self._load_program([
            0xA0,
            0x50,  # LDY #$50
            0xC4,
            0x10,  # CPY $10
            0xCC,
            0x34,
            0x12,  # CPY $1234
        ])

        self.cpu.step(self.bus)

        self.assertEqual(self.cpu.step(self.bus), 3)
        self.assertEqual(self.cpu.y, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

        self.assertEqual(self.cpu.step(self.bus), 4)
        self.assertEqual(self.cpu.y, 0x50)
        self.assertEqual(self.cpu.status & FLAG_CARRY, 0)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, FLAG_NEGATIVE)

    def test_pha_and_pla_round_trip_updates_stack_and_flags(self):
        self._load_program([
            0xA9,
            0x00,  # LDA #$00
            0x48,  # PHA
            0xA9,
            0x80,  # LDA #$80
            0x48,  # PHA
            0x68,  # PLA => $80
            0x68,  # PLA => $00
        ])

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.step(self.bus), 3)
        self.assertEqual(self.bus.read(0x01FD), 0x00)
        self.assertEqual(self.cpu.stack_pointer, 0xFC)

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.step(self.bus), 3)
        self.assertEqual(self.bus.read(0x01FC), 0x80)
        self.assertEqual(self.cpu.stack_pointer, 0xFB)

        self.assertEqual(self.cpu.step(self.bus), 4)
        self.assertEqual(self.cpu.a, 0x80)
        self.assertEqual(self.cpu.stack_pointer, 0xFC)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, FLAG_NEGATIVE)
        self.assertEqual(self.cpu.status & FLAG_ZERO, 0)

        self.assertEqual(self.cpu.step(self.bus), 4)
        self.assertEqual(self.cpu.a, 0x00)
        self.assertEqual(self.cpu.stack_pointer, 0xFD)
        self.assertEqual(self.cpu.status & FLAG_ZERO, FLAG_ZERO)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

    def test_php_and_plp_round_trip_restores_status(self):
        self.cpu.status = FLAG_CARRY | FLAG_NEGATIVE
        self._load_program([
            0x08,  # PHP
            0x18,  # CLC
            0xB8,  # CLV
            0x58,  # CLI
            0x28,  # PLP
        ])

        self.assertEqual(self.cpu.step(self.bus), 3)
        self.assertEqual(self.bus.read(0x01FD), FLAG_CARRY | FLAG_NEGATIVE | FLAG_BREAK | 0x20)
        self.assertEqual(self.cpu.stack_pointer, 0xFC)

        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.status & FLAG_CARRY, 0)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, FLAG_NEGATIVE)

        self.assertEqual(self.cpu.step(self.bus), 4)
        self.assertEqual(self.cpu.stack_pointer, 0xFD)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, FLAG_NEGATIVE)
        self.assertEqual(self.cpu.status & FLAG_BREAK, FLAG_BREAK)

    def test_asl_accumulator_updates_result_and_flags(self):
        self._load_program([
            0xA9,
            0x80,  # LDA #$80
            0x0A,  # ASL A -> $00, carry set
            0xA9,
            0x40,  # LDA #$40
            0x0A,  # ASL A -> $80, negative set
        ])

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.step(self.bus), 2)
        self.assertEqual(self.cpu.a, 0x00)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_ZERO, FLAG_ZERO)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.step(self.bus), 2)
        self.assertEqual(self.cpu.a, 0x80)
        self.assertEqual(self.cpu.status & FLAG_CARRY, 0)
        self.assertEqual(self.cpu.status & FLAG_ZERO, 0)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, FLAG_NEGATIVE)

    def test_lsr_accumulator_clears_negative_and_sets_carry(self):
        self._load_program([
            0xA9,
            0x01,  # LDA #$01
            0x4A,  # LSR A -> $00, carry set
            0xA9,
            0x80,  # LDA #$80
            0x4A,  # LSR A -> $40, negative clear
        ])

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.step(self.bus), 2)
        self.assertEqual(self.cpu.a, 0x00)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_ZERO, FLAG_ZERO)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.step(self.bus), 2)
        self.assertEqual(self.cpu.a, 0x40)
        self.assertEqual(self.cpu.status & FLAG_CARRY, 0)
        self.assertEqual(self.cpu.status & FLAG_ZERO, 0)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

    def test_rol_and_ror_accumulator_use_carry_in_and_out(self):
        self._load_program([
            0xA9,
            0x80,  # LDA #$80
            0x38,  # SEC
            0x2A,  # ROL A -> $01, carry set from bit 7
            0x18,  # CLC
            0x6A,  # ROR A -> $00, carry set from bit 0
        ])

        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.step(self.bus), 2)
        self.assertEqual(self.cpu.a, 0x01)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_ZERO, 0)

        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.step(self.bus), 2)
        self.assertEqual(self.cpu.a, 0x00)
        self.assertEqual(self.cpu.status & FLAG_CARRY, FLAG_CARRY)
        self.assertEqual(self.cpu.status & FLAG_ZERO, FLAG_ZERO)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)

    def test_shift_rotate_memory_modes_write_back_and_use_expected_cycles(self):
        self.bus.write(0x0010, 0x81)
        self.bus.write(0x0012, 0x03)
        self.bus.write(0x0022, 0x40)
        self.bus.write(0x1234, 0x80)
        self.bus.write(0x1236, 0x01)
        self.bus.write(0x2000, 0x80)
        self.bus.write(0x2002, 0x02)
        self.bus.write(0x3000, 0x01)
        self.bus.write(0x3002, 0x00)

        self._load_program([
            0xA2,
            0x02,  # LDX #$02
            0x06,
            0x10,  # ASL $10
            0x16,
            0x10,  # ASL $10,X => $12
            0x0E,
            0x34,
            0x12,  # ASL $1234
            0x1E,
            0x34,
            0x12,  # ASL $1234,X => $1236
            0x46,
            0x10,  # LSR $10
            0x56,
            0x20,  # LSR $20,X => $22
            0x4E,
            0x00,
            0x20,  # LSR $2000
            0x5E,
            0x00,
            0x20,  # LSR $2000,X => $2002
            0x26,
            0x10,  # ROL $10
            0x36,
            0x20,  # ROL $20,X => $22
            0x2E,
            0x00,
            0x30,  # ROL $3000
            0x3E,
            0x00,
            0x30,  # ROL $3000,X => $3002
            0x66,
            0x10,  # ROR $10
            0x76,
            0x20,  # ROR $20,X => $22
            0x6E,
            0x00,
            0x30,  # ROR $3000
            0x7E,
            0x00,
            0x30,  # ROR $3000,X => $3002
        ])

        self.assertEqual(self.cpu.step(self.bus), 2)

        self.assertEqual(self.cpu.step(self.bus), 5)
        self.assertEqual(self.bus.read(0x0010), 0x02)
        self.assertEqual(self.cpu.step(self.bus), 6)
        self.assertEqual(self.bus.read(0x0012), 0x06)
        self.assertEqual(self.cpu.step(self.bus), 6)
        self.assertEqual(self.bus.read(0x1234), 0x00)
        self.assertEqual(self.cpu.step(self.bus), 7)
        self.assertEqual(self.bus.read(0x1236), 0x02)

        self.assertEqual(self.cpu.step(self.bus), 5)
        self.assertEqual(self.bus.read(0x0010), 0x01)
        self.assertEqual(self.cpu.step(self.bus), 6)
        self.assertEqual(self.bus.read(0x0022), 0x20)
        self.assertEqual(self.cpu.step(self.bus), 6)
        self.assertEqual(self.bus.read(0x2000), 0x40)
        self.assertEqual(self.cpu.step(self.bus), 7)
        self.assertEqual(self.bus.read(0x2002), 0x01)

        self.assertEqual(self.cpu.step(self.bus), 5)
        self.assertEqual(self.bus.read(0x0010), 0x02)
        self.assertEqual(self.cpu.step(self.bus), 6)
        self.assertEqual(self.bus.read(0x0022), 0x40)
        self.assertEqual(self.cpu.step(self.bus), 6)
        self.assertEqual(self.bus.read(0x3000), 0x02)
        self.assertEqual(self.cpu.step(self.bus), 7)
        self.assertEqual(self.bus.read(0x3002), 0x00)

        self.assertEqual(self.cpu.step(self.bus), 5)
        self.assertEqual(self.bus.read(0x0010), 0x01)
        self.assertEqual(self.cpu.step(self.bus), 6)
        self.assertEqual(self.bus.read(0x0022), 0x20)
        self.assertEqual(self.cpu.step(self.bus), 6)
        self.assertEqual(self.bus.read(0x3000), 0x01)
        self.assertEqual(self.cpu.step(self.bus), 7)
        self.assertEqual(self.bus.read(0x3002), 0x00)
        self.assertEqual(self.cpu.status & FLAG_ZERO, FLAG_ZERO)
        self.assertEqual(self.cpu.status & FLAG_NEGATIVE, 0)


if __name__ == "__main__":
    unittest.main()
