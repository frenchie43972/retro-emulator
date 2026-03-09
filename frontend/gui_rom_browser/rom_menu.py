"""Graphical pygame ROM browser and runtime launch flow."""

from __future__ import annotations

from frontend.rom_browser import ROMLauncher, ROMLibraryManager

from .input_handler import MenuInputHandler
from .menu_renderer import MenuRenderer


class GuiRomMenu:
    """Runs the menu loop, launches games, and returns to menu on ESC."""

    def __init__(self, library: ROMLibraryManager, launcher: ROMLauncher) -> None:
        self.library = library
        self.launcher = launcher
        self.renderer = MenuRenderer()
        self.input_handler = MenuInputHandler()
        self.scroll_offset = 0

    def _run_game_session(self, runtime) -> str:
        import pygame

        clock = None
        if hasattr(runtime.video_output, "_pygame"):
            clock = runtime.video_output._pygame.time.Clock()

        running = True
        while running:
            runtime.run_frame()

            # Keep the pygame event queue active every frame so keyboard input
            # remains responsive while a ROM is running.
            pygame.event.pump()

            if pygame.key.get_pressed()[pygame.K_ESCAPE]:
                running = False
                continue

            for event in pygame.event.get([pygame.QUIT]):
                if event.type == pygame.QUIT:
                    runtime.shutdown()
                    return "quit"

            if hasattr(runtime.video_output, "browser_exit_requested") and runtime.video_output.browser_exit_requested():
                runtime.shutdown()
                return "menu"

            if hasattr(runtime.video_output, "exit_requested") and runtime.video_output.exit_requested():
                runtime.shutdown()
                return "quit"

            if clock is not None:
                clock.tick(60)

        runtime.shutdown()
        return "menu"

    def _clamp_selected_index(self) -> None:
        if self.library.roms:
            self.library.selected_index = min(self.library.selected_index, len(self.library.roms) - 1)
            return
        self.library.selected_index = 0

    def _sync_scroll_offset(self) -> None:
        total_roms = len(self.library.roms)
        if total_roms == 0:
            self.scroll_offset = 0
            return

        visible_rows = self.renderer.visible_rows
        max_scroll = max(0, total_roms - visible_rows)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        if self.library.selected_index < self.scroll_offset:
            self.scroll_offset = self.library.selected_index
        elif self.library.selected_index >= self.scroll_offset + visible_rows:
            self.scroll_offset = self.library.selected_index - visible_rows + 1

        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

    def run(self) -> None:
        import pygame

        self.renderer.initialize()
        running = True

        while running:
            self.library.refresh()
            self._clamp_selected_index()
            self._sync_scroll_offset()
            self.renderer.render(self.library, scroll_offset=self.scroll_offset)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                if event.type != pygame.KEYDOWN:
                    continue

                action = self.input_handler.action_for_key(event.key)

                if action.name == "move":
                    self.library.move_selection(action.delta)
                    self._sync_scroll_offset()
                elif action.name == "launch":
                    selected = self.library.selected_rom()
                    if selected is None:
                        continue
                    launch_result = self.launcher.launch(selected)
                    next_state = self._run_game_session(launch_result.runtime)
                    if next_state == "quit":
                        running = False
                        break
                    self.renderer.initialize()
                elif action.name == "refresh":
                    self.library.refresh()
                    self._clamp_selected_index()
                    self._sync_scroll_offset()
                elif action.name == "exit":
                    running = False
                    break

        self.renderer.shutdown()
