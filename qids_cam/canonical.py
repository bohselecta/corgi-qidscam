"""Deterministic serialization and content identifiers for QIDS-CAM."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when a value cannot be represented canonically."""


def _normalize(value: Any) -> Any:
    """Return a JSON-safe, deterministic representation of *value*.

    The format intentionally stays simple. It is not a full IPLD codec; it is a
    small, inspectable canonical form suitable for this research prototype.
    """

    if dataclasses.is_dataclass(value):
        return _normalize(dataclasses.asdict(value))
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalizationError("NaN and infinite floats are not canonical")
        return 0.0 if value == 0.0 else value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("mapping keys must be strings")
            normalized[key] = _normalize(item)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, (set, frozenset)):
        items = [_normalize(item) for item in value]
        return sorted(items, key=canonical_json)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize(item) for item in value]
    raise CanonicalizationError(f"unsupported canonical type: {type(value)!r}")


def canonical_json(value: Any) -> str:
    """Serialize *value* into a stable UTF-8 JSON representation."""

    return json.dumps(
        _normalize(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_bytes(value: Any) -> bytes:
    """Return canonical JSON encoded as UTF-8."""

    return canonical_json(value).encode("utf-8")


def cid_for(value: Any, *, namespace: str = "qids-cam") -> str:
    """Create a namespaced SHA-256 content identifier."""

    digest = hashlib.sha256(namespace.encode("utf-8") + b"\0" + canonical_bytes(value))
    return f"sha256:{digest.hexdigest()}"
