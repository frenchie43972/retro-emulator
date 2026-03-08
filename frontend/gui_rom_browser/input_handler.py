"""Keyboard input mapping for the pygame ROM browser."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MenuAction:
    """Represents a high-level menu action produced from a key press."""

    name: str
    delta: int = 0


class MenuInputHandler:
    """Translate pygame key codes into menu actions."""

    def action_for_key(self, key: int) -> MenuAction:
        import pygame

        if key == pygame.K_UP:
            return MenuAction(name="move", delta=-1)
        if key == pygame.K_DOWN:
            return MenuAction(name="move", delta=1)
        if key == pygame.K_RETURN:
            return MenuAction(name="launch")
        if key == pygame.K_ESCAPE:
            return MenuAction(name="exit")
        return MenuAction(name="noop")
