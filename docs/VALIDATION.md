# Acceptance evidence — 0.2.0 candidate

Observed 2026-10-02 on Linux x86_64, Python 3.12.14. No paid runtime calls.
This record describes prepublication checks. The destination is
https://github.com/bohselecta/corgi-qidscam; its visibility, published commit and
post-push fresh-clone outcome are recorded in the campaign verification record.
No public tag or package-registry upload is included.

The original code passed 13 tests but failed four newly framed regressions:
local fatal contradictions changed winners between ablations; duplicate evidence
keys were overwritten; solver reuse changed roots; caller mutation changed
stored content. Separate random-DAG/empty-evidence checks subsequently exposed
missing evidence scored as positive local support. The derivative fixes these
rather than weakening the acceptance checks.

Current automated checks include original tests, those regressions, random DAGs
(60 seeds x five optimized configurations against separate reference), context
isolation, full alias renaming, malformed types/nonfinite/duplicate inputs,
cycle/depth rejection, immutable store, atomic failure preservation, missing
files, subprocess demo/archive/verify/inspect, altered input/state/trace/context,
orphan/missing DAG records and self-consistent forged-winner replay rejection.
Terminal control/bidi escape and resource-budget tests supplement them.

The declared v2 synthetic suite has 15 cases x seven configurations, all retained
in `results/suite-v2.json`, with candidate status/score/winner parity and repeated
root/work-count determinism. Timing includes full QIDS receipt/hash work but
simple reference baselines omit it. The latter are faster in every local
measured row. Unique/adverse cases tie on expansions. Disabling no-good learning
does not alter full expansion counts. These are valid unfavorable/null outcomes.

`python3 scripts/release_gate.py` reruns behavior checks, checks committed suite
roots/counts against recomputation, verifies the demo receipt, checks the wheel
against package source and checksum, and checks release-file boundaries.
Clean-clone + clean-venv offline install is recorded in the campaign evidence;
that is a local publication-candidate clone, not a public GitHub-clone result.
No second OS, real model, real corpus, human evaluator, production cost claim or
service deployment has been verified in these checks. Historical source results are retained
byte-for-byte, not claimed as new measurements.

Hash integrity is independent of solver execution. Semantic replay uses the
release solver plus a separately expressed reference evaluator; neither is an
externally audited formal proof system. Test evidence is builder-run; no external
reviewer or human acceptance is implied. The distinct acceptance pass attempted
to falsify parity, data integrity and safe failures with separate cases.

## Browser/product-preservation repair

Observed on the same Linux/Python 3.12.14 environment: 39 Python tests, all 105
frozen synthetic rows, both receipt-derived browser exports, a clean isolated
wheel install and installed CLI-to-HTML export pass. Browser acceptance with
Chromium checks alias merging, actual destroyed/surviving states, candidate
requirements/skips, event/selected-node filtering, keyboard trace controls,
archive download followed by an independent Python process, mobile (390px),
empty graphs, hostile HTML strings, and real no-good hits in the high-sharing
fixture. No external browser requests or runtime errors occurred.

The Python/JavaScript float-spelling mismatch was caught by verifying the
downloaded archive, then fixed by preserving the Python serialization.
Malformed/tampered export and input-overwrite attempts leave previous data safe.
Desktop and mobile screenshots were visually inspected; mobile page overflow
was corrected while preserving an internally scrollable graph.

Build/check: wheel and sdist pass Twine metadata checks. Same-toolchain repeat
builds have identical SHA-256 checksums; tar/gzip metadata are normalized.
The historical Markdown report, manuscript and bibliography were retained with
explicit v0.1 boundaries and checksums; TeX compilation is NOT RUN.

Hosted Python 3.10–3.14 and browser CI are configured but NOT RUN on this repair
until publication approval. No real-model study, empirical RAG/corpus result,
new public release or external human review is inferred from these checks.
