import unittest

from emulator.io import BufferedAudioOutput, FrameBufferVideoOutput, KeyboardInputProvider
from emulator.plugin import PluginLoader
from emulator.runtime import EmulatorRuntime


def make_bootable_ines_rom(*, reset_vector: int = 0xC000) -> bytes:
    header = bytearray(b"NES\x1A")
    header.extend([1, 0, 0x00, 0x00])
    header.extend(b"\x00" * 8)

    prg = bytearray([0xEA] * 0x4000)
    prg[reset_vector - 0xC000] = 0xA9  # LDA #imm
    prg[reset_vector - 0xC000 + 1] = 0x42
    prg[0x3FFC] = reset_vector & 0xFF
    prg[0x3FFD] = (reset_vector >> 8) & 0xFF

    return bytes(header) + bytes(prg)


class NESMemoryMapTests(unittest.TestCase):
    def test_internal_ram_is_mirrored(self):
        platform = PluginLoader().load("nes")
        platform.bus.write(0x0002, 0x7B)
        self.assertEqual(platform.bus.read(0x0802), 0x7B)
        self.assertEqual(platform.bus.read(0x1002), 0x7B)
        self.assertEqual(platform.bus.read(0x1802), 0x7B)

    def test_ppu_register_placeholder_is_mirrored(self):
        platform = PluginLoader().load("nes")
        platform.bus.write(0x2000, 0x33)
        self.assertEqual(platform.bus.read(0x2008), 0x33)
        self.assertEqual(platform.bus.read(0x3FF8), 0x33)


class NESBootTests(unittest.TestCase):
    def test_reset_vector_and_prg_execution(self):
        platform = PluginLoader().load("nes")
        runtime = EmulatorRuntime(
            platform,
            FrameBufferVideoOutput(),
            BufferedAudioOutput(),
            KeyboardInputProvider(),
        )

        runtime.initialize(make_bootable_ines_rom(reset_vector=0xC000))

        self.assertEqual(platform.cpu.program_counter, 0xC000)

        platform.cpu.step(platform.bus)
        self.assertEqual(platform.cpu.a, 0x42)


if __name__ == "__main__":
    unittest.main()
