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
        self.fine_x = 0
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
        self.fine_x = 0
        self._write_toggle = False
        self._data_buffer = 0

    def increment(self) -> None:
        step = 32 if (self.ctrl & 0x04) else 1
        self.vram_addr = (self.vram_addr + step) & 0x3FFF

    def write_ppuaddr(self, value: int) -> None:
        """Handle the two-write PPUADDR latch behavior."""
        value &= 0xFF
        if not self._write_toggle:
            self._temp_addr = (value & 0x3F) << 8
            self._write_toggle = True
            return

        self._temp_addr = (self._temp_addr & 0x3F00) | value
        self.vram_addr = self._temp_addr & 0x3FFF
        self._write_toggle = False

    def write_ppuctrl(self, value: int) -> None:
        self.ctrl = value & 0xFF
        self._temp_addr = (self._temp_addr & 0x73FF) | ((self.ctrl & 0x03) << 10)

    def write_ppuscroll(self, value: int) -> None:
        value &= 0xFF
        if not self._write_toggle:
            self.fine_x = value & 0x07
            coarse_x = (value >> 3) & 0x1F
            self._temp_addr = (self._temp_addr & 0x7FE0) | coarse_x
            self.scroll_x = value
            self._write_toggle = True
            return

        coarse_y = (value >> 3) & 0x1F
        fine_y = value & 0x07
        self._temp_addr = (self._temp_addr & 0x0C1F) | (coarse_y << 5) | (fine_y << 12)
        self.scroll_y = value
        self._write_toggle = False

    def reset_latch(self) -> None:
        self._write_toggle = False

    def set_vblank(self, active: bool) -> None:
        if active:
            self.status |= 0x80
        else:
            self.status &= ~0x80


    def serialize_state(self) -> dict:
        return {
            "ctrl": self.ctrl,
            "mask": self.mask,
            "status": self.status,
            "oam_addr": self.oam_addr,
            "scroll_x": self.scroll_x,
            "scroll_y": self.scroll_y,
            "vram_addr": self.vram_addr,
            "temp_addr": self._temp_addr,
            "fine_x": self.fine_x,
            "write_toggle": self._write_toggle,
            "data_buffer": self._data_buffer,
        }

    def deserialize_state(self, state: dict) -> None:
        self.ctrl = int(state["ctrl"])
        self.mask = int(state["mask"])
        self.status = int(state["status"])
        self.oam_addr = int(state["oam_addr"])
        self.scroll_x = int(state["scroll_x"])
        self.scroll_y = int(state["scroll_y"])
        self.vram_addr = int(state["vram_addr"])
        self._temp_addr = int(state["temp_addr"])
        self.fine_x = int(state.get("fine_x", 0))
        self._write_toggle = bool(state["write_toggle"])
        self._data_buffer = int(state["data_buffer"])
