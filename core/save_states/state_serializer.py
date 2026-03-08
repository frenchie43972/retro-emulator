"""Serialization helpers for emulator save state files."""

from __future__ import annotations

import base64
import json
from typing import Any


class StateFormatError(ValueError):
    """Raised when a save state payload is malformed or unsupported."""


def serialize_state_document(document: dict[str, Any]) -> bytes:
    """Serialize a state document to UTF-8 JSON bytes."""

    return json.dumps(_encode_value(document), separators=(",", ":")).encode("utf-8")


def deserialize_state_document(payload: bytes) -> dict[str, Any]:
    """Parse UTF-8 JSON save state bytes into a document."""

    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise StateFormatError("Save state is not valid UTF-8 JSON") from exc

    result = _decode_value(decoded)
    if not isinstance(result, dict):
        raise StateFormatError("Save state root must be a JSON object")
    return result


def _encode_value(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray)):
        return {
            "__type__": "bytes",
            "data": base64.b64encode(bytes(value)).decode("ascii"),
        }
    if isinstance(value, dict):
        return {key: _encode_value(inner) for key, inner in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode_value(item) for item in value]
    return value


def _decode_value(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("__type__") == "bytes":
            data = value.get("data")
            if not isinstance(data, str):
                raise StateFormatError("Corrupt save state bytes payload")
            try:
                return base64.b64decode(data.encode("ascii"), validate=True)
            except ValueError as exc:
                raise StateFormatError("Corrupt save state base64 payload") from exc
        return {key: _decode_value(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_decode_value(item) for item in value]
    return value

