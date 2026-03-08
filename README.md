# Retro Emulator Framework

This repository provides a reusable emulator core intended for multiple console platforms.

## Architecture overview

- **`emulator/runtime.py`**: Central runtime loop. Coordinates CPU stepping, graphics frame production, audio sample production, and input propagation.
- **`emulator/interfaces.py`**: Hardware interface contracts for CPU, video, audio, cartridge, controller, memory devices, and host I/O.
- **`emulator/bus.py`**: Memory bus abstraction with address-range registration and built-in RAM/ROM devices.
- **`emulator/io.py`**: Generic host output/input adapters, including keyboard state input.
- **`emulator/plugin.py`**: Platform plugin discovery/loader for modules in `platforms/<platform_name>/plugin.py`.
- **`core/cartridge/`**: Cartridge subsystem with ROM format parsers, metadata modeling, mapper abstractions, and save RAM persistence helpers.
- **`platforms/`**: Per-platform implementation area. Each plugin provides CPU, graphics, audio, memory map, cartridge, and controller bindings.

## Platform plugin layout

Each platform should live under:

```text
platforms/<platform_name>/
  ├── __init__.py
  └── plugin.py
```

`plugin.py` must expose a `PlatformPlugin` class with a `create()` method that returns an `emulator.platform.Platform`.

## Current status

The repository includes a `null_platform` plugin that acts as a non-console reference implementation for testing the framework wiring.


## Cartridge subsystem

- `core/cartridge/loader.py` detects and parses ROM formats. The initial implementation supports NES iNES files.
- `core/cartridge/mappers.py` currently implements NES Mapper 0 (NROM) PRG ROM mapping with optional save RAM at `$6000-$7FFF`.
- Platform plugins choose how cartridges are interpreted. The new `platforms/nes` plugin delegates parsing to `CartridgeLoader` and attaches mapper-provided regions to the shared memory bus.
