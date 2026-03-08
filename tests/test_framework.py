import unittest

from emulator.bus import MappedMemoryBus, RAM
from emulator.io import BufferedAudioOutput, FrameBufferVideoOutput, KeyboardInputProvider
from emulator.plugin import PluginLoader
from emulator.runtime import EmulatorRuntime


class MemoryBusTests(unittest.TestCase):
    def test_bus_routes_reads_and_writes(self):
        bus = MappedMemoryBus()
        ram = RAM(0x10)
        bus.register(0x1000, 0x100F, ram)

        bus.write(0x1000, 0xAB)
        self.assertEqual(bus.read(0x1000), 0xAB)

    def test_overlapping_mappings_raise(self):
        bus = MappedMemoryBus()
        bus.register(0x0000, 0x000F, RAM(0x10))
        with self.assertRaises(ValueError):
            bus.register(0x000F, 0x001F, RAM(0x11))


class RuntimeIntegrationTests(unittest.TestCase):
    def test_runtime_processes_frame_audio_and_input(self):
        platform = PluginLoader().load("null_platform")
        video = FrameBufferVideoOutput()
        audio = BufferedAudioOutput()
        input_provider = KeyboardInputProvider()
        input_provider.set_key_state("A", True)

        runtime = EmulatorRuntime(platform, video, audio, input_provider)
        runtime.initialize(b"\x00" * 4)
        runtime.run_frame()

        self.assertIsNotNone(video.last_frame)
        self.assertTrue(audio.sample_buffer)
        self.assertTrue(platform.controller.state.get("A"))


if __name__ == "__main__":
    unittest.main()
