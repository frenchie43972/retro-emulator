"""NES PPU implementation integrated with the emulator video pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from core.cartridge.base import LoadedCartridge
from emulator.interfaces import FrameBuffer, MemoryDevice, VideoProcessor

from .background_renderer import BackgroundRenderer
from .ppu_memory import PPUMemory
from .ppu_registers import PPURegisters
from .sprite_system import SpriteSystem

NES_WIDTH = 256
NES_HEIGHT = 240

NES_PALETTE: tuple[tuple[int, int, int], ...] = (
    (84, 84, 84), (0, 30, 116), (8, 16, 144), (48, 0, 136), (68, 0, 100), (92, 0, 48), (84, 4, 0), (60, 24, 0),
    (32, 42, 0), (8, 58, 0), (0, 64, 0), (0, 60, 0), (0, 50, 60), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (152, 150, 152), (8, 76, 196), (48, 50, 236), (92, 30, 228), (136, 20, 176), (160, 20, 100), (152, 34, 32), (120, 60, 0),
    (84, 90, 0), (40, 114, 0), (8, 124, 0), (0, 118, 40), (0, 102, 120), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (236, 238, 236), (76, 154, 236), (120, 124, 236), (176, 98, 236), (228, 84, 236), (236, 88, 180), (236, 106, 100), (212, 136, 32),
    (160, 170, 0), (116, 196, 0), (76, 208, 32), (56, 204, 108), (56, 180, 204), (60, 60, 60), (0, 0, 0), (0, 0, 0),
    (236, 238, 236), (168, 204, 236), (188, 188, 236), (212, 178, 236), (236, 174, 236), (236, 174, 212), (236, 180, 176), (228, 196, 144),
    (204, 210, 120), (180, 222, 120), (168, 226, 144), (152, 226, 180), (160, 214, 228), (160, 162, 160), (0, 0, 0), (0, 0, 0),
)


@dataclass
class NESPPU(VideoProcessor, MemoryDevice):
    memory: PPUMemory
    registers: PPURegisters
    background_renderer: BackgroundRenderer
    sprite_system: SpriteSystem

    def __init__(self) -> None:
        self.memory = PPUMemory()
        self.registers = PPURegisters()
        self.background_renderer = BackgroundRenderer()
        self.sprite_system = SpriteSystem()
        self._scanline = 0
        self._cycle = 0
        self._frame_ready = False
        self._frame = FrameBuffer(width=NES_WIDTH, height=NES_HEIGHT, pixels=b"\x00" * (NES_WIDTH * NES_HEIGHT * 4))

    def set_cartridge(self, cartridge: LoadedCartridge | None) -> None:
        self.memory.set_cartridge(cartridge)

    def reset(self) -> None:
        self.registers.reset()
        self.sprite_system.reset()
        self._scanline = 0
        self._cycle = 0
        self._frame_ready = False
        self.registers.set_vblank(False)

    def step(self, cycles: int) -> None:
        ppu_cycles = cycles * 3
        for _ in range(ppu_cycles):
            self._cycle += 1
            if self._cycle >= 341:
                self._cycle = 0
                self._scanline += 1

                if self._scanline == 241:
                    self.registers.set_vblank(True)
                    self._render_frame()
                    self._frame_ready = True
                elif self._scanline >= 262:
                    self._scanline = 0
                    self.registers.set_vblank(False)

    def frame_ready(self) -> bool:
        return self._frame_ready

    def consume_frame(self) -> FrameBuffer:
        self._frame_ready = False
        return self._frame

    def read(self, address: int) -> int:
        register = address % 8
        if register == 2:
            value = self.registers.status
            self.registers.set_vblank(False)
            self.registers.reset_latch()
            return value
        if register == 4:
            return self.sprite_system.oam[self.registers.oam_addr]
        if register == 7:
            addr = self.registers.vram_addr
            self.registers.increment()
            if addr >= 0x3F00:
                return self.memory.read(addr)
            value = self.registers._data_buffer
            self.registers._data_buffer = self.memory.read(addr)
            return value
        return 0

    def write(self, address: int, value: int) -> None:
        register = address % 8
        value &= 0xFF
        if register == 0:
            self.registers.ctrl = value
            return
        if register == 1:
            self.registers.mask = value
            return
        if register == 3:
            self.registers.oam_addr = value
            return
        if register == 4:
            self.sprite_system.oam[self.registers.oam_addr] = value
            self.registers.oam_addr = (self.registers.oam_addr + 1) & 0xFF
            return
        if register == 5:
            if not self.registers._write_toggle:
                self.registers.scroll_x = value
            else:
                self.registers.scroll_y = value
            self.registers._write_toggle = not self.registers._write_toggle
            return
        if register == 6:
            if not self.registers._write_toggle:
                self.registers._temp_addr = (value & 0x3F) << 8
            else:
                self.registers._temp_addr = (self.registers._temp_addr & 0x3F00) | value
                self.registers.vram_addr = self.registers._temp_addr
            self.registers._write_toggle = not self.registers._write_toggle
            return
        if register == 7:
            self.memory.write(self.registers.vram_addr, value)
            self.registers.increment()

    def _render_frame(self) -> None:
        frame_indexes = self.background_renderer.render(
            self.memory,
            ctrl=self.registers.ctrl,
            mask=self.registers.mask,
            scroll_x=self.registers.scroll_x,
            scroll_y=self.registers.scroll_y,
            width=NES_WIDTH,
            height=NES_HEIGHT,
        )
        self.sprite_system.render(frame_indexes, self.memory, ctrl=self.registers.ctrl, mask=self.registers.mask)

        pixels = bytearray(NES_WIDTH * NES_HEIGHT * 4)
        cursor = 0
        for row in frame_indexes:
            for palette_index in row:
                r, g, b = NES_PALETTE[palette_index & 0x3F]
                pixels[cursor : cursor + 4] = bytes((r, g, b, 0xFF))
                cursor += 4

        self._frame = FrameBuffer(width=NES_WIDTH, height=NES_HEIGHT, pixels=bytes(pixels))
