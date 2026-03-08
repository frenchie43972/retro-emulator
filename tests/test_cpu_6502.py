import unittest

from emulator.bus import MappedMemoryBus, RAM
from platforms.nes.cpu_6502.cpu import (
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


if __name__ == "__main__":
    unittest.main()
