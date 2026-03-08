import tempfile
import unittest
from pathlib import Path

from core.save_states.state_loader import SaveStateCompatibilityError
from core.save_states.state_serializer import StateFormatError
from emulator.io import BufferedAudioOutput, FrameBufferVideoOutput, KeyboardInputProvider
from emulator.plugin import PluginLoader
from emulator.runtime import EmulatorRuntime, RuntimeConfig


def make_ines_rom(*, flags6: int = 0x00) -> bytes:
    header = bytearray(b"NES\x1A")
    header.extend([1, 0, flags6, 0x00])
    header.extend(b"\x00" * 8)

    prg = bytearray([0xEA] * 0x4000)
    prg[0x3FFC] = 0x00
    prg[0x3FFD] = 0xC0
    return bytes(header) + bytes(prg)


class SaveStateTests(unittest.TestCase):
    def test_save_and_load_state_restores_cpu_and_memory(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = EmulatorRuntime(
                PluginLoader().load("nes"),
                FrameBufferVideoOutput(),
                BufferedAudioOutput(),
                KeyboardInputProvider(),
                config=RuntimeConfig(saves_root=Path(td)),
            )
            runtime.initialize(make_ines_rom())

            runtime.platform.cpu.a = 0x34
            runtime.platform.cpu.program_counter = 0xC123
            runtime.platform.bus.write(0x0005, 0xAA)
            runtime.platform.ppu.registers.ctrl = 0x80
            runtime.platform.apu.frame_counter_mode = 1
            runtime.platform.controller.set_button_state("z", True)

            runtime.save_state(2)

            runtime.platform.cpu.a = 0x00
            runtime.platform.cpu.program_counter = 0x0000
            runtime.platform.bus.write(0x0005, 0x00)
            runtime.platform.ppu.registers.ctrl = 0x00
            runtime.platform.apu.frame_counter_mode = 0
            runtime.platform.controller.set_button_state("z", False)

            runtime.load_state(2)

            self.assertEqual(runtime.platform.cpu.a, 0x34)
            self.assertEqual(runtime.platform.cpu.program_counter, 0xC123)
            self.assertEqual(runtime.platform.bus.read(0x0005), 0xAA)
            self.assertEqual(runtime.platform.ppu.registers.ctrl, 0x80)
            self.assertEqual(runtime.platform.apu.frame_counter_mode, 1)
            self.assertTrue(runtime.platform.controller._buttons["A"])

    def test_corrupt_or_incompatible_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = EmulatorRuntime(
                PluginLoader().load("nes"),
                FrameBufferVideoOutput(),
                BufferedAudioOutput(),
                KeyboardInputProvider(),
                config=RuntimeConfig(saves_root=Path(td)),
            )
            runtime.initialize(make_ines_rom())
            path = runtime.save_state(0)

            path.write_bytes(b"not-json")
            with self.assertRaises(StateFormatError):
                runtime.load_state(0)

            runtime.save_state(0)
            text = path.read_text(encoding="utf-8").replace('"platform":"nes"', '"platform":"null_platform"')
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(SaveStateCompatibilityError):
                runtime.load_state(0)


class BatteryRAMPersistenceTests(unittest.TestCase):
    def test_battery_ram_persists_across_runtime_sessions(self):
        with tempfile.TemporaryDirectory() as td:
            save_root = Path(td)
            rom = make_ines_rom(flags6=0x02)

            runtime1 = EmulatorRuntime(
                PluginLoader().load("nes"),
                FrameBufferVideoOutput(),
                BufferedAudioOutput(),
                KeyboardInputProvider(),
                config=RuntimeConfig(saves_root=save_root),
            )
            runtime1.initialize(rom)
            runtime1.platform.bus.write(0x6000, 0x77)
            runtime1.shutdown()

            runtime2 = EmulatorRuntime(
                PluginLoader().load("nes"),
                FrameBufferVideoOutput(),
                BufferedAudioOutput(),
                KeyboardInputProvider(),
                config=RuntimeConfig(saves_root=save_root),
            )
            runtime2.initialize(rom)
            self.assertEqual(runtime2.platform.bus.read(0x6000), 0x77)


if __name__ == "__main__":
    unittest.main()
