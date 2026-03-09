"""Executable entry point for launching the emulator GUI ROM browser."""

from __future__ import annotations

from pathlib import Path

from frontend.gui_rom_browser import GuiRomMenu
from frontend.rom_browser import ROMLauncher, ROMLibraryManager, ROMScanner, load_rom_browser_config


def _load_config() -> tuple[list[Path], bool]:
    try:
        config = load_rom_browser_config()
    except FileNotFoundError:
        print("[error] Missing config file: rom_browser_config.json")
        return [], True
    except Exception as exc:
        print(f"[error] Could not load configuration: {exc}")
        return [], True
    return list(config.rom_directories), config.recursive_scan


def main() -> None:
    """Initialize systems, open graphical ROM browser, and run until user exits."""

    scanner = ROMScanner()
    launcher = ROMLauncher()

    rom_directories, recursive_scan = _load_config()
    if not rom_directories:
        print("[error] Missing ROM directory. Set 'rom_directories' in rom_browser_config.json.")
        return

    missing = [str(path) for path in rom_directories if not path.exists() or not path.is_dir()]
    if missing:
        print("[error] Missing ROM directory:")
        for path in missing:
            print(f"  - {path}")
        return

    library = ROMLibraryManager(scanner=scanner, directories=rom_directories, recursive_scan=recursive_scan)
    library.refresh()

    menu = GuiRomMenu(library=library, launcher=launcher)
    menu.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        import pygame

        print("[shutdown] Emulator interrupted by user.")
        pygame.quit()
