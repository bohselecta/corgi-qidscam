# Mechanism positioning — checked 2026-10-02

Current public repository READMEs were retrieved for
[Kubo](https://github.com/ipfs/kubo), [PySAT](https://github.com/pysathq/pysat),
and [Z3](https://github.com/Z3Prover/z3). Kubo describes verifiable content
addressing/DAG transfer. PySAT exposes mature SAT oracles with incremental solver
technology. Z3 provides a mature theorem-proving/SMT toolchain. No code or assets
from these projects are imported. A metadata query for the old microsoft/Z3
path returned 404; the current Z3Prover/z3 README was read successfully.

These established mechanisms remain useful. QIDS-CAM contributes a compact
inspectable *combination* for supplied signed evidence DAGs, reusable
context-bound destructive states and replayable receipts. It does not replace
SAT/SMT, provide probabilistic calibration, invent content addressing or prove
novelty. Its hash codec is not an interoperable IPFS CID codec. Similarity-based
semantic memory and calibrated real-corpus RAG evaluation remain outside scope.

The strongest current positioning is an offline experimental instrument:
compare graph reuse/pruning against simple baselines and inspect exactly what
happened. The suite's neutral/adverse results and slower simple-baseline timing
are part of that instrument's output. Historical prior-art framing remains in
`docs/history/PRIOR_ART.md`; any historical novelty language is an unproven
research proposition, not this release's claim.
