import unittest

from emulator.io import BufferedAudioOutput, FrameBufferVideoOutput, KeyboardInputProvider
from emulator.plugin import PluginLoader
from emulator.runtime import EmulatorRuntime
from platforms.turbografx16.video.huc6270_vdc import HuC6270VDC


def make_vdc_init_rom() -> bytes:
    rom = bytearray([0xEA] * 0x10000)
    program = [
        0xA9, 0xFF,  # LDA #$FF
        0x53, 0x01,  # TAM #$01 (MPR0 = $FF, map IO at $0000)
        0xA9, 0x00,  # LDA #$00
        0x8D, 0x02, 0x00,  # STA $0002 (select REG_CONTROL)
        0xA9, 0x01,  # LDA #$01
        0x8D, 0x00, 0x00,  # STA $0000 (display enable)
        0x4C, 0x0E, 0x80,  # JMP $800E
    ]
    rom[0x8000 : 0x8000 + len(program)] = bytes(program)
    rom[0xFFFC] = 0x00
    rom[0xFFFD] = 0x80
    return bytes(rom)


class HuC6270VDCTests(unittest.TestCase):
    def _write_vdc_register(self, platform, register: int, value: int) -> None:
        platform.cpu.bank_registers.set_register(0, 0xFF)
        platform.cpu.bus.write(0x0002, register & 0x1F)
        platform.cpu.bus.write(0x0000, value & 0xFF)
        platform.cpu.bus.write(0x0001, (value >> 8) & 0xFF)

    def _write_vram(self, platform, address: int, value: int) -> None:
        self._write_vdc_register(platform, HuC6270VDC.REG_VRAM_ADDR, address)
        platform.cpu.bus.write(0x0003, value & 0xFF)

    def test_vdc_generates_framebuffer_and_cpu_writes_control_display(self):
        platform = PluginLoader().load("turbografx16")
        output = FrameBufferVideoOutput()
        runtime = EmulatorRuntime(
            platform,
            output,
            BufferedAudioOutput(),
            KeyboardInputProvider(),
        )
        runtime.initialize(make_vdc_init_rom())

        # Execute setup code from ROM so VDC display gets enabled through CPU writes.
        for _ in range(8):
            platform.cpu.step(platform.bus)

        # Configure renderer base addresses and sequential VRAM writes.
        self._write_vdc_register(platform, HuC6270VDC.REG_VRAM_INC, 1)
        self._write_vdc_register(platform, HuC6270VDC.REG_BG_MAP_BASE, 0x0000)
        self._write_vdc_register(platform, HuC6270VDC.REG_BG_TILE_BASE, 0x0800)
        self._write_vdc_register(platform, HuC6270VDC.REG_SAT_BASE, 0x1000)
        self._write_vdc_register(platform, HuC6270VDC.REG_SPRITE_TILE_BASE, 0x1800)

        # Background tile 0 filled with color index 1.
        for index in range(32):
            self._write_vram(platform, 0x0800 + index, 0x11)

        # Tile map first entry uses tile 0 with palette bank 1.
        self._write_vram(platform, 0x0000, 0x00)
        self._write_vram(platform, 0x0001, 0x10)

        # Sprite tile 0 filled with color index 2.
        for index in range(128):
            self._write_vram(platform, 0x1800 + index, 0x22)

        # Sprite 0 at (20, 20), tile 0, palette bank 2.
        sprite_entry = [20, 20, 0, 0x20]
        for index, value in enumerate(sprite_entry):
            self._write_vram(platform, 0x1000 + index, value)

        runtime.run_frame()

        self.assertIsNotNone(output.last_frame)
        self.assertEqual(output.last_frame.width, 256)
        self.assertEqual(output.last_frame.height, 240)

        pixels = output.last_frame.pixels
        self.assertNotEqual(set(pixels), {0})

        bg_pixel = pixels[(0 * 256 + 0) * 4 : (0 * 256 + 0) * 4 + 3]
        sprite_pixel = pixels[(20 * 256 + 20) * 4 : (20 * 256 + 20) * 4 + 3]
        self.assertNotEqual(bg_pixel, sprite_pixel)


if __name__ == "__main__":
    unittest.main()
