"""Strict content-addressed DAG storage; hash verification never runs a solver."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Iterable

from .canonical import cid_for

CID_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_NODES = 100_000
MAX_LINKS = 500_000


@dataclass(frozen=True, slots=True)
class MerkleNode:
    cid: str
    kind: str
    payload: dict[str, Any]
    links: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "schema": "qids-cam/node/v1",
            "kind": self.kind,
            "payload": copy.deepcopy(self.payload),
            "links": list(self.links),
        }


class MerkleStore:
    """Content is copied on insertion and retrieval, including nested payloads."""

    def __init__(self) -> None:
        self._nodes: dict[str, MerkleNode] = {}

    def put(self, kind: str, payload: dict[str, Any], links: Iterable[str] = ()) -> str:
        if not isinstance(kind, str) or not kind or not isinstance(payload, dict):
            raise ValueError(
                "node kind must be a nonempty string and payload an object"
            )
        items = tuple(links)
        if any(not isinstance(x, str) or not CID_PATTERN.fullmatch(x) for x in items):
            raise ValueError("links must contain SHA-256 CIDs")
        normalized = tuple(sorted(set(items)))
        record = {
            "schema": "qids-cam/node/v1",
            "kind": kind,
            "payload": copy.deepcopy(payload),
            "links": list(normalized),
        }
        cid = cid_for(record, namespace="qids-cam-node-v1")
        if cid not in self._nodes and len(self._nodes) >= MAX_NODES:
            raise ValueError("store exceeds node limit")
        self._nodes[cid] = MerkleNode(cid, kind, record["payload"], normalized)
        return cid

    def get(self, cid: str) -> MerkleNode:
        try:
            return copy.deepcopy(self._nodes[cid])
        except KeyError as exc:
            raise KeyError(f"unknown CID: {cid}") from exc

    def __contains__(self, cid: object) -> bool:
        return isinstance(cid, str) and cid in self._nodes

    def __len__(self) -> int:
        return len(self._nodes)

    def verify(self, cid: str, *, recursive: bool = True) -> bool:
        colors: dict[str, int] = {}
        stack = [(cid, False)]
        while stack:
            current, leaving = stack.pop()
            if leaving:
                colors[current] = 2
                continue
            if colors.get(current) == 1:
                return False
            if colors.get(current) == 2:
                continue
            node = self._nodes.get(current)
            if (
                node is None
                or cid_for(node.as_record(), namespace="qids-cam-node-v1") != current
            ):
                return False
            colors[current] = 1
            stack.append((current, True))
            if recursive:
                stack.extend((link, False) for link in reversed(node.links))
        return True

    def reachable(self, root: str) -> set[str]:
        found: set[str] = set()
        stack = [root]
        while stack:
            cid = stack.pop()
            if cid in found:
                continue
            node = self.get(cid)
            found.add(cid)
            stack.extend(node.links)
        return found

    def export_archive(self, root: str) -> dict[str, Any]:
        if not self.verify(root):
            raise ValueError("cannot export an invalid Merkle DAG")
        return {
            "schema": "qids-cam/archive/v1",
            "root": root,
            "nodes": {
                cid: self.get(cid).as_record() for cid in sorted(self.reachable(root))
            },
        }

    @classmethod
    def from_archive(cls, archive: dict[str, Any]) -> "MerkleStore":
        if (
            not isinstance(archive, dict)
            or set(archive) != {"schema", "root", "nodes"}
            or archive["schema"] != "qids-cam/archive/v1"
        ):
            raise ValueError("unsupported or malformed archive schema")
        raw = archive["nodes"]
        root = archive["root"]
        if not isinstance(raw, dict) or not raw or len(raw) > MAX_NODES:
            raise ValueError(
                "archive nodes must be a nonempty object within node limit"
            )
        if not isinstance(root, str) or not CID_PATTERN.fullmatch(root):
            raise ValueError("invalid root CID")
        store = cls()
        edges = 0
        for claimed, record in raw.items():
            if not isinstance(claimed, str) or not CID_PATTERN.fullmatch(claimed):
                raise ValueError("invalid node CID")
            if (
                not isinstance(record, dict)
                or set(record) != {"schema", "kind", "payload", "links"}
                or record["schema"] != "qids-cam/node/v1"
            ):
                raise ValueError("malformed node record")
            links = record["links"]
            if (
                not isinstance(links, list)
                or any(not isinstance(x, str) for x in links)
                or links != sorted(set(links))
            ):
                raise ValueError("node links must be sorted unique CID strings")
            edges += len(links)
            if edges > MAX_LINKS:
                raise ValueError("archive exceeds link limit")
            actual = store.put(record["kind"], record["payload"], links)
            if claimed != actual:
                raise ValueError(f"archive CID mismatch: {claimed}")
        if not store.verify(root):
            raise ValueError(
                "archive root failed verification: hash, cycle or missing node"
            )
        if store.reachable(root) != set(raw):
            raise ValueError("archive contains unreachable nodes")
        return store
