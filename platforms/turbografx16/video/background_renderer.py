"""Tile-based background renderer for the TurboGrafx-16 VDC."""

from __future__ import annotations

from .vram import VDCVRAM


class BackgroundRenderer:
    """Renders a 32x32 tile map into a frame-sized index buffer."""

    TILE_SIZE = 8
    MAP_WIDTH_TILES = 32
    MAP_HEIGHT_TILES = 32

    def render(
        self,
        vram: VDCVRAM,
        *,
        width: int,
        height: int,
        map_base: int,
        tile_base: int,
        scroll_x: int,
        scroll_y: int,
    ) -> list[list[int]]:
        frame = [[0 for _ in range(width)] for _ in range(height)]

        for y in range(height):
            map_y = (y + scroll_y) % (self.MAP_HEIGHT_TILES * self.TILE_SIZE)
            tile_y = map_y // self.TILE_SIZE
            in_tile_y = map_y % self.TILE_SIZE

            for x in range(width):
                map_x = (x + scroll_x) % (self.MAP_WIDTH_TILES * self.TILE_SIZE)
                tile_x = map_x // self.TILE_SIZE
                in_tile_x = map_x % self.TILE_SIZE

                map_offset = ((tile_y * self.MAP_WIDTH_TILES) + tile_x) * 2
                tile_entry = vram.read_u16(map_base + map_offset)
                tile_index = tile_entry & 0x07FF
                palette = (tile_entry >> 12) & 0x0F

                pixel = self._tile_pixel(vram, tile_base, tile_index, in_tile_x, in_tile_y)
                frame[y][x] = (palette << 4) | pixel

        return frame

    def _tile_pixel(self, vram: VDCVRAM, tile_base: int, tile_index: int, x: int, y: int) -> int:
        # 8x8, 4bpp packed as one nibble per pixel.
        tile_stride = 32
        row_stride = 4
        address = tile_base + (tile_index * tile_stride) + (y * row_stride) + (x // 2)
        value = vram.read(address)
        if x & 1:
            return value & 0x0F
        return (value >> 4) & 0x0F
