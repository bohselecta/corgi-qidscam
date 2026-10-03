# QIDS-CAM 0.2.0

Evaluate contradiction-aware evidence graphs and inspect their portable receipts
in an offline browser. Shared aliases resolve to one proposition identity;
destroyed prerequisites propagate through candidate paths; the retained trace
shows exactly when states were resolved, reused and pruned.

Includes a zero-dependency Python library/CLI, strict v2 archive verification,
separate reference evaluator, reproducible synthetic benchmarks, historical
research artifacts and an accessible browser explorer. The five-workload suite
retains all 105 rows, neutral/unfavorable results and the null effect of no-good
learning on cold-run expansion counts. No real-model or production study is run.

Artifacts: `qids_cam-0.2.0-py3-none-any.whl`, `qids_cam-0.2.0.tar.gz`, `SHA256SUMS`.
Build with `python3 scripts/build_release.py` using setuptools 84.0.0 and wheel;
check with `python3 scripts/release_gate.py`. Repeating the build in the same
toolchain produces identical asset checksums. The bundled wheel permits offline
installation; the GitHub Release is the versioned distribution lifecycle.

Python 3.10+; Python 3.10–3.14 are hosted CI targets. Only actually executed
platform/toolchain combinations belong in the acceptance evidence. Browser
verification tooling is optional for development. No provider API or package
registry upload is required. Apache-2.0, original Hayden Lindley attribution;
publisher Corgi-verse Software.
