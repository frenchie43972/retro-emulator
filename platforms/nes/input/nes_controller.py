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
    _latched_state: tuple[int, ...] = field(default_factory=tuple)
    _read_index: int = 0
    _strobe: int = 0

    def __post_init__(self) -> None:
        self._latched_state = self.snapshot()

    def set_button_state(self, button: str, pressed: bool) -> None:
        mapped_button = self.key_mapping.get(button)
        if mapped_button is None:
            return
        self._buttons[mapped_button] = bool(pressed)

    def snapshot(self) -> tuple[int, ...]:
        """Capture current button state in serial register order."""

        return tuple(1 if self._buttons[name] else 0 for name in BUTTON_ORDER)

    def read(self) -> int:
        if self._strobe:
            self._latched_state = self.snapshot()
            self._read_index = 0
            return self._latched_state[0]

        if self._read_index >= len(self._latched_state):
            return 1

        value = self._latched_state[self._read_index]
        self._read_index += 1
        return value

    def write(self, value: int) -> None:
        next_strobe = value & 0x01
        if next_strobe == 1:
            self._read_index = 0
        elif self._strobe == 1 and next_strobe == 0:
            self._latched_state = self.snapshot()
            self._read_index = 0
        self._strobe = next_strobe


    def serialize_state(self) -> dict:
        return {
            "buttons": dict(self._buttons),
            "latched_state": list(self._latched_state),
            "read_index": self._read_index,
            "strobe": self._strobe,
        }

    def deserialize_state(self, state: dict) -> None:
        for button in BUTTON_ORDER:
            self._buttons[button] = bool(state["buttons"].get(button, False))
        self._latched_state = tuple(int(v) for v in state.get("latched_state", self.snapshot()))
        self._read_index = int(state.get("read_index", 0))
        self._strobe = int(state.get("strobe", 0)) & 0x01
