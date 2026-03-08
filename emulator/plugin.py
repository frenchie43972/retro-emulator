"""Helpers for discovering and loading platform plugins."""

from __future__ import annotations

import importlib
from pathlib import Path

from .platform import Platform


class PluginLoader:
    """Loads platform factory modules from `/platforms/<name>/plugin.py`."""

    def __init__(self, platforms_root: Path | None = None) -> None:
        self.platforms_root = platforms_root or Path("platforms")

    def available_platforms(self) -> list[str]:
        if not self.platforms_root.exists():
            return []
        names: list[str] = []
        for child in self.platforms_root.iterdir():
            if child.is_dir() and (child / "plugin.py").exists():
                names.append(child.name)
        return sorted(names)

    def load(self, platform_name: str) -> Platform:
        module = importlib.import_module(f"platforms.{platform_name}.plugin")
        factory = module.PlatformPlugin()
        return factory.create()
