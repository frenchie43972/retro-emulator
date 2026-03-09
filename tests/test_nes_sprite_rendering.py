import unittest

from platforms.nes.ppu.nes_ppu import NESPPU


class NESSpriteRenderingTests(unittest.TestCase):
    def _set_solid_tile(self, ppu: NESPPU, tile_index: int, color_bits: int) -> None:
        base = tile_index * 16
        plane0 = 0xFF if (color_bits & 0x01) else 0x00
        plane1 = 0xFF if (color_bits & 0x02) else 0x00
        for row in range(8):
            ppu.memory.write(base + row, plane0)
            ppu.memory.write(base + row + 8, plane1)

    def test_sprites_overlay_background_and_use_sprite_palette(self):
        ppu = NESPPU()
        ppu.registers.ctrl = 0x00
        ppu.registers.mask = 0x18

        # Background tile at (0, 0) uses color index 1.
        ppu.memory.write(0x2000, 0x01)
        self._set_solid_tile(ppu, 0x01, 0x01)

        # Sprite tile #2 uses color bits 2 and sits on top-left.
        self._set_solid_tile(ppu, 0x02, 0x02)
        ppu.sprite_system.oam[0:4] = bytes((0x00, 0x02, 0x00, 0x00))

        # Give different universal background and sprite palette colors.
        ppu.memory.write(0x3F02, 0x01)
        ppu.memory.write(0x3F12, 0x21)

        ppu._render_frame()
        sprite_pixel = ppu._frame.pixels[(1 * 256) * 3 : (1 * 256) * 3 + 3]

        self.assertEqual(sprite_pixel, bytes((76, 154, 236)))

    def test_sprite_zero_color_is_transparent(self):
        ppu = NESPPU()
        ppu.registers.ctrl = 0x00
        ppu.registers.mask = 0x18

        # Background tile at (0, 0) uses color index 1.
        ppu.memory.write(0x2000, 0x01)
        self._set_solid_tile(ppu, 0x01, 0x01)

        # Sprite tile #2 uses color bits 0 (fully transparent).
        self._set_solid_tile(ppu, 0x02, 0x00)
        ppu.sprite_system.oam[0:4] = bytes((0x00, 0x02, 0x00, 0x00))

        ppu.memory.write(0x3F01, 0x18)

        ppu._render_frame()
        sprite_pixel = ppu._frame.pixels[(1 * 256) * 3 : (1 * 256) * 3 + 3]

        self.assertEqual(sprite_pixel, bytes((84, 90, 0)))

    def test_lower_oam_index_sprite_is_drawn_on_top(self):
        ppu = NESPPU()
        ppu.registers.ctrl = 0x00
        ppu.registers.mask = 0x10

        self._set_solid_tile(ppu, 0x01, 0x01)
        self._set_solid_tile(ppu, 0x02, 0x02)

        # Sprite at OAM index 0 should end up on top of OAM index 1.
        ppu.sprite_system.oam[0:4] = bytes((0x00, 0x01, 0x00, 0x00))
        ppu.sprite_system.oam[4:8] = bytes((0x00, 0x02, 0x00, 0x00))

        sprite_frame = ppu.sprite_system.render(
            ppu.memory,
            ctrl=ppu.registers.ctrl,
            mask=ppu.registers.mask,
            width=8,
            height=8,
            background_frame=[[0 for _ in range(8)] for _ in range(8)],
        )

        self.assertEqual(sprite_frame[1][0], 0x11)


if __name__ == "__main__":
    unittest.main()
