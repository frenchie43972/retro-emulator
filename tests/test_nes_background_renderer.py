import unittest

from platforms.nes.ppu.background_renderer import BackgroundRenderer
from platforms.nes.ppu.ppu_memory import PPUMemory


class BackgroundRendererTests(unittest.TestCase):
    def test_decode_row_combines_both_bitplanes(self):
        row = BackgroundRenderer._decode_row(0b10101010, 0b01010101)
        self.assertEqual(row, [1, 2, 1, 2, 1, 2, 1, 2])

    def test_render_uses_nametable_tile_index_and_background_pattern_table_select(self):
        memory = PPUMemory()
        renderer = BackgroundRenderer()

        # Top-left nametable entry points at tile index 1.
        memory.write(0x2000, 0x01)

        # Pattern table at $0000 has tile #1 as all color index 1.
        for row in range(8):
            memory.write(0x0010 + row, 0xFF)
            memory.write(0x0010 + row + 8, 0x00)

        # Pattern table at $1000 has tile #1 as all color index 2.
        for row in range(8):
            memory.write(0x1010 + row, 0x00)
            memory.write(0x1010 + row + 8, 0xFF)

        frame_low = renderer.render(
            memory,
            ctrl=0x00,
            mask=0x08,
            scroll_x=0,
            scroll_y=0,
            width=8,
            height=8,
        )
        frame_high = renderer.render(
            memory,
            ctrl=0x10,
            mask=0x08,
            scroll_x=0,
            scroll_y=0,
            width=8,
            height=8,
        )

        self.assertTrue(all(pixel == 1 for row in frame_low for pixel in row))
        self.assertTrue(all(pixel == 2 for row in frame_high for pixel in row))


if __name__ == "__main__":
    unittest.main()
