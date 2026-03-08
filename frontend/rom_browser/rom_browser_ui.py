"""Simple ROM browser interaction model and key handling."""

from __future__ import annotations

from dataclasses import dataclass

from .rom_launcher import ROMLauncher
from .rom_library import ROMLibraryManager


@dataclass(frozen=True)
class UIAction:
    action: str
    message: str


class ROMBrowserUI:
    """Keyboard-driven ROM list UI controller."""

    KEY_UP = "UP"
    KEY_DOWN = "DOWN"
    KEY_ENTER = "ENTER"
    KEY_ESCAPE = "ESCAPE"

    def __init__(self, library: ROMLibraryManager, launcher: ROMLauncher) -> None:
        self.library = library
        self.launcher = launcher
        self.in_game = False

    def handle_key(self, key: str):
        if key == self.KEY_UP:
            self.library.move_selection(-1)
            return UIAction("navigate", "selection moved up")
        if key == self.KEY_DOWN:
            self.library.move_selection(1)
            return UIAction("navigate", "selection moved down")
        if key == self.KEY_ENTER:
            selected = self.library.selected_rom()
            if selected is None:
                return UIAction("noop", "no ROM selected")
            self.in_game = True
            launch_result = self.launcher.launch(selected)
            return UIAction("launch", f"launched {selected.file_name} on {launch_result.platform_name}")
        if key == self.KEY_ESCAPE:
            if self.in_game:
                self.in_game = False
                return UIAction("return", "returned to ROM browser")
            return UIAction("exit", "exit emulator")
        return UIAction("noop", "unhandled key")

    def render_list(self) -> str:
        if not self.library.roms:
            return "No ROMs found."

        lines: list[str] = []
        for idx, rom in enumerate(self.library.roms):
            prefix = ">" if idx == self.library.selected_index else " "
            lines.append(
                f"{prefix} {rom.file_name} [{rom.platform}] {rom.rom_size} bytes mapper={rom.mapper}"
            )
        return "\n".join(lines)
