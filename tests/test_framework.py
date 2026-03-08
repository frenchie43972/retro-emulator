import tempfile
import unittest
from pathlib import Path

from core.cartridge import CartridgeLoadError, CartridgeLoader
from emulator.bus import MappedMemoryBus, RAM
from emulator.io import BufferedAudioOutput, FrameBufferVideoOutput, KeyboardInputProvider
from emulator.plugin import PluginLoader
from emulator.runtime import EmulatorRuntime


def make_ines_rom(
    *,
    prg_banks: int = 1,
    chr_banks: int = 1,
    mapper: int = 0,
    flags6: int = 0,
) -> bytes:
    header = bytearray(b"NES\x1A")
    header.extend([prg_banks, chr_banks, (flags6 & 0x0F) | ((mapper & 0x0F) << 4), mapper & 0xF0])
    header.extend(b"\x00" * 8)
    prg = bytes((idx % 256 for idx in range(prg_banks * 0x4000)))
    chr_data = bytes((255 - (idx % 256) for idx in range(chr_banks * 0x2000)))
    return bytes(header) + prg + chr_data


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


class CartridgeLoaderTests(unittest.TestCase):
    def test_loads_ines_header_and_mapper0(self):
        loader = CartridgeLoader()
        cartridge = loader.load_bytes(make_ines_rom(prg_banks=1, chr_banks=1))

        self.assertEqual(cartridge.metadata.format_name, "iNES")
        self.assertEqual(cartridge.metadata.prg_rom_size, 0x4000)
        self.assertEqual(cartridge.metadata.chr_rom_size, 0x2000)
        self.assertEqual(cartridge.metadata.mapper, 0)

    def test_rejects_unsupported_mapper(self):
        loader = CartridgeLoader()
        with self.assertRaises(CartridgeLoadError):
            loader.load_bytes(make_ines_rom(mapper=2))

    def test_mapper0_bus_mapping_and_save_ram(self):
        loader = CartridgeLoader()
        cart = loader.load_bytes(make_ines_rom(prg_banks=1, chr_banks=0, flags6=0x02))
        bus = MappedMemoryBus()
        bus.register(0x0000, 0x5FFF, RAM(0x6000))
        cart.attach_to_bus(bus)

        self.assertEqual(bus.read(0x8000), 0x00)
        self.assertEqual(bus.read(0xC000), 0x00)  # 16KB PRG mirrored into upper bank

        bus.write(0x6000, 0x5A)
        self.assertEqual(bus.read(0x6000), 0x5A)

        with tempfile.TemporaryDirectory() as td:
            save_path = Path(td) / "save.sav"
            cart.save_ram(save_path)
            bus.write(0x6000, 0x00)
            cart.load_ram(save_path)
            self.assertEqual(bus.read(0x6000), 0x5A)


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

    def test_nes_plugin_available_and_rom_mapped(self):
        platform = PluginLoader().load("nes")
        runtime = EmulatorRuntime(
            platform,
            FrameBufferVideoOutput(),
            BufferedAudioOutput(),
            KeyboardInputProvider(),
        )
        runtime.initialize(make_ines_rom(prg_banks=1, chr_banks=0))
        self.assertEqual(platform.bus.read(0x8000), 0x00)


if __name__ == "__main__":
    unittest.main()
