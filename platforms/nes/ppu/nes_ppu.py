"""NES PPU implementation integrated with the emulator video pipeline."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Callable

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
        self.current_scanline = 0
        self.current_cycle = 0
        self._frame_ready = False
        self.ppu_cycles_per_cpu_cycle = 3
        self._debug_frame_completion = os.getenv("NES_PPU_DEBUG", "0") in {"1", "true", "TRUE", "on", "ON"}
        self._frame = FrameBuffer(width=NES_WIDTH, height=NES_HEIGHT, pixels=b"\x00" * (NES_WIDTH * NES_HEIGHT * 3))
        self._frame_sink: Callable[[FrameBuffer], None] | None = None
        self._nmi_callback: Callable[[], None] | None = None
        self._debug_vblank = os.getenv("NES_PPU_DEBUG", "0") in {"1", "true", "TRUE", "on", "ON"}

    def set_cartridge(self, cartridge: LoadedCartridge | None) -> None:
        self.memory.set_cartridge(cartridge)

    def set_frame_sink(self, frame_sink: Callable[[FrameBuffer], None] | None) -> None:
        """Set optional callback invoked whenever a frame finishes rendering."""
        self._frame_sink = frame_sink

    def set_nmi_callback(self, callback: Callable[[], None] | None) -> None:
        """Set callback invoked when PPU requests an NMI on VBlank start."""
        self._nmi_callback = callback

    def reset(self) -> None:
        self.registers.reset()
        self.sprite_system.reset()
        self.current_scanline = 0
        self.current_cycle = 0
        self._frame_ready = False

    def step(self, cycles: int) -> None:
        for _ in range(cycles):
            if self.current_scanline == 241 and self.current_cycle == 1:
                self.registers.set_vblank(True)
                if self._debug_vblank:
                    print("[ppu] vblank started")
                if (self.registers.ctrl & 0x80) and self._nmi_callback is not None:
                    self._nmi_callback()
                    if self._debug_vblank:
                        print("[ppu] nmi triggered")

            if self.current_scanline == 261 and self.current_cycle == 1:
                self.registers.set_vblank(False)

            if self.current_scanline == 261 and self.current_cycle == 340:
                self._complete_frame()

            self.current_cycle += 1
            if self.current_cycle >= 341:
                self.current_cycle = 0
                self.current_scanline += 1
                if self.current_scanline >= 262:
                    self.current_scanline = 0

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


    def serialize_state(self) -> dict:
        return {
            "memory": self.memory.serialize_state(),
            "registers": self.registers.serialize_state(),
            "sprites": self.sprite_system.serialize_state(),
            "scanline": self.current_scanline,
            "cycle": self.current_cycle,
            "frame_ready": self._frame_ready,
        }

    def deserialize_state(self, state: dict) -> None:
        self.memory.deserialize_state(state["memory"])
        self.registers.deserialize_state(state["registers"])
        self.sprite_system.deserialize_state(state["sprites"])
        self.current_scanline = int(state["scanline"])
        self.current_cycle = int(state["cycle"])
        self._frame_ready = bool(state["frame_ready"])
        self._render_frame()

    def _complete_frame(self) -> None:
        self._render_frame()
        self._frame_ready = True
        if self._debug_frame_completion:
            print("[ppu] frame completed")

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

        pixels = bytearray(NES_WIDTH * NES_HEIGHT * 3)
        cursor = 0
        grayscale = ((0, 0, 0), (85, 85, 85), (170, 170, 170), (255, 255, 255))
        for row in frame_indexes:
            for palette_index in row:
                if 0 <= palette_index <= 3:
                    r, g, b = grayscale[palette_index]
                else:
                    r, g, b = NES_PALETTE[palette_index & 0x3F]
                pixels[cursor : cursor + 3] = bytes((r, g, b))
                cursor += 3

        self._frame = FrameBuffer(width=NES_WIDTH, height=NES_HEIGHT, pixels=bytes(pixels))
        if self._frame_sink is not None:
            self._frame_sink(self._frame)
