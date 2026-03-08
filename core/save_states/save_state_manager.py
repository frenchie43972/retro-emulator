"""Save state manager for runtime-integrated platform snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .state_loader import load_state_file
from .state_serializer import serialize_state_document


class SaveStateManager:
    """Coordinates save/load operations and slot file management."""

    FORMAT_VERSION = 1

    def __init__(self, *, platform: Any, rom_key: str, save_root: Path | None = None) -> None:
        self.platform = platform
        self.rom_key = rom_key
        self.save_root = save_root or Path("saves")

    def save_state(self, slot_number: int) -> Path:
        state = self.platform.capture_state()
        payload = {
            "platform": self.platform.name,
            "version": self.FORMAT_VERSION,
            "components": state,
        }
        path = self._slot_path(slot_number)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(serialize_state_document(payload))
        return path

    def load_state(self, slot_number: int) -> Path:
        path = self._slot_path(slot_number)
        document = load_state_file(
            path,
            expected_platform=self.platform.name,
            expected_version=self.FORMAT_VERSION,
        )
        self.platform.restore_state(document["components"])
        return path

    def _slot_path(self, slot_number: int) -> Path:
        if slot_number < 0:
            raise ValueError("slot_number must be >= 0")
        return self.save_root / self.rom_key / f"slot_{slot_number}.state"
