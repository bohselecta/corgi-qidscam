"""Small independently expressed oracle: no hashes, learning, ordering or pruning.

Optional memoization is by local alias, not semantic content identity. This is
also an inexpensive baseline, so timing includes less receipt work by design.
"""

from __future__ import annotations

import math
import time

from .schema import Problem
from .solver import QIDS_CAM_CONFIG, SolverConfig


def evaluate(
    problem: Problem, *, memoized: bool = False, config: SolverConfig = QIDS_CAM_CONFIG
):
    start = time.perf_counter()
    cache = {}
    expansions = 0
    reads = 0

    def status(score):
        if score <= config.destroy_below:
            return "destroyed"
        return "uncertain" if abs(score) <= config.uncertain_band else "survives"

    def visit(key):
        nonlocal expansions, reads
        if memoized and key in cache:
            return cache[key]
        expansions += 1
        p = problem.propositions[key]
        observations = [problem.evidence[e] for e in p.evidence]
        reads += len(observations)
        mass = math.fsum(e.confidence for e in observations)

        def phase(e):
            if config.phase_aggregation and e.phase_degrees is not None:
                return math.radians(e.phase_degrees)
            return 0.0 if e.stance == 1 else math.pi

        local = (
            round(
                math.fsum(e.confidence * math.cos(phase(e)) for e in observations)
                / mass,
                12,
            )
            if mass
            else 0.0
        )
        children = [visit(d) for d in p.depends_on]
        bad = [x for x in children if x[0] == "destroyed"]
        if status(local) == "destroyed":
            result = ("destroyed", local)
        elif bad:
            result = ("destroyed", min(x[1] for x in bad))
        else:
            mean = (
                math.fsum(x[1] for x in children) / len(children) if children else 0.0
            )
            score = (
                (
                    (1 - config.dependency_weight) * local
                    + config.dependency_weight * mean
                )
                if observations and children
                else (mean if children else local)
            )
            score = round(max(-1.0, min(1.0, score)), 12)
            result = (status(score), score)
        if memoized:
            cache[key] = result
        return result

    outcomes = []
    for c in problem.candidates:
        values = [visit(k) for k in c.requires]
        if any(v[0] == "destroyed" for v in values):
            outcome = (c.key, "destroyed", -1.0)
        else:
            score = round(
                max(
                    -1.0,
                    min(
                        1.0,
                        c.prior
                        + (
                            math.fsum(v[1] for v in values) / len(values)
                            if values
                            else 0.0
                        ),
                    ),
                ),
                12,
            )
            outcome = (c.key, status(score), score)
        outcomes.append(outcome)
    surviving = [x for x in outcomes if x[1] != "destroyed"]
    return {
        "winner": max(surviving, key=lambda x: (x[2], x[0]))[0] if surviving else None,
        "outcomes": outcomes,
        "proposition_expansions": expansions,
        "evidence_reads": reads,
        "elapsed_ms": (time.perf_counter() - start) * 1000,
    }
