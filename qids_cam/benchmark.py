"""Synthetic shared-subgraph benchmark for QIDS-CAM."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Any

from .schema import Candidate, Evidence, Problem, Proposition
from .solver import SolveResult, run_all_ablations


@dataclass(frozen=True, slots=True)
class BenchmarkScale:
    name: str
    candidates: int
    good_leaves: int
    good_modules: int
    trap_groups: int
    requirements_per_candidate: int


SCALES: dict[str, BenchmarkScale] = {
    "small": BenchmarkScale("small", 16, 16, 8, 3, 4),
    "medium": BenchmarkScale("medium", 128, 48, 24, 8, 7),
    "large": BenchmarkScale("large", 1024, 96, 48, 16, 9),
}


def generate_problem(scale: str = "medium", *, seed: int = 7) -> Problem:
    if scale not in SCALES:
        raise ValueError(
            f"unknown benchmark scale {scale!r}; choose from {sorted(SCALES)}"
        )
    spec = SCALES[scale]
    rng = random.Random(seed)

    evidence: dict[str, Evidence] = {}
    propositions: dict[str, Proposition] = {}

    for index in range(spec.good_leaves):
        evidence_keys: list[str] = []
        for sample in range(3):
            key = f"e_good_{index}_{sample}"
            evidence_keys.append(key)
            evidence[key] = Evidence(
                key=key,
                text=f"Independent telemetry supports reusable fact {index}, sample {sample}.",
                stance=1,
                confidence=round(rng.uniform(0.70, 0.97), 4),
                source=f"telemetry://good/{index}/{sample}",
            )
        propositions[f"leaf_good_{index}"] = Proposition(
            key=f"leaf_good_{index}",
            statement=f"Shared fact {index} remains compatible with the observations.",
            evidence=tuple(evidence_keys),
        )

    for index in range(spec.trap_groups):
        support_key = f"e_trap_{index}_support"
        oppose_a = f"e_trap_{index}_oppose_a"
        oppose_b = f"e_trap_{index}_oppose_b"
        evidence[support_key] = Evidence(
            key=support_key,
            text=f"A noisy source weakly suggests trap proposition {index}.",
            stance=1,
            confidence=0.21,
            source=f"report://unverified/{index}",
        )
        evidence[oppose_a] = Evidence(
            key=oppose_a,
            text=f"Authoritative measurement contradicts trap proposition {index}.",
            stance=-1,
            confidence=0.96,
            source=f"telemetry://authoritative/{index}/a",
        )
        evidence[oppose_b] = Evidence(
            key=oppose_b,
            text=f"Independent audit also contradicts trap proposition {index}.",
            stance=-1,
            confidence=0.89,
            source=f"audit://independent/{index}/b",
        )
        propositions[f"leaf_trap_{index}"] = Proposition(
            key=f"leaf_trap_{index}",
            statement=f"Fatal shared assumption {index} is valid.",
            evidence=(support_key, oppose_a, oppose_b),
        )

    for index in range(spec.good_modules):
        dependencies = tuple(
            f"leaf_good_{(index * 3 + offset) % spec.good_leaves}"
            for offset in range(3)
        )
        evidence_key = f"e_module_good_{index}"
        evidence[evidence_key] = Evidence(
            key=evidence_key,
            text=f"Module-level observation supports composite module {index}.",
            stance=1,
            confidence=round(rng.uniform(0.60, 0.88), 4),
            source=f"module://good/{index}",
        )
        propositions[f"module_good_{index}"] = Proposition(
            key=f"module_good_{index}",
            statement=f"Composite reusable module {index} is internally consistent.",
            evidence=(evidence_key,),
            depends_on=dependencies,
        )

    for index in range(spec.trap_groups):
        dependencies = (
            f"leaf_trap_{index}",
            f"leaf_good_{(index * 5) % spec.good_leaves}",
            f"leaf_good_{(index * 5 + 1) % spec.good_leaves}",
        )
        propositions[f"module_trap_{index}"] = Proposition(
            key=f"module_trap_{index}",
            statement=f"Composite branch containing fatal assumption {index} survives.",
            depends_on=dependencies,
        )

    good_requirement_pool = [f"module_good_{i}" for i in range(spec.good_modules)]
    winner_requirements = tuple(
        good_requirement_pool[: spec.requirements_per_candidate]
    )
    candidates: list[Candidate] = [
        Candidate(
            key="candidate_0000",
            label="Known compatible hypothesis",
            requires=winner_requirements,
            prior=0.02,
        )
    ]

    for index in range(1, spec.candidates):
        trap = f"module_trap_{index % spec.trap_groups}"
        start = (index * 7) % spec.good_modules
        good_count = max(1, spec.requirements_per_candidate - 1)
        selected = [
            good_requirement_pool[(start + offset) % spec.good_modules]
            for offset in range(good_count)
        ]
        # The trap is intentionally last in source order. The destructive
        # fail-first heuristic must discover and move it to the front.
        candidates.append(
            Candidate(
                key=f"candidate_{index:04d}",
                label=f"Hypothesis {index} containing shared contradiction {index % spec.trap_groups}",
                requires=tuple((*selected, trap)),
            )
        )

    return Problem(
        problem_id=f"shared-subgraph-{scale}-seed-{seed}",
        query="Which candidate remains consistent after contradictory shared assumptions are eliminated?",
        evidence=evidence,
        propositions=propositions,
        candidates=tuple(candidates),
        metadata={
            "benchmark": True,
            "scale": asdict(spec),
            "seed": seed,
            "expected_winner": "candidate_0000",
        },
    )


def summarize_run(result: SolveResult) -> dict[str, Any]:
    metrics = result.metrics
    return {
        "winner": result.winner,
        "proof_root": result.proof_root,
        "candidate_evaluations": metrics.candidate_evaluations,
        "proposition_expansions": metrics.proposition_expansions,
        "evidence_reads": metrics.evidence_reads,
        "memo_hits": metrics.memo_hits,
        "nogood_hits": metrics.nogood_hits,
        "learned_nogoods": metrics.learned_nogoods,
        "early_prunes": metrics.early_prunes,
        "avoided_requirements": metrics.avoided_requirements,
        "unique_merkle_nodes": metrics.unique_merkle_nodes,
        "elapsed_ms": round(metrics.elapsed_ms, 4),
    }


def run_benchmark(scale: str = "medium", *, seed: int = 7) -> dict[str, Any]:
    problem = generate_problem(scale, seed=seed)
    runs = run_all_ablations(problem)
    expected = str(problem.metadata["expected_winner"])
    summaries = {name: summarize_run(result) for name, result in runs.items()}
    parity = all(summary["winner"] == expected for summary in summaries.values())
    baseline_expansions = summaries["independent-exhaustive"]["proposition_expansions"]
    full_expansions = summaries["qids-cam"]["proposition_expansions"]
    destructive_expansions = summaries["destructive-only"]["proposition_expansions"]
    return {
        "schema": "qids-cam/benchmark-result/v1",
        "scale": scale,
        "seed": seed,
        "problem": {
            "problem_id": problem.problem_id,
            "candidate_count": len(problem.candidates),
            "proposition_count": len(problem.propositions),
            "evidence_count": len(problem.evidence),
            "expected_winner": expected,
        },
        "answer_parity": parity,
        "runs": summaries,
        "ratios": {
            "expansion_reduction_vs_exhaustive": round(
                baseline_expansions / max(1, full_expansions), 4
            ),
            "expansion_reduction_vs_destructive_only": round(
                destructive_expansions / max(1, full_expansions), 4
            ),
        },
    }
