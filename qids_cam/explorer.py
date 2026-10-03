"""Offline browser inspection of verified v2 execution receipts.

No browser solver or alternate hash codec is used. Export verifies in Python;
the HTML records that result and contains the exact archive for independent use.
"""
from __future__ import annotations

import copy
import json
from importlib import resources
from typing import Any

from .proof import verify_archive
from .schema import Problem
from .solver import QIDSCAMSolver, SolverConfig

MAX_EXPLORER_NODES = 5000
MAX_EXPLORER_EVENTS = 20000


def explorer_data(archive: dict[str, Any]) -> dict[str, Any]:
    # Bound visualization work before replay; the archive loader has its own limits.
    if not isinstance(archive, dict) or not isinstance(archive.get("nodes"), dict):
        raise ValueError("explorer requires a v2 archive")
    if len(archive["nodes"]) > MAX_EXPLORER_NODES:
        raise ValueError("explorer supports at most 5000 archive nodes; use CLI inspect")
    report = verify_archive(archive)
    if len(report["trace"]) > MAX_EXPLORER_EVENTS:
        raise ValueError("explorer supports at most 20000 trace events; use CLI inspect")
    nodes = archive["nodes"]
    proof = nodes[archive["root"]]["payload"]
    source = nodes[proof["input"]]["payload"]
    problem = Problem.from_dict(source["problem"])
    compiled = QIDSCAMSolver(SolverConfig(**proof["solver"])).compile(problem)
    states = nodes[proof["states"]]["payload"]["propositions"]
    aliases: dict[str, list[str]] = {}
    for key, cid in compiled.proposition_cids.items():
        if cid in nodes:
            aliases.setdefault(cid, []).append(key)
    propositions = []
    for cid, names in sorted(aliases.items()):
        resolved = next((states[n] for n in names if n in states), None)
        propositions.append({
            "cid": cid,
            "aliases": sorted(names),
            "statement": nodes[cid]["payload"]["statement"],
            "dependencies": nodes[cid]["payload"]["dependencies"],
            "evidence": nodes[cid]["payload"]["evidence"],
            "resolved": resolved,
        })
    return {
        "schema": "qids-cam/explorer/v1",
        "archive": copy.deepcopy(archive),
        # JS JSON.stringify drops 1.0's float spelling, changing Python CIDs.
        # Keep Python serialization intact for the downloadable archive.
        "archive_json": json.dumps(archive, ensure_ascii=False, allow_nan=False, sort_keys=True),
        "verification_at_export": report["verification"],
        "problem": {"id": problem.problem_id, "query": problem.query,
                    "metadata": problem.metadata},
        "proof": copy.deepcopy(proof),
        "propositions": propositions,
        "trace": report["trace"],
    }


def render_explorer(archive: dict[str, Any]) -> str:
    data = explorer_data(archive)
    assets = resources.files("qids_cam").joinpath("explorer")
    template = assets.joinpath("index.html").read_text(encoding="utf-8")
    # Escape HTML delimiters, including hostile script closers. User content is
    # rendered only with textContent; it never becomes executable HTML.
    encoded = json.dumps(data, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":"))
    encoded = encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return (template.replace("/*EXPLORER_CSS*/", assets.joinpath("style.css").read_text(encoding="utf-8"))
            .replace("/*EXPLORER_JS*/", assets.joinpath("app.js").read_text(encoding="utf-8"))
            .replace("__EXPLORER_DATA__", encoded))
