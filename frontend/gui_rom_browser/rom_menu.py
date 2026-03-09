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

    def _run_game_session(self, runtime) -> str:
        clock = None
        if hasattr(runtime.video_output, "_pygame"):
            clock = runtime.video_output._pygame.time.Clock()

        while True:
            runtime.run_frame()

            if hasattr(runtime.video_output, "browser_exit_requested") and runtime.video_output.browser_exit_requested():
                runtime.shutdown()
                return "menu"

            if hasattr(runtime.video_output, "exit_requested") and runtime.video_output.exit_requested():
                runtime.shutdown()
                return "quit"

            if clock is not None:
                clock.tick(60)

    def run(self) -> None:
        import pygame

        self.renderer.initialize()
        running = True

        while running:
            self.library.refresh()
            if self.library.roms:
                self.library.selected_index = min(self.library.selected_index, len(self.library.roms) - 1)
            else:
                self.library.selected_index = 0
            self.renderer.render(self.library)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                if event.type != pygame.KEYDOWN:
                    continue

                action = self.input_handler.action_for_key(event.key)

                if action.name == "move":
                    self.library.move_selection(action.delta)
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
                elif action.name == "exit":
                    running = False
                    break

        self.renderer.shutdown()
