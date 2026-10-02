"""QIDS-CAM public API."""

from .benchmark import generate_problem, run_benchmark
from .merkle import MerkleStore
from .proof import inspect_archive, verify_archive
from .schema import Candidate, Evidence, Problem, Proposition
from .solver import (
    BASELINE_CONFIG,
    DESTRUCTIVE_ONLY_CONFIG,
    MERKLE_ONLY_CONFIG,
    QIDS_CAM_CONFIG,
    QIDSCAMSolver,
    SolverConfig,
    SolveResult,
    run_all_ablations,
)

__all__ = [
    "verify_archive",
    "inspect_archive",
    "BASELINE_CONFIG",
    "Candidate",
    "DESTRUCTIVE_ONLY_CONFIG",
    "Evidence",
    "MERKLE_ONLY_CONFIG",
    "MerkleStore",
    "Problem",
    "Proposition",
    "QIDS_CAM_CONFIG",
    "QIDSCAMSolver",
    "SolveResult",
    "SolverConfig",
    "generate_problem",
    "run_all_ablations",
    "run_benchmark",
]

__version__ = "0.2.0"
