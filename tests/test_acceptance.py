"""Falsification cases framed around promises, not the implementation branches."""

import copy
import hashlib
import json
import random
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from qids_cam import (
    Candidate,
    Evidence,
    MerkleStore,
    Problem,
    Proposition,
    QIDSCAMSolver,
    verify_archive,
)
from qids_cam.io import load, loads, write_json
from qids_cam.reference import evaluate
from qids_cam.solver import SolverConfig
from qids_cam.suite import CONFIGS, WORKLOADS, workload

ROOT = Path(__file__).resolve().parents[1]


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.problem = Problem.load(ROOT / "examples/outage-investigation.json")
        self.result = QIDSCAMSolver().solve(self.problem)
        self.archive = self.result.store.export_archive(self.result.proof_root)

    def test_separate_reference_on_random_dags(self):
        for seed in range(60):
            rng = random.Random(seed)
            es = {}
            ps = {}
            for i in range(14):
                key = f"p{i}"
                keys = []
                for j in range(rng.randrange(4)):
                    e = f"e{i}_{j}"
                    keys.append(e)
                    es[e] = Evidence(
                        e,
                        e,
                        rng.choice((-1, 1)),
                        rng.random(),
                        "synthetic",
                        rng.choice((None, 0.0, 60.0, 180.0, 270.0)),
                    )
                dependencies = tuple(
                    rng.sample(list(ps), min(len(ps), rng.randrange(4)))
                )
                ps[key] = Proposition(key, key, tuple(keys), dependencies)
            cs = tuple(
                Candidate(
                    f"c{i}",
                    f"c{i}",
                    tuple(rng.sample(list(ps), 4)),
                    rng.uniform(-0.4, 0.4),
                )
                for i in range(6)
            )
            p = Problem(f"random-{seed}", "?", es, ps, cs)
            oracle = evaluate(p, memoized=True)
            for config in CONFIGS:
                r = QIDSCAMSolver(config).solve(p)
                self.assertEqual(r.winner, oracle["winner"], (seed, config.name))
                for got, want in zip(r.candidate_results, oracle["outcomes"]):
                    self.assertEqual(
                        (got.key, got.status), want[:2], (seed, config.name)
                    )
                    self.assertAlmostEqual(got.score, want[2], places=10)

    def test_self_consistent_forged_winner_fails_replay(self):
        a = copy.deepcopy(self.archive)
        old = a["root"]
        node = a["nodes"].pop(old)
        node["payload"]["winner"] = "database_failure"
        # Independently recompute this node's valid hash; hash-only must pass,
        # whereas execution verification must reject the forged semantic claim.
        raw = json.dumps(
            node, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        new = "sha256:" + hashlib.sha256(b"qids-cam-node-v1\0" + raw).hexdigest()
        a["root"] = new
        a["nodes"][new] = node
        MerkleStore.from_archive(a)
        with self.assertRaisesRegex(ValueError, "replay mismatch"):
            verify_archive(a)

    def test_tampered_trace_and_missing_links_fail(self):
        for field in ("trace", "states", "input", "context_node"):
            a = copy.deepcopy(self.archive)
            cid = a["nodes"][a["root"]]["payload"][field]
            a["nodes"][cid]["payload"]["unexpected"] = True
            with self.assertRaises(ValueError):
                verify_archive(a)
        a = copy.deepcopy(self.archive)
        del a["nodes"][a["root"]]
        with self.assertRaises(ValueError):
            MerkleStore.from_archive(a)

    def test_unreachable_nodes_and_schema_ambiguity_fail(self):
        a = copy.deepcopy(self.archive)
        s = MerkleStore()
        cid = s.put("unrelated", {"x": 1})
        a["nodes"][cid] = s.get(cid).as_record()
        with self.assertRaisesRegex(ValueError, "unreachable"):
            MerkleStore.from_archive(a)
        for change in (
            lambda a: a.update(extra=1),
            lambda a: a["nodes"][a["root"]].update(schema="unknown"),
            lambda a: a.update(root=[]),
        ):
            a = copy.deepcopy(self.archive)
            change(a)
            with self.assertRaises(ValueError):
                MerkleStore.from_archive(a)

    def test_cycle_and_deep_graph_are_rejected(self):
        v = self.problem.to_dict()
        v["propositions"][0]["depends_on"] = [v["propositions"][0]["key"]]
        with self.assertRaisesRegex(ValueError, "cycle"):
            Problem.from_dict(v)
        ps = {
            f"p{i}": Proposition(
                f"p{i}", f"p{i}", depends_on=(f"p{i - 1}",) if i else ()
            )
            for i in range(129)
        }
        with self.assertRaisesRegex(ValueError, "depth"):
            Problem("deep", "?", {}, ps, ())
        # A corrupted in-memory cycle must fail without recursive overflow.
        s = MerkleStore()
        a = s.put("a", {})
        b = s.put("b", {}, (a,))
        s._nodes[a] = replace(s._nodes[a], links=(b,))
        self.assertFalse(s.verify(b))

    def test_strict_types_duplicates_and_nonfinite(self):
        invalid = [True, "1", float("nan"), float("inf")]
        for value in invalid:
            with self.assertRaises(ValueError):
                Evidence("e", "x", 1, value, "s")
        with self.assertRaises(ValueError):
            Evidence("e", "x", True, 0.5, "s")
        with self.assertRaises(ValueError):
            Evidence("e", "x", 1, 0.5, "s", float("inf"))
        with self.assertRaises(ValueError):
            SolverConfig("bad", dependency_weight=2)
        for text in ('{"x":1,"x":2}', '{"x":NaN}', "[[[[[[[[[[[[[[[bad"):
            with self.assertRaises(ValueError):
                loads(text)
        v = self.problem.to_dict()
        v["candidates"].append(v["candidates"][0])
        with self.assertRaises(ValueError):
            Problem.from_dict(v)

    def test_context_bound_nogoods_and_no_stale_problem(self):
        p = workload("high-sharing", 7)
        s = QIDSCAMSolver()
        a = s.solve(p, constraints={"scope": "A"})
        b = s.solve(p, constraints={"scope": "B"})
        self.assertGreater(a.metrics.nogood_hits, 0)
        self.assertEqual(a.metrics.deterministic(), b.metrics.deterministic())
        self.assertNotEqual(a.proof_root, b.proof_root)
        # A different graph under the same alias cannot reuse the prior result.
        c = s.solve(self.problem, constraints={"scope": "A"})
        self.assertEqual(
            c.proof_root,
            QIDSCAMSolver().solve(self.problem, constraints={"scope": "A"}).proof_root,
        )

    def test_alias_renaming_preserves_proposition_identity(self):
        v = self.problem.to_dict()
        mapping = {x["key"]: "renamed_" + x["key"] for x in v["propositions"]}
        for x in v["propositions"]:
            x["key"] = mapping[x["key"]]
            x["depends_on"] = [mapping[k] for k in x["depends_on"]]
        for c in v["candidates"]:
            c["requires"] = [mapping[k] for k in c["requires"]]
        a = QIDSCAMSolver().compile(self.problem)
        b = QIDSCAMSolver().compile(Problem.from_dict(v))
        for key, cid in a.proposition_cids.items():
            self.assertEqual(cid, b.proposition_cids[mapping[key]])

    def test_atomic_failed_write_preserves_previous_result(self):
        with TemporaryDirectory() as directory:
            p = Path(directory) / "receipt.json"
            p.write_text("previous")
            with patch(
                "qids_cam.io.os.replace", side_effect=OSError("simulated interruption")
            ):
                with self.assertRaises(OSError):
                    write_json(p, {"new": True})
            self.assertEqual(p.read_text(), "previous")
            self.assertEqual(list(Path(directory).iterdir()), [p])

    def test_empty_unknown_and_all_destroyed_are_honest(self):
        self.assertIsNone(
            QIDSCAMSolver().solve(Problem("empty", "?", {}, {}, ())).winner
        )
        p = Problem(
            "uncertain",
            "?",
            {},
            {"p": Proposition("p", "no evidence")},
            (Candidate("c", "c", ("p",)),),
        )
        r = QIDSCAMSolver().solve(p)
        self.assertEqual(r.candidate_results[0].status, "uncertain")
        self.assertEqual(
            r.winner, "c"
        )  # unresolved candidates can rank; not a truth assertion
        p = Problem(
            "dead",
            "?",
            {"e": Evidence("e", "no", -1, 1.0, "s")},
            {"p": Proposition("p", "p", ("e",))},
            (Candidate("c", "c", ("p",)),),
        )
        self.assertIsNone(QIDSCAMSolver().solve(p).winner)

    def test_subprocess_golden_path_and_failure_recovery(self):
        with TemporaryDirectory() as directory:
            archive = Path(directory) / "proof.json"
            for args in (
                ["demo", "--archive", str(archive)],
                ["verify", str(archive)],
                ["inspect", str(archive), "--json"],
            ):
                r = subprocess.run(
                    [sys.executable, "-m", "qids_cam", *args],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(r.returncode, 0, r.stderr)
            archive.write_text('{"broken":true}')
            r = subprocess.run(
                [sys.executable, "-m", "qids_cam", "verify", str(archive)],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(r.returncode, 2)
            self.assertNotIn("Traceback", r.stderr)
            r = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "qids_cam",
                    "solve",
                    str(archive.parent / "missing.json"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(r.returncode, 2)
            self.assertNotIn("Traceback", r.stderr)

    def test_json_exponent_overflow_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite range"):
            loads('{"weight":1e999}')

    def test_resource_budgets_fail_before_overwrite(self):
        with patch("qids_cam.solver.MAX_EXPANSIONS", 1):
            with self.assertRaisesRegex(ValueError, "expansion budget"):
                QIDSCAMSolver().solve(self.problem)
        with TemporaryDirectory() as directory:
            target = Path(directory) / "large.json"
            target.write_text('{"payload":"too large"}')
            with patch("qids_cam.io.MAX_BYTES", 8):
                with self.assertRaisesRegex(ValueError, "limit"):
                    load(target)
                with self.assertRaisesRegex(ValueError, "limit"):
                    write_json(target, {"new": "too large"})
            self.assertEqual(target.read_text(), '{"payload":"too large"}')
        with patch("qids_cam.merkle.MAX_NODES", 1):
            store = MerkleStore()
            store.put("leaf", {})
            with self.assertRaisesRegex(ValueError, "node limit"):
                store.put("other", {})

    def test_numeric_field_spelling_and_candidate_metrics(self):
        p1 = Problem(
            "same",
            "?",
            {"e": Evidence("e", "yes", 1, 1, "s")},
            {"p": Proposition("p", "p", ("e",))},
            (Candidate("c", "c", ("p",), 0),),
        )
        p2 = Problem(
            "same",
            "?",
            {"e": Evidence("e", "yes", 1, 1.0, "s")},
            {"p": Proposition("p", "p", ("e",))},
            (Candidate("c", "c", ("p",), 0.0),),
        )
        self.assertEqual(
            QIDSCAMSolver().solve(p1).proof_root, QIDSCAMSolver().solve(p2).proof_root
        )
        p = Problem(
            "prior",
            "?",
            {},
            {"p": Proposition("p", "p")},
            (Candidate("c", "c", ("p",), -0.5),),
        )
        result = QIDSCAMSolver().solve(p)
        self.assertEqual(result.metrics.destroyed_candidates, 1)
        self.assertIsNone(result.winner)

    def test_terminal_evidence_is_escaped(self):
        from qids_cam.io import terminal_text

        self.assertEqual(
            terminal_text("evil\x1b[2J\n\u202e"), "evil\\u001b[2J\\u000a\\u202e"
        )

    def test_new_workloads_do_not_require_an_advantage(self):
        for name in WORKLOADS:
            p = workload(name, 7)
            ref = evaluate(p, memoized=True)
            full = QIDSCAMSolver().solve(p)
            self.assertEqual(full.winner, ref["winner"])
            if name in ("unique-no-contradiction", "adverse-ordering"):
                self.assertEqual(
                    full.metrics.proposition_expansions, ref["proposition_expansions"]
                )
