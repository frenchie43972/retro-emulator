"""Background tile renderer for the NES PPU."""

from __future__ import annotations

from .ppu_memory import PPUMemory


class BackgroundRenderer:
    @staticmethod
    def _decode_row(plane0: int, plane1: int) -> list[int]:
        """Decode one 8-pixel tile row from NES bitplanes into palette indexes 0-3."""
        row: list[int] = []
        for pixel in range(8):
            shift = 7 - pixel
            plane0_bit = (plane0 >> shift) & 1
            plane1_bit = (plane1 >> shift) & 1
            row.append(plane0_bit | (plane1_bit << 1))
        return row

    @staticmethod
    def _attribute_shift(tile_x: int, tile_y: int) -> int:
        """Return bit shift for 2x2 tile quadrant inside one attribute byte."""
        quadrant_x = (tile_x % 4) // 2
        quadrant_y = (tile_y % 4) // 2
        return (quadrant_y * 4) + (quadrant_x * 2)

    def render(
        self,
        memory: PPUMemory,
        *,
        ctrl: int,
        mask: int,
        scroll_x: int,
        scroll_y: int,
        width: int,
        height: int,
    ) -> list[list[int]]:
        frame = [[0 for _ in range(width)] for _ in range(height)]
        if (mask & 0x08) == 0:
            return frame

        base_nt = ctrl & 0x03
        pattern_base = 0x1000 if (ctrl & 0x10) else 0x0000

        for y in range(height):
            world_y = (y + scroll_y) % 480
            for x in range(width):
                world_x = (x + scroll_x) % 512
                nt_x = world_x // 256
                nt_y = world_y // 240
                current_nt = (base_nt + nt_x + (nt_y * 2)) % 4

                tile_x = (world_x % 256) // 8
                tile_y = (world_y % 240) // 8
                fine_x = world_x % 8
                fine_y = world_y % 8

                nt_address = 0x2000 + current_nt * 0x400
                tile_index = memory.read(nt_address + tile_y * 32 + tile_x)
                tile_addr = pattern_base + tile_index * 16
                plane0 = memory.read(tile_addr + fine_y)
                plane1 = memory.read(tile_addr + fine_y + 8)
                attribute_addr = nt_address + 0x03C0 + (tile_y // 4) * 8 + (tile_x // 4)
                attribute_byte = memory.read(attribute_addr)
                palette_shift = self._attribute_shift(tile_x, tile_y)
                palette_index = (attribute_byte >> palette_shift) & 0x03

                pixel_value = self._decode_row(plane0, plane1)[fine_x]
                if pixel_value == 0:
                    frame[y][x] = 0
                else:
                    frame[y][x] = pixel_value | (palette_index << 2)
        return frame
