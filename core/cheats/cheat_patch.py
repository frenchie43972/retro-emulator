"""Cheat patch representation shared across platforms."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheatPatch:
    """Represents one active/inactive memory patch."""

    id: int
    code: str
    address: int
    value: int
    compare: int | None = None
    enabled: bool = True

    def matches(self, address: int, actual_value: int) -> bool:
        """Return True if this patch should replace a read at the given address."""
        if not self.enabled or self.address != address:
            return False
        if self.compare is None:
            return True
        return self.compare == actual_value
