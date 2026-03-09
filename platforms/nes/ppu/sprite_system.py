"""Basic OAM and sprite rendering support."""

from __future__ import annotations

from .ppu_memory import PPUMemory


class SpriteSystem:
    def __init__(self) -> None:
        self.oam = bytearray(256)

    def reset(self) -> None:
        self.oam[:] = b"\x00" * 256

    def render(
        self,
        frame: list[list[int]],
        memory: PPUMemory,
        *,
        ctrl: int,
        mask: int,
    ) -> None:
        if (mask & 0x10) == 0:
            return

        sprite_height = 16 if (ctrl & 0x20) else 8
        pattern_base = 0x1000 if (ctrl & 0x08) else 0x0000

        # Draw sprites in reverse OAM order so lower indexed sprites end up on top.
        for sprite in range(63, -1, -1):
            base = sprite * 4
            sprite_y = self.oam[base] + 1
            tile_index = self.oam[base + 1]
            attrs = self.oam[base + 2]
            sprite_x = self.oam[base + 3]

            if sprite_height != 8:
                continue

            palette_select = attrs & 0x03
            flip_horizontal = bool(attrs & 0x40)
            flip_vertical = bool(attrs & 0x80)
            behind_bg = bool(attrs & 0x20)

            for row in range(8):
                y = sprite_y + row
                if not (0 <= y < len(frame)):
                    continue

                tile_row = 7 - row if flip_vertical else row
                tile_addr = pattern_base + tile_index * 16
                plane0 = memory.read(tile_addr + tile_row)
                plane1 = memory.read(tile_addr + tile_row + 8)

                for col in range(8):
                    x = sprite_x + col
                    if not (0 <= x < len(frame[0])):
                        continue

                    bit = col if flip_horizontal else (7 - col)
                    color_bits = ((plane1 >> bit) & 1) << 1 | ((plane0 >> bit) & 1)
                    if color_bits == 0:
                        continue
                    if behind_bg and frame[y][x] != 0:
                        continue

                    # Keep framebuffer entries as palette indexes (0x10-0x1F for sprites),
                    # matching background rendering which also stores palette indexes.
                    frame[y][x] = 0x10 + palette_select * 4 + color_bits


    def serialize_state(self) -> dict:
        return {"oam": bytes(self.oam)}

    def deserialize_state(self, state: dict) -> None:
        oam = state["oam"]
        if len(oam) != len(self.oam):
            raise ValueError("PPU OAM size mismatch in save state")
        self.oam[:] = oam
