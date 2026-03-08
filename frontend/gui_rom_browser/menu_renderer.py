"""Pygame text renderer for the graphical ROM menu."""

from __future__ import annotations

from frontend.rom_browser.rom_library import ROMLibraryManager


class MenuRenderer:
    """Draw the ROM list and current selection inside a pygame window."""

    BG_COLOR = (18, 18, 24)
    TITLE_COLOR = (240, 240, 255)
    ITEM_COLOR = (190, 190, 210)
    SELECTED_COLOR = (255, 230, 120)
    HELP_COLOR = (140, 140, 160)

    def __init__(self, *, width: int = 768, height: int = 576, title: str = "Retro Emulator") -> None:
        self.width = width
        self.height = height
        self.title = title
        self._pygame = None
        self._window = None
        self._title_font = None
        self._item_font = None

    def initialize(self) -> None:
        import pygame

        self._pygame = pygame
        if not pygame.get_init():
            pygame.init()
        pygame.display.set_caption(self.title)
        self._window = pygame.display.set_mode((self.width, self.height))
        self._title_font = pygame.font.SysFont("consolas", 48)
        self._item_font = pygame.font.SysFont("consolas", 30)

    def render(self, library: ROMLibraryManager) -> None:
        if self._window is None:
            self.initialize()

        self._window.fill(self.BG_COLOR)

        title_surface = self._title_font.render(self.title, True, self.TITLE_COLOR)
        self._window.blit(title_surface, (32, 24))

        if not library.roms:
            no_roms = self._item_font.render("No .nes ROMs found in configured roms/ directory.", True, self.ITEM_COLOR)
            self._window.blit(no_roms, (32, 120))
        else:
            y = 120
            for idx, rom in enumerate(library.roms):
                selected = idx == library.selected_index
                marker = "> " if selected else "  "
                color = self.SELECTED_COLOR if selected else self.ITEM_COLOR
                label = self._item_font.render(f"{marker}{rom.file_name}", True, color)
                self._window.blit(label, (48, y))
                y += 36

        help_text = "UP/DOWN: Select   ENTER: Launch   ESC: Exit"
        help_surface = self._item_font.render(help_text, True, self.HELP_COLOR)
        self._window.blit(help_surface, (32, self.height - 56))

        self._pygame.display.flip()

    def shutdown(self) -> None:
        if self._pygame is not None and self._pygame.get_init():
            self._pygame.quit()
        self._window = None
