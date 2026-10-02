"""Validated problem schema for evidence-graph destructive search."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .canonical import canonical_json
from .io import load


@dataclass(frozen=True, slots=True)
class Evidence:
    key: str
    text: str
    stance: int
    confidence: float
    source: str
    phase_degrees: float | None = None
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.key, "evidence key")
        _text(self.text, "evidence text")
        _text(self.source, "source")
        _refs(self.tags, "tags")
        _number(self.confidence, "confidence")
        if self.phase_degrees is not None:
            _number(self.phase_degrees, "phase_degrees")
        object.__setattr__(self, "confidence", float(self.confidence))
        if self.phase_degrees is not None:
            object.__setattr__(self, "phase_degrees", float(self.phase_degrees))
        if type(self.stance) is not int or self.stance not in (-1, 1):
            raise ValueError(f"evidence {self.key!r}: stance must be -1 or 1")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"evidence {self.key!r}: confidence must be in [0, 1]")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Evidence":
        _fields(
            value,
            {"key", "text", "stance", "confidence", "source", "phase_degrees", "tags"},
            {"key", "text", "stance", "confidence"},
        )
        return cls(
            key=value["key"],
            text=value["text"],
            stance=value["stance"],
            confidence=value["confidence"],
            source=value.get("source", "unknown"),
            phase_degrees=(
                None if value.get("phase_degrees") is None else value["phase_degrees"]
            ),
            tags=tuple(item for item in value.get("tags", ())),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "text": self.text,
            "stance": self.stance,
            "confidence": self.confidence,
            "source": self.source,
            "phase_degrees": self.phase_degrees,
            "tags": list(self.tags),
        }


@dataclass(frozen=True, slots=True)
class Proposition:
    key: str
    statement: str
    evidence: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        _text(self.key, "proposition key")
        _text(self.statement, "statement")
        _refs(self.evidence, "evidence references")
        _refs(self.depends_on, "dependencies")
        _metadata(self.metadata)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Proposition":
        _fields(
            value,
            {"key", "statement", "evidence", "depends_on", "metadata"},
            {"key", "statement"},
        )
        return cls(
            key=value["key"],
            statement=value["statement"],
            evidence=tuple(item for item in value.get("evidence", ())),
            depends_on=tuple(item for item in value.get("depends_on", ())),
            metadata=dict(value.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "statement": self.statement,
            "evidence": list(self.evidence),
            "depends_on": list(self.depends_on),
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class Candidate:
    key: str
    label: str
    requires: tuple[str, ...]
    prior: float = 0.0

    def __post_init__(self):
        _text(self.key, "candidate key")
        _text(self.label, "label")
        _refs(self.requires, "requirements")
        _number(self.prior, "prior")
        object.__setattr__(self, "prior", float(self.prior))
        if not -1 <= self.prior <= 1:
            raise ValueError("candidate prior must be in [-1, 1]")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Candidate":
        _fields(
            value, {"key", "label", "requires", "prior"}, {"key", "label", "requires"}
        )
        return cls(
            key=value["key"],
            label=value["label"],
            requires=tuple(item for item in value.get("requires", ())),
            prior=value.get("prior", 0.0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "requires": list(self.requires),
            "prior": self.prior,
        }


@dataclass(frozen=True, slots=True)
class Problem:
    problem_id: str
    query: str
    evidence: dict[str, Evidence]
    propositions: dict[str, Proposition]
    candidates: tuple[Candidate, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _text(self.problem_id, "problem_id")
        _text(self.query, "query")
        _metadata(self.metadata)
        if (
            len(self.evidence) > 20000
            or len(self.propositions) > 10000
            or len(self.candidates) > 4096
        ):
            raise ValueError("problem exceeds supported object limits")
        if len({c.key for c in self.candidates}) != len(self.candidates):
            raise ValueError("duplicate candidate key")
        for key, evidence in self.evidence.items():
            if key != evidence.key:
                raise ValueError(f"evidence map key {key!r} does not match object key")
        evidence_keys = set(self.evidence)
        proposition_keys = set(self.propositions)
        edges = sum(
            len(p.evidence) + len(p.depends_on) for p in self.propositions.values()
        ) + sum(len(c.requires) for c in self.candidates)
        if edges > 500000:
            raise ValueError("problem exceeds 500000 reference limit")
        for key, proposition in self.propositions.items():
            if key != proposition.key:
                raise ValueError(
                    f"proposition map key {key!r} does not match object key"
                )
            missing_evidence = set(proposition.evidence) - evidence_keys
            missing_dependencies = set(proposition.depends_on) - proposition_keys
            if missing_evidence:
                raise ValueError(f"{key}: missing evidence {sorted(missing_evidence)}")
            if missing_dependencies:
                raise ValueError(
                    f"{key}: missing dependencies {sorted(missing_dependencies)}"
                )
        for candidate in self.candidates:
            missing = set(candidate.requires) - proposition_keys
            if missing:
                raise ValueError(
                    f"candidate {candidate.key}: missing requirements {sorted(missing)}"
                )
        self._assert_acyclic()

    def _assert_acyclic(self) -> None:
        colors = {}
        depths = {}
        for root in self.propositions:
            stack = [(root, False)]
            while stack:
                key, leaving = stack.pop()
                deps = self.propositions[key].depends_on
                if leaving:
                    depths[key] = 1 + max((depths[d] for d in deps), default=0)
                    if depths[key] > 128:
                        raise ValueError("graph depth exceeds 128")
                    colors[key] = 2
                    continue
                if colors.get(key) == 1:
                    raise ValueError(f"cycle detected at proposition {key!r}")
                if colors.get(key) == 2:
                    continue
                colors[key] = 1
                stack.append((key, True))
                stack.extend((d, False) for d in reversed(deps))

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Problem":
        _fields(
            value,
            {
                "schema",
                "problem_id",
                "query",
                "evidence",
                "propositions",
                "candidates",
                "metadata",
            },
            {"problem_id", "query"},
        )
        if value.get("schema", "qids-cam/problem/v1") != "qids-cam/problem/v1":
            raise ValueError("unsupported problem schema")
        for name in ("evidence", "propositions", "candidates"):
            if not isinstance(value.get(name, []), list):
                raise ValueError(f"{name} must be an array")
        evidence_items = [
            Evidence.from_dict(item) for item in value.get("evidence", ())
        ]
        proposition_items = [
            Proposition.from_dict(item) for item in value.get("propositions", ())
        ]
        if len({x.key for x in evidence_items}) != len(evidence_items) or len(
            {x.key for x in proposition_items}
        ) != len(proposition_items):
            raise ValueError("duplicate evidence or proposition key")
        return cls(
            problem_id=value["problem_id"],
            query=value["query"],
            evidence={item.key: item for item in evidence_items},
            propositions={item.key: item for item in proposition_items},
            candidates=tuple(
                Candidate.from_dict(item) for item in value.get("candidates", ())
            ),
            metadata=dict(value.get("metadata", {})),
        )

    @classmethod
    def load(cls, path: str | Path) -> "Problem":
        value = load(path)
        if not isinstance(value, dict):
            raise ValueError("problem JSON must contain an object")
        return cls.from_dict(value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "qids-cam/problem/v1",
            "problem_id": self.problem_id,
            "query": self.query,
            "evidence": [self.evidence[key].to_dict() for key in sorted(self.evidence)],
            "propositions": [
                self.propositions[key].to_dict() for key in sorted(self.propositions)
            ],
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "metadata": self.metadata,
        }


def _text(value, name):
    if not isinstance(value, str) or not value or len(value) > 100000:
        raise ValueError(f"{name} must be a nonempty bounded string")


def _number(value, name):
    if (
        type(value) not in (int, float)
        or abs(value) > 1e300
        or not math.isfinite(value)
    ):
        raise ValueError(f"{name} must be a finite number")


def _refs(value, name):
    if not isinstance(value, (tuple, list)) or any(
        not isinstance(x, str) or not x for x in value
    ):
        raise ValueError(f"{name} must be a sequence of nonempty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"duplicate {name}")


def _metadata(value):
    if not isinstance(value, dict):
        raise ValueError("metadata must be an object")
    canonical_json(value)
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("metadata must contain JSON values") from exc


def _fields(value, allowed, required):
    if (
        not isinstance(value, dict)
        or not required <= set(value)
        or set(value) - allowed
    ):
        raise ValueError("missing, unknown or malformed object fields")
    for name in ("evidence", "depends_on", "requires", "tags"):
        if (
            "problem_id" not in allowed
            and name in value
            and (
                not isinstance(value[name], list)
                or any(not isinstance(x, str) for x in value[name])
            )
        ):
            raise ValueError(f"{name} must be an array of strings")
    if "metadata" in value:
        _metadata(value["metadata"])
