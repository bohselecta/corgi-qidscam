from __future__ import annotations

import copy
import io
import json
import re
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from qids_cam.cli import main
from qids_cam.explorer import explorer_data, render_explorer
from qids_cam.schema import Problem
from qids_cam.solver import QIDSCAMSolver

ROOT = Path(__file__).resolve().parents[1]


class ExplorerTests(unittest.TestCase):
    def setUp(self):
        self.archive = json.loads((ROOT / "results/demo-proof.json").read_text())

    def test_original_archive_aliases_dependencies_and_states_are_retained(self):
        data = explorer_data(self.archive)
        self.assertEqual(data["archive"], self.archive)
        self.assertEqual(json.loads(data["archive_json"]), self.archive)
        self.assertIn('"score": 1.0', data["archive_json"])
        aliases = next(p for p in data["propositions"] if "database_healthy_alias" in p["aliases"])
        self.assertEqual(aliases["aliases"], ["database_healthy", "database_healthy_alias"])
        self.assertEqual(aliases["resolved"]["status"], "survives")
        p = data["archive"]["nodes"][aliases["cid"]]
        self.assertEqual(aliases["dependencies"], p["payload"]["dependencies"])
        self.assertEqual(aliases["evidence"], p["payload"]["evidence"])
        self.assertIn("independent reference", data["verification_at_export"])
        self.assertEqual(len(data["propositions"]), 11)
        self.assertEqual(len(data["trace"]), 35)

    def test_tampering_fails_before_an_existing_output_is_replaced(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "archive.json"
            output = Path(directory) / "explorer.html"
            output.write_text("previous good export")
            tampered = copy.deepcopy(self.archive)
            tampered["nodes"][tampered["root"]]["payload"]["winner"] = "forged"
            source.write_text(json.dumps(tampered))
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(["explore", str(source), "--output", str(output)])
            self.assertEqual(output.read_text(), "previous good export")

    def test_hostile_evidence_remains_inert_json_and_preserves_download(self):
        original = json.loads((ROOT / "examples/outage-investigation.json").read_text())
        hostile = '</script><script>globalThis.pwned=true</script><img src=x onerror=alert(1)>'
        original["query"] = hostile
        result = QIDSCAMSolver().solve(Problem.from_dict(original))
        archive = result.store.export_archive(result.proof_root)
        html = render_explorer(archive)
        self.assertNotIn(hostile, html)
        embedded = re.search(r'<script id="receipt-data" type="application/json">(.*?)</script>', html, re.S)
        self.assertEqual(json.loads(embedded.group(1))["archive"], json.loads(json.dumps(archive)))
        self.assertEqual(json.loads(embedded.group(1))["problem"]["query"], hostile)
        self.assertIn("connect-src 'none'", html)
        self.assertNotIn("<script src=", html)

    def test_empty_graph_is_a_valid_explorer_and_unevaluated_is_not_surviving(self):
        problem = Problem.from_dict({"problem_id": "empty", "query": "No candidates",
                                     "evidence": [], "propositions": [], "candidates": []})
        result = QIDSCAMSolver().solve(problem)
        data = explorer_data(result.store.export_archive(result.proof_root))
        self.assertEqual(data["propositions"], [])
        self.assertEqual(data["proof"]["winner"], None)

    def test_output_cannot_destroy_input_archive(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "archive.json"
            source.write_text(json.dumps(self.archive))
            before = source.read_bytes()
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(["explore", str(source), "--output", str(source)])
            self.assertEqual(source.read_bytes(), before)

    def test_export_is_deterministic_and_visualization_is_bounded(self):
        self.assertEqual(render_explorer(self.archive), render_explorer(self.archive))
        oversized = {"nodes": {str(i): {} for i in range(5001)}}
        with self.assertRaisesRegex(ValueError, "5000"):
            explorer_data(oversized)
        with TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            path = Path(directory) / "explorer.html"
            self.assertEqual(main(["explore", str(ROOT / "results/demo-proof.json"),
                                   "--output", str(path)]), 0)
            self.assertIn("One identity", path.read_text())
