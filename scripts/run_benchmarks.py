"""Run the complete frozen v2 synthetic protocol, with all unfavorable rows."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qids_cam.io import write_json
from qids_cam.suite import run_suite

value = run_suite()
write_json(Path(__file__).resolve().parents[1] / "results/suite-v2.json", value)
for row in value["cases"]:
    r = row["runs"]
    print(
        f"{row['workload']:<24} seed={row['seed']:2} reference={r['simple-reference']['proposition_expansions']:5} alias-memo={r['simple-alias-memoized']['proposition_expansions']:4} full={r['qids-cam']['proposition_expansions']:4} parity={all(x['parity'] for x in r.values())}"
    )
if not value["parity"] or not value["deterministic"]:
    raise SystemExit(1)
