"""Minimal conflict-aware RAG adapter for QIDS-CAM.

This example intentionally uses fixed retrieved passages and fixed NLI outputs so
it is deterministic and requires no external model. Replace `retrieve` and
`classify_claim` with your own retriever and calibrated evidence evaluator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qids_cam import (
    Candidate,
    Evidence,
    Problem,
    Proposition,
    QIDSCAMSolver,
    verify_archive,
)
from qids_cam.io import load, write_json

CORPUS = [
    {
        "id": "runbook-cache",
        "text": "A cache stampede is accompanied by a rapid miss-rate increase and synchronized origin requests.",
    },
    {
        "id": "metric-miss-rate",
        "text": "During the incident the cache miss rate rose from 4% to 91% within two minutes.",
    },
    {
        "id": "metric-origin",
        "text": "Origin request concurrency increased 24x at the same time as the miss-rate increase.",
    },
    {
        "id": "deploy-log",
        "text": "No application deployment occurred in the six hours before the incident.",
    },
    {
        "id": "db-health",
        "text": "Database latency remained inside its normal range until origin traffic saturated the application tier.",
    },
]


def retrieve(query: str) -> list[dict[str, str]]:
    """Placeholder retriever returning a fixed, inspectable corpus."""

    del query
    return list(CORPUS)


def evidence(
    key: str,
    passage_id: str,
    text: str,
    *,
    stance: int,
    confidence: float,
) -> Evidence:
    """Convert a retrieved/NLI result into the QIDS-CAM evidence schema."""

    return Evidence(
        key=key,
        text=text,
        stance=stance,
        confidence=confidence,
        source=f"corpus://{passage_id}",
        tags=("retrieved", "deterministic-example"),
    )


def build_problem(query: str) -> Problem:
    passages = {item["id"]: item for item in retrieve(query)}

    evidence_items = [
        evidence(
            "ev_miss",
            "metric-miss-rate",
            passages["metric-miss-rate"]["text"],
            stance=1,
            confidence=0.97,
        ),
        evidence(
            "ev_origin",
            "metric-origin",
            passages["metric-origin"]["text"],
            stance=1,
            confidence=0.96,
        ),
        evidence(
            "ev_runbook",
            "runbook-cache",
            passages["runbook-cache"]["text"],
            stance=1,
            confidence=0.86,
        ),
        evidence(
            "ev_no_deploy",
            "deploy-log",
            passages["deploy-log"]["text"],
            stance=-1,
            confidence=0.99,
        ),
        evidence(
            "ev_db_normal",
            "db-health",
            passages["db-health"]["text"],
            stance=-1,
            confidence=0.91,
        ),
    ]

    propositions = [
        Proposition(
            key="cache_signature",
            statement="The incident exhibits the operational signature of a cache stampede.",
            evidence=("ev_miss", "ev_origin", "ev_runbook"),
        ),
        Proposition(
            key="recent_deploy",
            statement="A recent application deployment caused the incident.",
            evidence=("ev_no_deploy",),
        ),
        Proposition(
            key="primary_database_failure",
            statement="A primary database failure initiated the incident.",
            evidence=("ev_db_normal",),
        ),
        # This alias has identical semantic content and links. It therefore
        # compiles to the same CID as `recent_deploy`.
        Proposition(
            key="release_regression",
            statement="A recent application deployment caused the incident.",
            evidence=("ev_no_deploy",),
        ),
    ]

    candidates = (
        Candidate(
            key="cache_stampede",
            label="A cache stampede initiated the outage.",
            requires=("cache_signature",),
            prior=0.05,
        ),
        Candidate(
            key="bad_deploy",
            label="A bad deployment initiated the outage.",
            requires=("recent_deploy",),
        ),
        Candidate(
            key="release_regression_alias",
            label="A release regression initiated the outage.",
            requires=("release_regression",),
        ),
        Candidate(
            key="database_failure",
            label="A primary database failure initiated the outage.",
            requires=("primary_database_failure",),
        ),
    )

    return Problem(
        problem_id="minimal-rag-adapter",
        query=query,
        evidence={item.key: item for item in evidence_items},
        propositions={item.key: item for item in propositions},
        candidates=candidates,
        metadata={
            "adapter": "examples/rag_adapter.py",
            "retrieval_revision": "fixed-corpus-v1",
        },
    )


def main() -> None:
    query = "What most likely initiated the service outage?"
    problem = build_problem(query)
    context: dict[str, Any] = {
        "corpus_revision": "fixed-corpus-v1",
        "stance_policy": "fixed-demonstration-labels-v1",
        "as_of": "2026-08-17T00:00:00Z",
    }

    result = QIDSCAMSolver().solve(problem, constraints=context)

    print(f"winner:      {result.winner}")
    print(f"problem CID: {result.problem_root}")
    print(f"proof CID:   {result.proof_root}")
    print("candidate outcomes:")
    for candidate in result.candidate_results:
        print(f"  {candidate.key:<27} {candidate.status:<10} {candidate.reason}")

    recent = result.proposition_results["recent_deploy"]
    alias = result.proposition_results["release_regression"]
    print(f"semantic alias shares CID: {recent.cid == alias.cid}")
    print(f"no-good hits: {result.metrics.nogood_hits}")

    target = Path("results/rag-adapter-proof.json")
    write_json(target, result.store.export_archive(result.proof_root))
    verify_archive(load(target))
    print(f"verified archive: {target}")


if __name__ == "__main__":
    main()
