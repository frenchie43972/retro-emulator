"""Load and validate on-disk emulator save states."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .state_serializer import StateFormatError, deserialize_state_document


class SaveStateCompatibilityError(StateFormatError):
    """Raised when a save state cannot be loaded by this emulator build."""


def load_state_file(path: Path, *, expected_platform: str, expected_version: int) -> dict[str, Any]:
    """Read, deserialize, and validate a save-state file."""

    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise StateFormatError(f"Unable to read save state '{path}': {exc}") from exc

    document = deserialize_state_document(payload)

    platform = document.get("platform")
    if platform != expected_platform:
        raise SaveStateCompatibilityError(
            f"Save state platform mismatch: expected '{expected_platform}', got '{platform}'"
        )

    version = document.get("version")
    if version != expected_version:
        raise SaveStateCompatibilityError(
            f"Save state version mismatch: expected {expected_version}, got {version}"
        )

    components = document.get("components")
    if not isinstance(components, dict):
        raise StateFormatError("Save state is missing a 'components' object")

    return document
