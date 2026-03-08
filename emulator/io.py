"""Host I/O abstractions and lightweight default implementations."""

from __future__ import annotations

from dataclasses import dataclass, field

from .interfaces import AudioOutput, FrameBuffer, InputProvider, VideoOutput


@dataclass
class FrameBufferVideoOutput(VideoOutput):
    """Stores the last submitted frame for host integration/testing."""

    last_frame: FrameBuffer | None = None

    def display(self, frame: FrameBuffer) -> None:
        self.last_frame = frame


@dataclass
class BufferedAudioOutput(AudioOutput):
    """Collects audio samples for later playback or testing."""

    sample_buffer: list[float] = field(default_factory=list)

    def play(self, samples: list[float]) -> None:
        self.sample_buffer.extend(samples)


@dataclass
class KeyboardInputProvider(InputProvider):
    """Generic keyboard state provider.

    A host application can call :meth:`set_key_state` from event callbacks while
    the emulator runtime reads a snapshot via :meth:`poll`.
    """

    _state: dict[str, bool] = field(default_factory=dict)

    def set_key_state(self, key: str, pressed: bool) -> None:
        self._state[key] = pressed

    def poll(self) -> dict[str, bool]:
        return dict(self._state)
