"""Executable entry point for launching the emulator ROM browser.

Startup flow:
1) Initialize the emulator framework components used by the launcher.
2) Initialize the frontend ROM browser state.
3) Load ROM browser configuration and scan ROM directories.
4) Render a terminal ROM browser and allow launch/exit actions.

The main module intentionally stays thin and delegates emulation-heavy work to:
- frontend.rom_browser (config, scanning, library and UI rendering)
- core.cartridge.loader (format validation)
- emulator.runtime via frontend.rom_browser.ROMLauncher (platform init + runtime loop)
"""

from __future__ import annotations

from pathlib import Path

from core.cartridge import CartridgeLoadError, CartridgeLoader
from frontend.rom_browser import (
    ROMBrowserUI,
    ROMLauncher,
    ROMLibraryManager,
    ROMScanner,
    load_rom_browser_config,
)


def _clear_terminal() -> None:
    print("\n" * 3)


def _load_configured_directories() -> list[Path]:
    try:
        config = load_rom_browser_config()
    except FileNotFoundError:
        print("[error] Missing config file: rom_browser_config.json")
        return []
    except Exception as exc:
        print(f"[error] Could not load configuration: {exc}")
        return []
    return list(config.rom_directories)


def _run_game_session(runtime) -> str:
    """Start the emulator loop for a launched title.

    Controls:
    - Enter: step one frame
    - b: exit game and return to ROM browser
    - q: exit emulator completely
    """

    print("\nGame session started. Press Enter to step a frame, 'b' for browser, 'q' to quit.")
    while True:
        command = input("game> ").strip().lower()

        if command == "q":
            runtime.shutdown()
            return "quit"
        if command == "b":
            runtime.shutdown()
            return "browser"

        runtime.run_frame()
        if hasattr(runtime.video_output, "exit_requested") and runtime.video_output.exit_requested():
            runtime.shutdown()
            return "quit"
        print("[runtime] Frame executed.")


def _launch_selected_rom(library: ROMLibraryManager, launcher: ROMLauncher) -> str:
    selected = library.selected_rom()
    if selected is None:
        print("[info] No ROM selected.")
        return "browser"

    print(f"[startup] Loading ROM: {selected.file_name}")

    # Validate the ROM format through the cartridge loader before launch.
    # This keeps unsupported format errors explicit and user-friendly.
    try:
        cartridge = CartridgeLoader().load_file(selected.file_path)
    except CartridgeLoadError as exc:
        print(f"[error] Unsupported ROM format: {exc}")
        return "browser"

    detected_platform = "nes" if cartridge.metadata.format_name.lower() == "ines" else "unknown"
    if detected_platform == "unknown":
        print("[error] Unsupported ROM format: no platform mapping for this cartridge.")
        return "browser"

    print(f"[startup] Detected platform: {detected_platform}")

    try:
        print(f"[startup] Initializing platform module: {detected_platform}")
        launch_result = launcher.launch(selected)
    except (ImportError, ModuleNotFoundError, AttributeError) as exc:
        print(f"[error] Platform initialization failed: {exc}")
        return "browser"
    except CartridgeLoadError as exc:
        print(f"[error] Unsupported ROM format: {exc}")
        return "browser"
    except Exception as exc:
        print(f"[error] Failed to start emulator runtime: {exc}")
        return "browser"

    print(f"[startup] Emulator loop started for platform: {launch_result.platform_name}")
    return _run_game_session(launch_result.runtime)


def main() -> None:
    """Initialize core systems, start ROM browser, and handle launch/exit flow."""

    print("[startup] Initializing emulator core systems...")
    scanner = ROMScanner()
    launcher = ROMLauncher()

    print("[startup] Initializing frontend ROM browser...")
    rom_directories = _load_configured_directories()
    if not rom_directories:
        print("[error] Missing ROM directory. Set 'rom_directories' in rom_browser_config.json.")
        return

    missing = [str(path) for path in rom_directories if not path.exists() or not path.is_dir()]
    if missing:
        print("[error] Missing ROM directory:")
        for path in missing:
            print(f"  - {path}")
        return

    library = ROMLibraryManager(scanner=scanner, directories=rom_directories)
    library.refresh()
    ui = ROMBrowserUI(library=library, launcher=launcher)

    while True:
        _clear_terminal()
        print("=== Retro Emulator ROM Browser ===")
        print(ui.render_list())
        print("\nCommands: [w] up  [s] down  [l] launch  [r] rescan  [q] quit")

        command = input("browser> ").strip().lower()
        if command == "w":
            ui.handle_key(ROMBrowserUI.KEY_UP)
        elif command == "s":
            ui.handle_key(ROMBrowserUI.KEY_DOWN)
        elif command == "r":
            library.refresh()
            print("[info] ROM library refreshed.")
        elif command == "l":
            ui.in_game = True
            next_state = _launch_selected_rom(library, launcher)
            ui.in_game = False
            if next_state == "quit":
                print("[shutdown] Emulator exited.")
                return
        elif command == "q":
            print("[shutdown] Emulator exited.")
            return
        else:
            print("[info] Unknown command.")


if __name__ == "__main__":
    main()
