"""Bounded strict JSON input and atomic user-requested output."""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

MAX_BYTES = 64 * 1024 * 1024


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("JSON number exceeds finite range")
    return result


def loads(text: str) -> Any:
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("JSON exceeds 64 MiB limit")
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_float=_finite_float,
            parse_constant=lambda x: (_ for _ in ()).throw(
                ValueError(f"nonfinite JSON number: {x}")
            ),
        )
    except (RecursionError, UnicodeError) as exc:
        raise ValueError("JSON nesting or encoding exceeds supported limits") from exc


def load(path: str | Path) -> Any:
    with Path(path).open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("JSON exceeds 64 MiB limit")
    try:
        return loads(raw.decode("utf-8"))
    except UnicodeError as exc:
        raise ValueError("JSON must be UTF-8") from exc


def write_json(path: str | Path, value: Any) -> None:
    text = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    )
    write_text(path, text)


def write_text(path: str | Path, text: str) -> None:
    """Atomically replace an explicitly requested bounded UTF-8 output."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("output exceeds 64 MiB archive limit")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent, delete=False
        ) as handle:
            temporary = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def terminal_text(value: object) -> str:
    """Escape control/bidi characters when displaying user-supplied evidence."""
    text = str(value)
    return "".join(
        f"\\u{ord(c):04x}"
        if ord(c) < 32
        or 127 <= ord(c) < 160
        or 0x202A <= ord(c) <= 0x202E
        or 0x2066 <= ord(c) <= 0x2069
        else c
        for c in text
    )
