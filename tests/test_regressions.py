import unittest

from qids_cam import (
    Candidate,
    Evidence,
    MerkleStore,
    Problem,
    Proposition,
    QIDSCAMSolver,
    run_all_ablations,
)


class RegressionTests(unittest.TestCase):
    def test_local_fatal_cannot_be_rescued_by_dependencies(self):
        p = Problem(
            "fatal",
            "?",
            {
                "no": Evidence("no", "no", -1, 1.0, "fixture"),
                "yes": Evidence("yes", "yes", 1, 1.0, "fixture"),
            },
            {
                "good": Proposition("good", "good", ("yes",)),
                "bad": Proposition("bad", "bad", ("no",), ("good",)),
            },
            (Candidate("a", "a", ("bad",)), Candidate("b", "b", ("good",), -0.9)),
        )
        results = run_all_ablations(p)
        self.assertEqual({r.winner for r in results.values()}, {"b"})
        self.assertEqual(
            {r.candidate_results[0].status for r in results.values()}, {"destroyed"}
        )

    def test_store_does_not_expose_mutable_content(self):
        s = MerkleStore()
        payload = {"a": {"b": [1]}}
        cid = s.put("leaf", payload)
        payload["a"]["b"].append(2)
        s.get(cid).payload["a"]["b"].append(3)
        self.assertTrue(s.verify(cid))

    def test_reusing_solver_is_a_deterministic_cold_solve(self):
        p = Problem(
            "p",
            "?",
            {"e": Evidence("e", "e", 1, 1.0, "fixture")},
            {"p": Proposition("p", "p", ("e",))},
            (Candidate("c", "c", ("p",)),),
        )
        s = QIDSCAMSolver()
        first = s.solve(p)
        second = s.solve(p)
        self.assertEqual(first.proof_root, second.proof_root)
        self.assertEqual(first.metrics.deterministic(), second.metrics.deterministic())

    def test_duplicate_evidence_keys_rejected(self):
        value = {
            "problem_id": "p",
            "query": "?",
            "evidence": [{"key": "e", "text": "x", "stance": 1, "confidence": 1.0}] * 2,
            "propositions": [],
            "candidates": [],
        }
        with self.assertRaises(ValueError):
            Problem.from_dict(value)
