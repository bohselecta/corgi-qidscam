"""Command-line interface for QIDS-CAM."""

from __future__ import annotations

import argparse
import builtins
import json
import sys
from dataclasses import asdict
from importlib import resources
from pathlib import Path
from typing import Any

from .benchmark import SCALES, run_benchmark
from .io import load, loads, terminal_text, write_json
from .merkle import MerkleStore
from .proof import inspect_archive, verify_archive
from .schema import Problem
from .solver import QIDS_CAM_CONFIG, QIDSCAMSolver, run_all_ablations


def print_line(*values):
    builtins.print(*(terminal_text(v) for v in values))


DEFAULT_EXAMPLE_RESOURCE = "data/outage-investigation.json"


def _load_problem(path: str | Path | None) -> Problem:
    if path is not None:
        return Problem.load(path)
    text = (
        resources.files("qids_cam")
        .joinpath(DEFAULT_EXAMPLE_RESOURCE)
        .read_text(encoding="utf-8")
    )
    value = loads(text)
    if not isinstance(value, dict):
        raise ValueError("built-in problem JSON must contain an object")
    return Problem.from_dict(value)


def _write_json(path: str | Path, value: Any) -> None:
    write_json(path, value)


def _metric_line(name: str, value: object) -> str:
    return f"  {name.replace('_', ' '):<28} {value}"


def command_demo(args: argparse.Namespace) -> int:
    problem = _load_problem(args.problem)
    solver = QIDSCAMSolver(QIDS_CAM_CONFIG)
    constraints = load(args.context) if args.context else None
    result = solver.solve(problem, constraints=constraints)

    print_line("QIDS-CAM destructive solve")
    print_line(f"  problem                     {result.problem_id}")
    print_line(f"  winner                      {result.winner}")
    print_line(f"  problem root                {result.problem_root}")
    print_line(f"  proof root                  {result.proof_root}")
    print_line("  metrics")
    for key, value in asdict(result.metrics).items():
        shown = round(value, 4) if isinstance(value, float) else value
        print_line(_metric_line(key, shown))
    print_line("  candidate outcomes")
    for candidate in result.candidate_results:
        print_line(
            f"    {candidate.key:<20} {candidate.status:<10} "
            f"score={candidate.score:>7.3f}  {candidate.label}"
        )

    if args.json:
        _write_json(args.json, result.to_dict(include_trace=True))
        print_line(f"  wrote result                {args.json}")
    if args.archive:
        _write_json(args.archive, result.store.export_archive(result.proof_root))
        print_line(f"  wrote verifiable archive    {args.archive}")
    return 0


def command_compare(args: argparse.Namespace) -> int:
    problem = _load_problem(args.problem)
    runs = run_all_ablations(problem)
    print_line(f"Comparison for {problem.problem_id}")
    header = (
        f"{'configuration':<25} {'winner':<18} {'expansions':>11} "
        f"{'evidence':>9} {'memo':>7} {'nogood':>8} {'prunes':>8}"
    )
    print_line(header)
    print_line("-" * len(header))
    for name, result in runs.items():
        metrics = result.metrics
        print_line(
            f"{name:<25} {str(result.winner):<18} "
            f"{metrics.proposition_expansions:>11} {metrics.evidence_reads:>9} "
            f"{metrics.memo_hits:>7} {metrics.nogood_hits:>8} "
            f"{metrics.early_prunes:>8}"
        )
    if args.json:
        _write_json(
            args.json,
            {
                "schema": "qids-cam/comparison/v1",
                "problem_id": problem.problem_id,
                "runs": {
                    name: result.to_dict(include_trace=False)
                    for name, result in runs.items()
                },
            },
        )
        print_line(f"wrote {args.json}")
    parity = len({result.winner for result in runs.values()}) <= 1
    return 0 if parity else 2


def command_benchmark(args: argparse.Namespace) -> int:
    if args.suite:
        from .suite import run_suite

        value = run_suite()
        print_line(
            f"Synthetic v2 suite / parity={value['parity']} / deterministic={value['deterministic']}"
        )
        if args.json:
            _write_json(args.json, value)
        return 0 if value["parity"] and value["deterministic"] else 2
    value = run_benchmark(args.scale, seed=args.seed)
    print_line(f"QIDS-CAM benchmark: {args.scale}, seed={args.seed}")
    print_line(f"  answer parity               {value['answer_parity']}")
    print_line(
        "  reduction vs exhaustive     "
        f"{value['ratios']['expansion_reduction_vs_exhaustive']}x"
    )
    print_line(
        "  reduction vs destructive    "
        f"{value['ratios']['expansion_reduction_vs_destructive_only']}x"
    )
    header = (
        f"{'configuration':<25} {'winner':<18} {'expansions':>11} "
        f"{'evidence':>9} {'memo':>7} {'nogood':>8} {'avoided':>8}"
    )
    print_line(header)
    print_line("-" * len(header))
    for name, run in value["runs"].items():
        print_line(
            f"{name:<25} {str(run['winner']):<18} "
            f"{run['proposition_expansions']:>11} {run['evidence_reads']:>9} "
            f"{run['memo_hits']:>7} {run['nogood_hits']:>8} "
            f"{run['avoided_requirements']:>8}"
        )
    if args.json:
        _write_json(args.json, value)
        print_line(f"wrote {args.json}")
    return 0 if value["answer_parity"] else 2


def command_verify(args: argparse.Namespace) -> int:
    archive = load(args.archive)
    if args.hash_only:
        store = MerkleStore.from_archive(archive)
        print_line(f"verified {len(store)} nodes / hash integrity only")
        print_line(f"root {archive['root']}")
    else:
        report = verify_archive(archive)
        print_line(f"verified {report['nodes']} nodes / {report['verification']}")
        print_line(f"winner {report['winner']}")
        print_line(f"root {report['root']}")
    return 0


def command_inspect(args: argparse.Namespace) -> int:
    if args.limit < 0 or args.limit > 1000:
        raise ValueError("trace limit must be 0..1000")
    archive = load(args.archive)
    if args.json:
        builtins.print(json.dumps(verify_archive(archive), indent=2, ensure_ascii=True))
    else:
        builtins.print(inspect_archive(archive, cid=args.cid, limit=args.limit))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qids-cam",
        description=(
            "Quantum-inspired destructive search with persistent, "
            "content-addressed memory. Classical research prototype."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="run the outage evidence demo")
    demo.add_argument(
        "--problem", help="problem JSON; defaults to the packaged outage demo"
    )
    demo.add_argument(
        "--context", help="JSON constraint namespace (does not change evidence scoring)"
    )
    demo.add_argument("--json", help="write full result JSON")
    demo.add_argument("--archive", help="write a verifiable Merkle-DAG archive")
    demo.set_defaults(func=command_demo)

    compare = subparsers.add_parser("compare", help="compare all solver ablations")
    compare.add_argument(
        "--problem", help="problem JSON; defaults to the packaged outage demo"
    )
    compare.add_argument("--json", help="write comparison JSON")
    compare.set_defaults(func=command_compare)

    benchmark = subparsers.add_parser(
        "benchmark", help="run the shared-subgraph benchmark"
    )
    benchmark.add_argument(
        "--suite",
        action="store_true",
        help="run all five v2 workloads, seven configurations, three fixed seeds",
    )
    benchmark.add_argument("--scale", choices=sorted(SCALES), default="medium")
    benchmark.add_argument("--seed", type=int, default=7)
    benchmark.add_argument("--json", help="write benchmark JSON")
    benchmark.set_defaults(func=command_benchmark)

    verify = subparsers.add_parser("verify", help="verify an exported proof archive")
    verify.add_argument("archive")
    verify.add_argument(
        "--hash-only",
        action="store_true",
        help="check DAG integrity only; no execution claim",
    )
    verify.set_defaults(func=command_verify)
    solve = subparsers.add_parser(
        "solve", help="solve an evidence graph and export a receipt"
    )
    solve.add_argument("problem")
    solve.add_argument("--context")
    solve.add_argument("--json")
    solve.add_argument("--archive")
    solve.set_defaults(func=command_demo)
    inspect = subparsers.add_parser(
        "inspect", help="inspect a verified portable proof and its trace"
    )
    inspect.add_argument("archive")
    inspect.add_argument("--cid")
    inspect.add_argument("--limit", type=int, default=20)
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(func=command_inspect)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (
        ValueError,
        KeyError,
        OSError,
        TypeError,
        OverflowError,
        RecursionError,
    ) as exc:
        parser.error(terminal_text(exc))
    return 2


if __name__ == "__main__":
    sys.exit(main())
