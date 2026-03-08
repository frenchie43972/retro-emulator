"""CPU-facing PPU register file ($2000-$2007)."""

from __future__ import annotations


class PPURegisters:
    def __init__(self) -> None:
        self.ctrl = 0
        self.mask = 0
        self.status = 0
        self.oam_addr = 0
        self.scroll_x = 0
        self.scroll_y = 0
        self.vram_addr = 0
        self._temp_addr = 0
        self._write_toggle = False
        self._data_buffer = 0

    def reset(self) -> None:
        self.ctrl = 0
        self.mask = 0
        self.status = 0
        self.oam_addr = 0
        self.scroll_x = 0
        self.scroll_y = 0
        self.vram_addr = 0
        self._temp_addr = 0
        self._write_toggle = False
        self._data_buffer = 0

    def increment(self) -> None:
        step = 32 if (self.ctrl & 0x04) else 1
        self.vram_addr = (self.vram_addr + step) & 0x3FFF

    def reset_latch(self) -> None:
        self._write_toggle = False

    def set_vblank(self, active: bool) -> None:
        if active:
            self.status |= 0x80
        else:
            self.status &= ~0x80
