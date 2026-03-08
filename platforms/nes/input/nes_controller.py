"""NES controller state and host keyboard mapping."""

from __future__ import annotations

from dataclasses import dataclass, field

from emulator.interfaces import Controller

BUTTON_ORDER: tuple[str, ...] = (
    "A",
    "B",
    "Select",
    "Start",
    "Up",
    "Down",
    "Left",
    "Right",
)

DEFAULT_KEYBOARD_MAPPING: dict[str, str] = {
    "z": "A",
    "x": "B",
    "enter": "Start",
    "right shift": "Select",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
}


@dataclass
class NESController(Controller):
    """Tracks NES controller button state from host keyboard input."""

    key_mapping: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_KEYBOARD_MAPPING))
    _buttons: dict[str, bool] = field(
        default_factory=lambda: {button: False for button in BUTTON_ORDER}
    )

    def set_button_state(self, button: str, pressed: bool) -> None:
        mapped_button = self.key_mapping.get(button)
        if mapped_button is None:
            return
        self._buttons[mapped_button] = bool(pressed)

    def snapshot(self) -> tuple[int, ...]:
        """Capture current button state in serial register order."""

        return tuple(1 if self._buttons[name] else 0 for name in BUTTON_ORDER)


    def serialize_state(self) -> dict:
        return {"buttons": dict(self._buttons)}

    def deserialize_state(self, state: dict) -> None:
        for button in BUTTON_ORDER:
            self._buttons[button] = bool(state["buttons"].get(button, False))
