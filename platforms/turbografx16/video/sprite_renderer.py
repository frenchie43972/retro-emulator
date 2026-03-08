"""Basic TurboGrafx-16 sprite rendering."""

from __future__ import annotations

from .vram import VDCVRAM


class SpriteRenderer:
    """Renders 16x16 sprites from a sprite attribute table."""

    SPRITE_COUNT = 64
    SPRITE_SIZE = 16

    def render(
        self,
        frame_indexes: list[list[int]],
        vram: VDCVRAM,
        *,
        sat_base: int,
        sprite_tile_base: int,
    ) -> None:
        height = len(frame_indexes)
        width = len(frame_indexes[0]) if height else 0

        for sprite_index in range(self.SPRITE_COUNT):
            entry_base = sat_base + (sprite_index * 4)
            y = vram.read(entry_base)
            x = vram.read(entry_base + 1)
            tile = vram.read(entry_base + 2)
            attributes = vram.read(entry_base + 3)
            palette = (attributes >> 4) & 0x0F

            self._draw_sprite(
                frame_indexes,
                vram,
                width,
                height,
                x,
                y,
                tile,
                palette,
                sprite_tile_base,
            )

    def _draw_sprite(
        self,
        frame_indexes: list[list[int]],
        vram: VDCVRAM,
        width: int,
        height: int,
        x: int,
        y: int,
        tile: int,
        palette: int,
        sprite_tile_base: int,
    ) -> None:
        # 16x16 sprite, 4bpp packed nibbles.
        tile_stride = 128
        row_stride = 8

        for row in range(self.SPRITE_SIZE):
            screen_y = y + row
            if not 0 <= screen_y < height:
                continue

            for col in range(self.SPRITE_SIZE):
                screen_x = x + col
                if not 0 <= screen_x < width:
                    continue

                address = sprite_tile_base + (tile * tile_stride) + (row * row_stride) + (col // 2)
                packed = vram.read(address)
                pixel = packed & 0x0F if (col & 1) else (packed >> 4) & 0x0F
                if pixel == 0:
                    continue
                frame_indexes[screen_y][screen_x] = (palette << 4) | pixel
