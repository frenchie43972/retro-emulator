# Retro Emulator User Manual

## 1) Introduction

Retro Emulator is a classic-console emulator project designed to run vintage games on modern personal computers. It lets you load game ROM files and play them with keyboard controls, plus extra emulator features such as save states and cheats.

In the current version, the ROM workflow is focused on **NES (`.nes`) files** and a ROM browser that scans your game folders.

> **Important:** Only use ROMs you legally own and are allowed to use in your region.

---

## 2) Supported Platform (Current Version)

### Currently supported

- **Nintendo Entertainment System (NES)**

The project is modular, and additional platforms may be added in future releases.

---

## 3) Installation

This project is primarily a Python-based emulator framework. Depending on how your build/package is distributed, you may run it in one of the following ways.

### A. Running with Python

1. Install Python 3.10+.
2. Open a terminal in the project folder.
3. Start the emulator entry script (if provided by your build):

```bash
python main.py
```

If your build uses a different script name, run that script instead.

### B. Running with Node.js (if your distribution includes a JS launcher)

Some distributions may include a JavaScript launcher:

```bash
node main.js
```

If `main.js` is not included, use the Python path above.

### C. Running a compiled executable (if provided)

If your release includes a packaged executable, run it directly:

- **Windows:** double-click `retro-emulator.exe` or run it in Command Prompt/PowerShell.
- **macOS/Linux:** run from terminal (example):

```bash
./retro-emulator
```

If needed on Linux/macOS:

```bash
chmod +x ./retro-emulator
./retro-emulator
```

---

## 4) ROM Setup

To make games appear in the ROM browser:

1. Create a ROM directory (for example, `roms`).
2. Place your NES ROM files (`.nes`) in that folder.
3. Ensure the emulator ROM browser config includes this directory.

Example layout:

```text
/roms/
  Super Mario Bros.nes
  The Legend of Zelda.nes
```

Project default config points to `./roms` (relative to the project root), so this structure usually works immediately.

Tips:

- Only `.nes` files are detected by the scanner.
- Invalid/corrupt ROM files are skipped.

---

## 5) Launching Games

1. Start the emulator.
2. Open the ROM browser (or wait for it to appear on startup, depending on your build).
3. The ROM selection list shows detected files and metadata such as platform and mapper.
4. Use navigation keys to highlight a game.
5. Press **Enter** to launch the selected ROM.

ROM browser navigation behavior:

- **Up / Down:** move selection
- **Enter:** launch selected ROM
- **Escape:**
  - while in-game: return to ROM browser
  - from ROM browser: exit emulator

---

## 6) Default Controls

Default NES keyboard mapping:

- **Z** → A
- **X** → B
- **Enter** → Start
- **Right Shift** → Select
- **Arrow Keys** → Directional pad (Up/Down/Left/Right)

If your front-end supports remapping, you can customize these bindings in its settings.

---

## 7) Save States

Save states let you capture an exact snapshot of the current game and reload it later.

### Create a save state

- Use your front-end save-state action (menu item/hotkey), then choose a slot number.
- The emulator writes a state file for that ROM under a slot path like:

```text
saves/<rom_name>/slot_<number>.state
```

### Load a save state

- Use your front-end load-state action and choose the same slot.
- The emulator restores CPU, memory, graphics, audio, controller, and cartridge state for that game.

### Multiple save slots

- You can keep several independent states for one game using different slot numbers (for example slot 0, slot 1, slot 2, ...).

---

## 8) Cheat Codes

The NES platform supports **Game Genie-style** cheat codes.

### How to use cheats

1. Open your cheat manager UI (or use the integration provided in your launcher).
2. Enter a 6-character or 8-character Game Genie code.
3. Add/enable the cheat.
4. You can disable or remove cheats at any time.

Example code format:

- `PAAAAA` (example 6-character code)

Notes:

- Codes are validated by format/alphabet before use.
- 8-character codes include compare-value behavior.

---

## 9) Troubleshooting

### ROM not appearing in browser

- Confirm file extension is `.nes`.
- Confirm the ROM folder is listed in ROM browser config.
- Confirm the file is readable and not corrupted.
- Restart/refresh the ROM library scan.

### Unsupported mapper errors

Current NES mapper support includes:

- Mapper 0 (NROM)
- Mapper 1 (MMC1)
- Mapper 2 (UxROM)
- Mapper 3 (CNROM)

If a ROM needs another mapper, it will fail to load until support is added.

### No audio or video output

- Verify your build includes active host audio/video output integration.
- Make sure the game has launched (not just selected in browser).
- Test with another known-good ROM.
- Check terminal logs for runtime or plugin errors.

---

## 10) Project Structure (Advanced Users)

For users who want to understand or extend the project:

- **`/core`**: shared emulator subsystems (cartridge loading/mappers, cheats, save states)
- **`/platforms`**: console-specific implementations (currently NES and a null/test platform)
- **`/frontend`**: ROM browser and launch orchestration components
- **`/docs`**: project documentation

The emulator is modular: each platform is added via a plugin-like structure, so additional console support can be integrated without rewriting the full core.

---

## 11) Future Platforms

The architecture is designed for expansion. Future versions may add additional platforms such as:

- Sega Genesis
- Super NES
- TurboGrafx-16

Platform availability depends on future implementation and release priorities.
