"""HuC6270-inspired VDC implementation for baseline TurboGrafx-16 video."""

from __future__ import annotations

from emulator.interfaces import FrameBuffer, MemoryDevice, VideoProcessor

from .background_renderer import BackgroundRenderer
from .sprite_renderer import SpriteRenderer
from .vram import VDCVRAM

TG16_WIDTH = 256
TG16_HEIGHT = 240
CPU_CYCLES_PER_FRAME = 29_780

TG16_PALETTE: tuple[tuple[int, int, int], ...] = tuple(
    (index * 3 % 256, index * 5 % 256, index * 7 % 256) for index in range(256)
)


class HuC6270VDC(VideoProcessor, MemoryDevice):
    """CPU-visible VDC registers and software frame rendering."""

    REG_CONTROL = 0
    REG_VRAM_ADDR = 1
    REG_VRAM_INC = 2
    REG_SCROLL_X = 3
    REG_SCROLL_Y = 4
    REG_BG_MAP_BASE = 5
    REG_BG_TILE_BASE = 6
    REG_SAT_BASE = 7
    REG_SPRITE_TILE_BASE = 8

    def __init__(self) -> None:
        self.vram = VDCVRAM()
        self.background_renderer = BackgroundRenderer()
        self.sprite_renderer = SpriteRenderer()
        self._selected_register = 0
        self._registers = [0] * 32
        self._cycles = 0
        self._frame_ready = False
        self._frame = FrameBuffer(
            width=TG16_WIDTH,
            height=TG16_HEIGHT,
            pixels=b"\x00" * (TG16_WIDTH * TG16_HEIGHT * 4),
        )

    def reset(self) -> None:
        self.vram.reset()
        self._selected_register = 0
        self._registers = [0] * 32
        self._registers[self.REG_VRAM_INC] = 1
        self._cycles = 0
        self._frame_ready = False

    def step(self, cycles: int) -> None:
        self._cycles += cycles
        while self._cycles >= CPU_CYCLES_PER_FRAME:
            self._cycles -= CPU_CYCLES_PER_FRAME
            self._render_frame()
            self._frame_ready = True

    def frame_ready(self) -> bool:
        return self._frame_ready

    def consume_frame(self) -> FrameBuffer:
        self._frame_ready = False
        return self._frame

    def read(self, address: int) -> int:
        port = address & 0x03
        if port == 0:
            return 0x00
        if port == 1:
            return (self._registers[self._selected_register] >> 8) & 0xFF
        if port == 2:
            return self._selected_register & 0x1F

        vram_addr = self._registers[self.REG_VRAM_ADDR] & 0xFFFF
        value = self.vram.read(vram_addr)
        self._increment_vram_address()
        return value

    def write(self, address: int, value: int) -> None:
        value &= 0xFF
        port = address & 0x03

        if port == 0:
            current = self._registers[self._selected_register]
            self._registers[self._selected_register] = (current & 0xFF00) | value
            return
        if port == 1:
            current = self._registers[self._selected_register]
            self._registers[self._selected_register] = (current & 0x00FF) | (value << 8)
            return
        if port == 2:
            self._selected_register = value & 0x1F
            return

        vram_addr = self._registers[self.REG_VRAM_ADDR] & 0xFFFF
        self.vram.write(vram_addr, value)
        self._increment_vram_address()

    def _increment_vram_address(self) -> None:
        increment = self._registers[self.REG_VRAM_INC] & 0xFFFF
        if increment == 0:
            increment = 1
        self._registers[self.REG_VRAM_ADDR] = (self._registers[self.REG_VRAM_ADDR] + increment) & 0xFFFF

    def _render_frame(self) -> None:
        if (self._registers[self.REG_CONTROL] & 0x0001) == 0:
            pixels = b"\x00" * (TG16_WIDTH * TG16_HEIGHT * 4)
            self._frame = FrameBuffer(width=TG16_WIDTH, height=TG16_HEIGHT, pixels=pixels)
            return

        frame_indexes = self.background_renderer.render(
            self.vram,
            width=TG16_WIDTH,
            height=TG16_HEIGHT,
            map_base=self._registers[self.REG_BG_MAP_BASE] & 0xFFFF,
            tile_base=self._registers[self.REG_BG_TILE_BASE] & 0xFFFF,
            scroll_x=self._registers[self.REG_SCROLL_X] & 0x01FF,
            scroll_y=self._registers[self.REG_SCROLL_Y] & 0x01FF,
        )

        self.sprite_renderer.render(
            frame_indexes,
            self.vram,
            sat_base=self._registers[self.REG_SAT_BASE] & 0xFFFF,
            sprite_tile_base=self._registers[self.REG_SPRITE_TILE_BASE] & 0xFFFF,
        )

        pixels = bytearray(TG16_WIDTH * TG16_HEIGHT * 4)
        cursor = 0
        for row in frame_indexes:
            for palette_index in row:
                r, g, b = TG16_PALETTE[palette_index & 0xFF]
                pixels[cursor : cursor + 4] = bytes((r, g, b, 0xFF))
                cursor += 4

        self._frame = FrameBuffer(width=TG16_WIDTH, height=TG16_HEIGHT, pixels=bytes(pixels))
