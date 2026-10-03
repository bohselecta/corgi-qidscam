"""Regenerate browser examples from actual verified v2 archives."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from qids_cam.explorer import render_explorer
from qids_cam.io import load, write_json, write_text
from qids_cam.solver import QIDSCAMSolver
from qids_cam.suite import workload

write_text(ROOT / "docs/explorer.html", render_explorer(load(ROOT / "results/demo-proof.json")))
result = QIDSCAMSolver().solve(workload("high-sharing", 7))
archive = result.store.export_archive(result.proof_root)
write_json(ROOT / "results/reuse-proof.json", archive)
write_text(ROOT / "docs/reuse-explorer.html", render_explorer(archive))
print("Exported outage and frozen high-sharing/seed-7 receipt explorers.")
