from __future__ import annotations

import unittest
from pathlib import Path

from qids_cam.schema import Problem
from qids_cam.solver import QIDSCAMSolver, run_all_ablations

ROOT = Path(__file__).resolve().parents[1]


class SolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.problem = Problem.load(ROOT / "examples" / "outage-investigation.json")

    def test_expected_winner(self) -> None:
        result = QIDSCAMSolver().solve(self.problem)
        self.assertEqual(result.winner, "cache_stampede")
        self.assertTrue(result.store.verify(result.proof_root, recursive=True))

    def test_proof_root_is_reproducible(self) -> None:
        first = QIDSCAMSolver().solve(self.problem)
        second = QIDSCAMSolver().solve(self.problem)
        self.assertEqual(first.problem_root, second.problem_root)
        self.assertEqual(first.proof_root, second.proof_root)

    def test_identical_aliases_share_a_cid(self) -> None:
        solver = QIDSCAMSolver()
        compiled = solver.compile(self.problem)
        self.assertEqual(
            compiled.proposition_cids["database_healthy"],
            compiled.proposition_cids["database_healthy_alias"],
        )

    def test_ablations_preserve_answer(self) -> None:
        runs = run_all_ablations(self.problem)
        self.assertEqual(
            {result.winner for result in runs.values()}, {"cache_stampede"}
        )
        full = runs["qids-cam"].metrics
        baseline = runs["independent-exhaustive"].metrics
        self.assertLess(full.proposition_expansions, baseline.proposition_expansions)
        self.assertLess(full.evidence_reads, baseline.evidence_reads)


if __name__ == "__main__":
    unittest.main()
