import unittest

from emulator.io import BufferedAudioOutput, FrameBufferVideoOutput, KeyboardInputProvider
from emulator.plugin import PluginLoader
from emulator.runtime import EmulatorRuntime


def make_hucard_rom(*, reset_vector: int = 0x8000) -> bytes:
    rom = bytearray([0xEA] * 0x10000)

    # Program at logical/physical $8000: LDA #$42
    rom[0x8000] = 0xA9
    rom[0x8001] = 0x42

    rom[0xFFFC] = reset_vector & 0xFF
    rom[0xFFFD] = (reset_vector >> 8) & 0xFF
    return bytes(rom)


def make_sound_test_rom(*, reset_vector: int = 0x8000) -> bytes:
    """Minimal ROM scaffold used to validate PSG register side effects."""
    return make_hucard_rom(reset_vector=reset_vector)


class TurboGrafx16PlatformTests(unittest.TestCase):
    def test_hucard_loads_and_cpu_executes_from_reset_vector(self):
        platform = PluginLoader().load("turbografx16")
        runtime = EmulatorRuntime(
            platform,
            FrameBufferVideoOutput(),
            BufferedAudioOutput(),
            KeyboardInputProvider(),
        )

        rom = make_hucard_rom()
        runtime.initialize(rom)

        self.assertEqual(platform.cartridge.loaded.metadata.prg_rom_size, len(rom))
        self.assertEqual(platform.cpu.program_counter, 0x8000)

        platform.cpu.step(platform.bus)
        self.assertEqual(platform.cpu.a, 0x42)

    def test_ram_window_is_read_write_via_mpr_mapping(self):
        platform = PluginLoader().load("turbografx16")
        platform.cartridge.load(make_hucard_rom())
        platform.reset()

        # Map logical page 0 ($0000-$1FFF) to physical bank $F8 where system RAM starts.
        platform.cpu.bank_registers.set_register(0, 0xF8)
        platform.cpu.bus.write(0x0010, 0x77)

        self.assertEqual(platform.cpu.bus.read(0x0010), 0x77)

    def test_psg_register_writes_generate_audible_output(self):
        platform = PluginLoader().load("turbografx16")
        runtime = EmulatorRuntime(
            platform,
            FrameBufferVideoOutput(),
            BufferedAudioOutput(),
            KeyboardInputProvider(),
        )

        runtime.initialize(make_sound_test_rom())

        # Map logical $E000-$FFFF to physical bank $FF where hardware registers live.
        platform.cpu.bank_registers.set_register(7, 0xFF)

        # Program channel 0 waveform RAM with a ramp and enable playback.
        platform.cpu.bus.write(0xE100, 0x00)  # channel select
        platform.cpu.bus.write(0xE106, 0x00)  # waveform index
        for level in range(32):
            platform.cpu.bus.write(0xE107, level)

        platform.cpu.bus.write(0xE102, 0x80)  # frequency low
        platform.cpu.bus.write(0xE103, 0x01)  # frequency high
        platform.cpu.bus.write(0xE104, 0x1F)  # max volume
        platform.cpu.bus.write(0xE105, 0x01)  # channel enable

        platform.audio.step(10_000)
        samples = platform.audio.pull_samples()

        self.assertGreater(len(samples), 0)
        self.assertTrue(any(abs(sample) > 0.001 for sample in samples))


if __name__ == "__main__":
    unittest.main()
