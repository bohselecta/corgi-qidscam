"""Portable proof checking and evidence inspection."""

from __future__ import annotations

from typing import Any

from .canonical import cid_for
from .io import terminal_text as safe
from .merkle import MerkleStore
from .reference import evaluate
from .schema import Problem
from .solver import QIDSCAMSolver, SolverConfig


def verify_archive(archive: dict[str, Any], *, replay: bool = True) -> dict[str, Any]:
    store = MerkleStore.from_archive(archive)
    root = archive["root"]
    proof = store.get(root)
    if (
        proof.kind != "solve-proof"
        or proof.payload.get("proof_schema") != "qids-cam/solve-proof/v2"
    ):
        raise ValueError(
            "not a supported v2 solve receipt; use hash-only mode for historical/generic DAGs"
        )
    p = proof.payload
    required = {
        "proof_schema",
        "algorithm_version",
        "solver",
        "problem_root",
        "input",
        "context",
        "context_node",
        "trace",
        "states",
        "winner",
        "candidates",
        "metrics",
    }
    if set(p) != required or p["algorithm_version"] != "0.2.0":
        raise ValueError("unsupported or malformed solve receipt")
    expected = {
        "input": "solve-input",
        "context_node": "constraint-context",
        "trace": "execution-trace",
        "states": "resolved-states",
        "problem_root": "problem",
    }
    for field, kind in expected.items():
        if p[field] not in proof.links or store.get(p[field]).kind != kind:
            raise ValueError(f"proof {field} must link a {kind} node")
    source = store.get(p["input"]).payload
    if set(source) != {"problem", "constraints"} or not isinstance(
        source["constraints"], dict
    ):
        raise ValueError("malformed solve input")
    problem = Problem.from_dict(source["problem"])
    context = cid_for(source["constraints"], namespace="qids-cam-constraint-context-v1")
    if p["context"] != context or store.get(p["context_node"]).payload != {
        "context_cid": context,
        "constraints": source["constraints"],
    }:
        raise ValueError("context mismatch")
    if not isinstance(p["solver"], dict):
        raise ValueError("solver config must be an object")
    try:
        config = SolverConfig(**p["solver"])
    except TypeError as exc:
        raise ValueError("malformed solver config") from exc
    if replay:
        reproduced = QIDSCAMSolver(config).solve(
            problem, constraints=source["constraints"]
        )
        if reproduced.proof_root != root:
            raise ValueError("deterministic execution replay mismatch")
        oracle = evaluate(problem, memoized=True, config=config)
        if oracle["winner"] != reproduced.winner:
            raise ValueError("independent reference winner mismatch")
        for actual, expected_outcome in zip(
            reproduced.candidate_results, oracle["outcomes"]
        ):
            if (actual.key, actual.status) != expected_outcome[:2] or abs(
                actual.score - expected_outcome[2]
            ) > 1e-10:
                raise ValueError("independent reference candidate mismatch")
    return {
        "root": root,
        "nodes": len(store),
        "winner": p["winner"],
        "algorithm_version": p["algorithm_version"],
        "verification": "hash + context + deterministic replay + independent reference"
        if replay
        else "hash + receipt structure + context",
        "problem_id": problem.problem_id,
        "metrics": p["metrics"],
        "candidates": p["candidates"],
        "trace": store.get(p["trace"]).payload["events"],
    }


def inspect_archive(
    archive: dict[str, Any], *, cid: str | None = None, limit: int = 20
) -> str:
    report = verify_archive(archive)
    lines = [
        "QIDS-CAM / proof inspector",
        f"Verified: {report['verification']}",
        f"Problem: {safe(report['problem_id'])}",
        f"Winner: {safe(report['winner'])}",
        f"Root: {report['root']}",
        f"Nodes: {report['nodes']}",
        "",
        "Candidate outcomes",
    ]
    for c in report["candidates"]:
        lines.append(
            f"  {safe(c['key']):<24} {c['status']:<10} score={c['score']:+.6f}"
        )
        if c["skipped_requirements"]:
            lines.append(
                "    skipped: " + ", ".join(safe(x) for x in c["skipped_requirements"])
            )
    lines += [
        "",
        f"Trace / first {min(limit, len(report['trace']))} of {len(report['trace'])} events",
    ]
    for e in report["trace"][:limit]:
        lines.append(f"  {e['step']:>4} {e['event']:<20} {safe(e['subject'])}")
        lines.append(f"       {safe(e['detail'])}")
    if cid:
        from .canonical import canonical_json

        node = MerkleStore.from_archive(archive).get(cid)
        lines += [
            "",
            f"Node / {node.kind}",
            cid,
            safe(canonical_json(node.as_record())),
        ]
    lines += [
        "",
        "Receipt integrity does not prove evidence truth or production answer quality.",
    ]
    return "\n".join(lines)
