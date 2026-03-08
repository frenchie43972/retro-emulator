"""Cheat registry and memory read patching."""

from __future__ import annotations

from collections import defaultdict

from .cheat_decoder import CheatDecodeError, decode_game_genie
from .cheat_patch import CheatPatch


class CheatManager:
    """Stores and applies decoded cheats for one loaded game/session."""

    def __init__(self) -> None:
        self._next_id = 1
        self._cheats: dict[int, CheatPatch] = {}
        self._by_address: dict[int, list[int]] = defaultdict(list)

    def clear(self) -> None:
        self._next_id = 1
        self._cheats.clear()
        self._by_address.clear()

    def add_cheat(self, code: str) -> CheatPatch:
        decoded = decode_game_genie(code)
        cheat_id = self._next_id
        self._next_id += 1

        cheat = CheatPatch(
            id=cheat_id,
            code=code.strip().upper(),
            address=decoded.address,
            value=decoded.value,
            compare=decoded.compare,
            enabled=True,
        )
        self._cheats[cheat_id] = cheat
        self._by_address[cheat.address].append(cheat_id)
        return cheat

    def enable_cheat(self, cheat_id: int) -> None:
        self._get(cheat_id).enabled = True

    def disable_cheat(self, cheat_id: int) -> None:
        self._get(cheat_id).enabled = False

    def remove_cheat(self, cheat_id: int) -> None:
        cheat = self._cheats.pop(cheat_id)
        ids = self._by_address.get(cheat.address)
        if ids is not None:
            ids[:] = [existing for existing in ids if existing != cheat_id]
            if not ids:
                del self._by_address[cheat.address]

    def list_active_cheats(self) -> list[CheatPatch]:
        return [cheat for cheat in self._cheats.values() if cheat.enabled]

    def patch_read(self, address: int, actual_value: int) -> int:
        """Return patched value for a read, or the original byte when unchanged."""
        for cheat_id in self._by_address.get(address, []):
            cheat = self._cheats.get(cheat_id)
            if cheat is not None and cheat.matches(address, actual_value):
                return cheat.value
        return actual_value

    def _get(self, cheat_id: int) -> CheatPatch:
        cheat = self._cheats.get(cheat_id)
        if cheat is None:
            raise KeyError(f"Unknown cheat id: {cheat_id}")
        return cheat


__all__ = ["CheatDecodeError", "CheatManager"]
