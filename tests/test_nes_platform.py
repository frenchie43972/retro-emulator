import unittest

from emulator.io import BufferedAudioOutput, FrameBufferVideoOutput, KeyboardInputProvider
from emulator.plugin import PluginLoader
from emulator.runtime import EmulatorRuntime
from platforms.nes.ppu.nes_ppu import NESPPU


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


def make_ppu_test_rom(*, reset_vector: int = 0xC000) -> bytes:
    header = bytearray(b"NES\x1A")
    header.extend([1, 1, 0x00, 0x00])
    header.extend(b"\x00" * 8)

    # Program: configure PPU, write background palette and top-left tile, loop forever.
    program = [
        0xA9,
        0x00,
        0x8D,
        0x00,
        0x20,
        0xA9,
        0x0A,
        0x8D,
        0x01,
        0x20,
        0xA9,
        0x3F,
        0x8D,
        0x06,
        0x20,
        0xA9,
        0x00,
        0x8D,
        0x06,
        0x20,
        0xA9,
        0x0F,
        0x8D,
        0x07,
        0x20,
        0xA9,
        0x30,
        0x8D,
        0x07,
        0x20,
        0xA9,
        0x20,
        0x8D,
        0x06,
        0x20,
        0xA9,
        0x00,
        0x8D,
        0x06,
        0x20,
        0xA9,
        0x01,
        0x8D,
        0x07,
        0x20,
        0x4C,
        0x2D,
        0xC0,
    ]

    prg = bytearray([0xEA] * 0x4000)
    start = reset_vector - 0xC000
    prg[start : start + len(program)] = bytes(program)
    prg[0x3FFC] = reset_vector & 0xFF
    prg[0x3FFD] = (reset_vector >> 8) & 0xFF

    chr_rom = bytearray([0x00] * 0x2000)
    tile = 0x10
    for row in range(8):
        chr_rom[tile + row] = 0xFF
        chr_rom[tile + row + 8] = 0x00

    return bytes(header) + bytes(prg) + bytes(chr_rom)


class NESMemoryMapTests(unittest.TestCase):
    def test_internal_ram_is_mirrored(self):
        platform = PluginLoader().load("nes")
        platform.bus.write(0x0002, 0x7B)
        self.assertEqual(platform.bus.read(0x0802), 0x7B)
        self.assertEqual(platform.bus.read(0x1002), 0x7B)
        self.assertEqual(platform.bus.read(0x1802), 0x7B)

    def test_ppu_registers_are_accessible_through_mirrors(self):
        platform = PluginLoader().load("nes")
        platform.bus.write(0x2006, 0x20)
        platform.bus.write(0x2006, 0x00)
        platform.bus.write(0x2007, 0x33)

        platform.bus.write(0x3FFE, 0x20)
        platform.bus.write(0x3FFE, 0x00)
        _ = platform.bus.read(0x3FFF)
        self.assertEqual(platform.bus.read(0x3FFF), 0x33)

    def test_ppudata_write_uses_current_vram_address(self):
        platform = PluginLoader().load("nes")

        platform.bus.write(0x2006, 0x21)
        platform.bus.write(0x2006, 0x10)
        platform.bus.write(0x2007, 0xAB)

        platform.bus.write(0x2006, 0x21)
        platform.bus.write(0x2006, 0x10)
        _ = platform.bus.read(0x2007)
        self.assertEqual(platform.bus.read(0x2007), 0xAB)

    def test_ppudata_write_increments_vram_address_by_one_by_default(self):
        platform = PluginLoader().load("nes")

        platform.bus.write(0x2006, 0x20)
        platform.bus.write(0x2006, 0x00)
        platform.bus.write(0x2007, 0x12)
        platform.bus.write(0x2007, 0x34)

        platform.bus.write(0x2006, 0x20)
        platform.bus.write(0x2006, 0x00)
        _ = platform.bus.read(0x2007)
        self.assertEqual(platform.bus.read(0x2007), 0x12)

        platform.bus.write(0x2006, 0x20)
        platform.bus.write(0x2006, 0x01)
        _ = platform.bus.read(0x2007)
        self.assertEqual(platform.bus.read(0x2007), 0x34)

    def test_ppudata_write_respects_ctrl_increment_mode(self):
        platform = PluginLoader().load("nes")

        platform.bus.write(0x2000, 0x04)
        platform.bus.write(0x2006, 0x20)
        platform.bus.write(0x2006, 0x00)
        platform.bus.write(0x2007, 0x11)
        platform.bus.write(0x2007, 0x22)

        platform.bus.write(0x2006, 0x20)
        platform.bus.write(0x2006, 0x00)
        _ = platform.bus.read(0x2007)
        self.assertEqual(platform.bus.read(0x2007), 0x11)

        platform.bus.write(0x2006, 0x20)
        platform.bus.write(0x2006, 0x20)
        _ = platform.bus.read(0x2007)
        self.assertEqual(platform.bus.read(0x2007), 0x22)

    def test_ppustatus_read_resets_ppuaddr_latch(self):
        platform = PluginLoader().load("nes")

        platform.bus.write(0x2006, 0x21)
        _ = platform.bus.read(0x2002)
        platform.bus.write(0x2006, 0x20)
        platform.bus.write(0x2006, 0x00)
        platform.bus.write(0x2007, 0x66)

        platform.bus.write(0x2006, 0x20)
        platform.bus.write(0x2006, 0x00)
        _ = platform.bus.read(0x2007)
        self.assertEqual(platform.bus.read(0x2007), 0x66)


class NESControllerInputTests(unittest.TestCase):
    def test_latched_reads_shift_controller_bits_from_4016(self):
        platform = PluginLoader().load("nes")

        platform.controller.set_button_state("z", True)
        platform.controller.set_button_state("x", False)
        platform.controller.set_button_state("right shift", True)
        platform.controller.set_button_state("enter", False)
        platform.controller.set_button_state("up", True)
        platform.controller.set_button_state("down", False)
        platform.controller.set_button_state("left", True)
        platform.controller.set_button_state("right", False)

        platform.bus.write(0x4016, 0x01)

        reads = [platform.bus.read(0x4016) for _ in range(8)]

        self.assertEqual(reads, [1, 0, 1, 0, 1, 0, 1, 0])
        self.assertEqual(platform.bus.read(0x4016), 1)



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


class NESPPURenderTests(unittest.TestCase):
    def test_test_rom_produces_visible_frame(self):
        platform = PluginLoader().load("nes")
        video_out = FrameBufferVideoOutput()
        runtime = EmulatorRuntime(
            platform,
            video_out,
            BufferedAudioOutput(),
            KeyboardInputProvider(),
        )
        runtime.initialize(make_ppu_test_rom())

        runtime.run_frame()

        self.assertIsNotNone(video_out.last_frame)
        frame = video_out.last_frame
        assert frame is not None
        first = frame.pixels[(4 * frame.width + 4) * 3 : (4 * frame.width + 4) * 3 + 3]
        later = frame.pixels[(20 * frame.width + 20) * 3 : (20 * frame.width + 20) * 3 + 3]
        self.assertNotEqual(first, later)


def make_apu_sound_test_rom(*, reset_vector: int = 0xC000) -> bytes:
    header = bytearray(b"NES\x1A")
    header.extend([1, 0, 0x00, 0x00])
    header.extend(b"\x00" * 8)

    # Program: enable pulse 1 and noise, configure tone/noise, then loop.
    program = [
        0xA9,
        0x11,
        0x8D,
        0x15,
        0x40,
        0xA9,
        0xBF,
        0x8D,
        0x00,
        0x40,
        0xA9,
        0xFF,
        0x8D,
        0x02,
        0x40,
        0xA9,
        0x07,
        0x8D,
        0x03,
        0x40,
        0xA9,
        0x0F,
        0x8D,
        0x0C,
        0x40,
        0xA9,
        0x04,
        0x8D,
        0x0E,
        0x40,
        0xA9,
        0x08,
        0x8D,
        0x0F,
        0x40,
        0x4C,
        0x23,
        0xC0,
    ]

    prg = bytearray([0xEA] * 0x4000)
    start = reset_vector - 0xC000
    prg[start : start + len(program)] = bytes(program)
    prg[0x3FFC] = reset_vector & 0xFF
    prg[0x3FFD] = (reset_vector >> 8) & 0xFF

    return bytes(header) + bytes(prg)


class NESPPUTimingTests(unittest.TestCase):
    def test_ppu_completes_frame_at_261_340_boundary(self):
        platform = PluginLoader().load("nes")
        ppu = platform.video

        total_ppu_cycles = 262 * 341
        ppu.step(total_ppu_cycles - 1)

        self.assertFalse(ppu.frame_ready())
        self.assertEqual(ppu.current_scanline, 261)
        self.assertEqual(ppu.current_cycle, 340)

        ppu.step(1)

        self.assertTrue(ppu.frame_ready())
        self.assertEqual(ppu.current_scanline, 0)
        self.assertEqual(ppu.current_cycle, 0)

    def test_ppu_sets_and_clears_vblank_flag_during_frame_timing(self):
        platform = PluginLoader().load("nes")
        ppu = platform.video

        ppu.step((241 * 341) + 2)
        self.assertTrue(ppu.registers.status & 0x80)

        ppu.read(0x2002)
        self.assertFalse(ppu.registers.status & 0x80)

        ppu.step((20 * 341) + 2)
        self.assertFalse(ppu.registers.status & 0x80)

    def test_ppu_triggers_cpu_nmi_when_vblank_starts_and_enabled(self):
        platform = PluginLoader().load("nes")
        ppu = platform.video
        cpu = platform.cpu

        platform.cartridge.load(make_bootable_ines_rom())
        platform.cartridge.attach_to_bus(platform.bus)
        platform.reset()

        cpu.program_counter = 0xC000
        cpu.status = 0
        ppu.write(0x2000, 0x80)

        ppu.step((241 * 341) + 2)

        self.assertEqual(cpu.program_counter, 0xEAEA)
        self.assertEqual(cpu.stack_pointer, 0xFA)
        self.assertEqual(platform.bus.read(0x01FD), 0xC0)
        self.assertEqual(platform.bus.read(0x01FC), 0x00)
        self.assertEqual(platform.bus.read(0x01FB), 0x20)

    def test_runtime_advances_nes_ppu_at_three_to_one_ratio(self):
        platform = PluginLoader().load("nes")
        video_out = FrameBufferVideoOutput()
        runtime = EmulatorRuntime(
            platform,
            video_out,
            BufferedAudioOutput(),
            KeyboardInputProvider(),
        )
        runtime.initialize(make_bootable_ines_rom())

        start_scanline = platform.video.current_scanline
        start_cycle = platform.video.current_cycle

        cycles = platform.cpu.step(platform.bus)
        platform.video.step(cycles * platform.video.ppu_cycles_per_cpu_cycle)

        progressed = (platform.video.current_scanline * 341 + platform.video.current_cycle) - (start_scanline * 341 + start_cycle)
        self.assertEqual(progressed, cycles * 3)



class NESAPUTests(unittest.TestCase):
    def test_apu_register_writes_generate_audio_samples(self):
        platform = PluginLoader().load("nes")
        audio_out = BufferedAudioOutput()
        runtime = EmulatorRuntime(
            platform,
            FrameBufferVideoOutput(),
            audio_out,
            KeyboardInputProvider(),
        )

        runtime.initialize(make_apu_sound_test_rom())
        runtime.run_frame()

        self.assertGreater(len(audio_out.sample_buffer), 0)
        self.assertTrue(any(abs(sample) > 0.01 for sample in audio_out.sample_buffer))

    def test_cpu_writes_to_apu_status_update_channel_enable_flags(self):
        platform = PluginLoader().load("nes")
        platform.bus.write(0x4015, 0x1F)

        self.assertTrue(platform.audio.pulse1.enabled)
        self.assertTrue(platform.audio.pulse2.enabled)
        self.assertTrue(platform.audio.triangle.enabled)
        self.assertTrue(platform.audio.noise.enabled)
        self.assertTrue(platform.audio.dmc.enabled)


class NESPaletteRenderTests(unittest.TestCase):
    def test_render_looks_up_palette_ram_for_background_pixels(self):
        ppu = NESPPU()
        ppu.registers.mask = 0x08

        # Top-left nametable entry points to tile index 1.
        ppu.memory.write(0x2000, 0x01)

        # Tile #1 has pixel value 1 everywhere.
        for row in range(8):
            ppu.memory.write(0x0010 + row, 0xFF)
            ppu.memory.write(0x0010 + row + 8, 0x00)

        # Palette slot 1 maps to hardware color 0x21.
        ppu.memory.write(0x3F01, 0x21)

        ppu._render_frame()

        pixel = ppu.consume_frame().pixels[0:3]
        self.assertEqual(pixel, bytes((76, 154, 236)))


if __name__ == "__main__":
    unittest.main()
