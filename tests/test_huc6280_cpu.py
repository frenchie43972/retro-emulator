import unittest

from emulator.bus import MappedMemoryBus, RAM
from platforms.nes.cpu_6502.cpu import FLAG_ZERO
from platforms.turbografx16.cpu_huc6280 import HuC6280CPU


class HuC6280CPUTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = MappedMemoryBus()
        # 2MB physical space (256 banks x 8KB)
        self.ram = RAM(0x200000)
        self.bus.register(0x000000, 0x1FFFFF, self.ram)

        # Reset vector in bank 7 maps to logical 0xE000-0xFFFF by default.
        self.bus.write(0x00FFFC, 0x00)
        self.bus.write(0x00FFFD, 0x80)

        self.cpu = HuC6280CPU(self.bus)
        self.cpu.reset()

    def _load_program(self, program: list[int], start: int = 0x8000) -> None:
        for idx, byte in enumerate(program):
            self.cpu.bus.write(start + idx, byte)
        self.cpu.program_counter = start

    def test_reset_initializes_registers_and_cycles(self):
        self.assertEqual(self.cpu.program_counter, 0x8000)
        self.assertEqual(self.cpu.a, 0)
        self.assertEqual(self.cpu.x, 0)
        self.assertEqual(self.cpu.y, 0)
        self.assertEqual(self.cpu.stack_pointer, 0xFD)
        self.assertEqual(self.cpu.cycles, 7)

    def test_6502_instruction_execution_works_with_huc6280_core(self):
        self._load_program([
            0xA9,
            0x42,  # LDA #$42
            0xA2,
            0x10,  # LDX #$10
            0x95,
            0x20,  # STA $20,X
        ])

        self.assertEqual(self.cpu.step(self.bus), 2)
        self.assertEqual(self.cpu.a, 0x42)
        self.assertEqual(self.cpu.step(self.bus), 2)
        self.assertEqual(self.cpu.x, 0x10)
        self.assertEqual(self.cpu.step(self.bus), 4)
        self.assertEqual(self.cpu.bus.read(0x0030), 0x42)

    def test_tam_tma_update_bank_registers_and_accumulator(self):
        self._load_program([
            0xA9,
            0x0A,  # LDA #$0A
            0x53,
            0x02,  # TAM #%00000010 (set MPR1)
            0xA9,
            0x00,  # clear A
            0x43,
            0x02,  # TMA #%00000010 (read MPR1)
        ])

        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.bank_registers.get_register(1), 0x0A)

        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.assertEqual(self.cpu.a, 0x0A)
        self.assertFalse(self.cpu.status & FLAG_ZERO)

    def test_bank_mapping_changes_logical_to_physical_access(self):
        self.bus.write(0x092345, 0x99)
        self.cpu.bank_registers.set_register(1, 0x49)

        self.assertEqual(self.cpu.bus.read(0x2345), 0x99)

    def test_block_transfer_tii_copies_memory(self):
        self.cpu.bus.write(0x3000, 0x11)
        self.cpu.bus.write(0x3001, 0x22)
        self.cpu.bus.write(0x3002, 0x33)

        self._load_program([
            0x73,        # TII
            0x00,
            0x30,        # source = $3000
            0x00,
            0x40,        # destination = $4000
            0x03,
            0x00,        # length = 3
        ])

        cycles = self.cpu.step(self.bus)
        self.assertEqual(cycles, 35)
        self.assertEqual(self.cpu.bus.read(0x4000), 0x11)
        self.assertEqual(self.cpu.bus.read(0x4001), 0x22)
        self.assertEqual(self.cpu.bus.read(0x4002), 0x33)

    def test_timer_control_instruction_writes_ports(self):
        self._load_program([
            0x03,
            0xAA,  # ST0 #$AA
            0x13,
            0xBB,  # ST1 #$BB
            0x23,
            0xCC,  # ST2 #$CC
        ])

        self.cpu.step(self.bus)
        self.cpu.step(self.bus)
        self.cpu.step(self.bus)

        self.assertEqual(self.cpu.bus.read(0x1FF0), 0xAA)
        self.assertEqual(self.cpu.bus.read(0x1FF1), 0xBB)
        self.assertEqual(self.cpu.bus.read(0x1FF2), 0xCC)


if __name__ == "__main__":
    unittest.main()
