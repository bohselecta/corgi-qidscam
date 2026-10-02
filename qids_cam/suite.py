"""Declared synthetic workloads, simple baselines and matched ablations."""

from __future__ import annotations

import platform
import random
import time
from dataclasses import replace

from .benchmark import generate_problem
from .reference import evaluate
from .schema import Candidate, Evidence, Problem, Proposition
from .solver import (
    BASELINE_CONFIG,
    DESTRUCTIVE_ONLY_CONFIG,
    MERKLE_ONLY_CONFIG,
    QIDS_CAM_CONFIG,
    QIDSCAMSolver,
)

WORKLOADS = (
    "high-sharing",
    "low-sharing",
    "low-contradiction",
    "unique-no-contradiction",
    "adverse-ordering",
)
CONFIGS = (
    BASELINE_CONFIG,
    DESTRUCTIVE_ONLY_CONFIG,
    MERKLE_ONLY_CONFIG,
    QIDS_CAM_CONFIG,
    replace(QIDS_CAM_CONFIG, name="cid-pruning-no-learning", learn_nogoods=False),
)


def workload(name: str, seed: int) -> Problem:
    if name == "high-sharing":
        return generate_problem("medium", seed=seed)
    if name not in WORKLOADS:
        raise ValueError("unknown workload")
    rng = random.Random(seed)
    evidence = {}
    props = {}
    candidates = []
    shared = name == "low-contradiction"
    for i in range(32):
        group = i % 4 if shared else i
        keys = []
        for j in range(4):
            k = f"p{group}_{j}"
            keys.append(k)
            if k in props:
                continue
            adverse = name == "adverse-ordering"
            fatal = j == 0 and (
                adverse
                or (name == "low-sharing" and i % 3 == 0)
                or (shared and group == 0)
            )
            stance = (1 if j == 0 else -1) if adverse else (-1 if fatal else 1)
            phase = (180.0 if fatal else 0.0) if adverse else None
            evidence[k] = Evidence(
                k,
                f"Synthetic observation {group}/{j}",
                stance,
                round(rng.uniform(0.5, 1.0), 4),
                "synthetic://fixture",
                phase,
            )
            props[k] = Proposition(k, f"Synthetic proposition {group}/{j}", (k,))
        candidates.append(
            Candidate(f"c{i:02}", f"Synthetic candidate {i}", tuple(keys), i / 10000)
        )
    return Problem(
        f"{name}-seed-{seed}",
        "Synthetic candidate selection",
        evidence,
        props,
        tuple(candidates),
        {"synthetic": True, "workload": name, "seed": seed},
    )


def _same(outcomes, expected):
    return len(outcomes) == len(expected) and all(
        a[:2] == b[:2] and abs(a[2] - b[2]) <= 1e-10 for a, b in zip(outcomes, expected)
    )


def run_suite(seeds=(7, 19, 41)):
    rows = []
    for name in WORKLOADS:
        for seed in seeds:
            p = workload(name, seed)
            oracle = evaluate(p)
            runs = {}
            for memo in (False, True):
                label = "simple-alias-memoized" if memo else "simple-reference"
                first = evaluate(p, memoized=memo)
                second = evaluate(p, memoized=memo)
                deterministic = all(
                    first[k] == second[k]
                    for k in (
                        "winner",
                        "outcomes",
                        "proposition_expansions",
                        "evidence_reads",
                    )
                )
                runs[label] = {
                    **first,
                    "parity": first["winner"] == oracle["winner"]
                    and _same(first["outcomes"], oracle["outcomes"]),
                    "deterministic": deterministic,
                }
            for config in CONFIGS:
                start = time.perf_counter()
                first = QIDSCAMSolver(config).solve(p)
                elapsed = (time.perf_counter() - start) * 1000
                second = QIDSCAMSolver(config).solve(p)
                outcomes = [(x.key, x.status, x.score) for x in first.candidate_results]
                runs[config.name] = {
                    "winner": first.winner,
                    "outcomes": outcomes,
                    **first.metrics.deterministic(),
                    "proof_root": first.proof_root,
                    "end_to_end_ms": elapsed,
                    "parity": first.winner == oracle["winner"]
                    and _same(outcomes, oracle["outcomes"]),
                    "deterministic": first.proof_root == second.proof_root
                    and first.metrics.deterministic() == second.metrics.deterministic(),
                }
            rows.append(
                {"workload": name, "seed": seed, "synthetic": True, "runs": runs}
            )
    return {
        "schema": "qids-cam/suite/v2",
        "protocol": "docs/RESEARCH-PROTOCOL-v2.md",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "paid_runtime_usd": 0,
        "parity": all(r["parity"] for row in rows for r in row["runs"].values()),
        "deterministic": all(
            r["deterministic"] for row in rows for r in row["runs"].values()
        ),
        "cases": rows,
    }
