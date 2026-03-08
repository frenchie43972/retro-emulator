"""Configuration model for the ROM browser frontend."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RomBrowserConfig:
    """Simple ROM browser configuration."""

    rom_directories: list[Path]


def load_rom_browser_config(path: str | Path = "rom_browser_config.json") -> RomBrowserConfig:
    """Load ROM browser config from a JSON file.

    Expected format:
    {
      "rom_directories": ["/path/to/roms", "./roms"]
    }
    """

    config_path = Path(path)
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    rom_dirs = [Path(entry).expanduser() for entry in raw.get("rom_directories", [])]
    return RomBrowserConfig(rom_directories=rom_dirs)
