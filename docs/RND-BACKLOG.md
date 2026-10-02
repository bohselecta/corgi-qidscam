# Deferred R&D pass: a new strategy

Status: **QUEUED FOR LATER**, requested 2026-10-02. No new experiment has been
run, no runtime budget granted, and no improvement is asserted. This work does
not reopen or replace the 0.2.0 release evidence.

## Starting evidence

The frozen v2 suite reports 15 cases across five synthetic workloads and three
seeds, with seven configurations. Simple alias memoization is faster than full
QIDS-CAM in every recorded local timing row, while omitting hash/receipt work.
Unique and adverse-ordering cases do not reduce expansions. Turning off no-good
learning produces the same full expansion counts in every case. These results
must remain available, including the frozen historical v0.1 protocol/results.

## Proposed direction, still a hypothesis

Investigate an incremental, proof-producing strategy for repeated related
queries: separate reusable immutable graph construction from evaluation; build
a dependency index; invalidate affected states precisely when evidence or the
constraint context changes. Evaluate whether contradiction propagation and
amortized receipt construction help over exact memoization when changes are
sparse. Do not import trusted no-goods across contexts merely because their text
looks similar. Reuse requires verified provenance and exact semantic identity.

This direction changes the workload and cache lifecycle. Any success would be
specific to the newly declared setting, not a correction of the cold-run v2
results or evidence for quantum speedup. It may not outperform simpler methods.

## Protocol required before implementation experiments

- Version the new algorithm, protocol, inputs, seeds, run order, limits and
  discovery/holdout partitions. Freeze the holdout before tuning; log all
  attempted strategies and failures. Preserve v2 as a regression suite.
- Compare cold and amortized repeated-query runs against simple alias memo,
  dependency-indexed incremental memo, and the existing full solver. Include
  high sharing, sparse updates, widespread invalidation, context changes,
  unrelated graphs and adversarial hazard ordering.
- Match output and proof obligations. Give baselines equivalent receipt work,
  or report the receipt cost separately. Measure end-to-end latency, expanded
  propositions, hashing/receipt bytes, peak memory and invalidation overhead.
  Predeclare repetitions and report spread; retain every raw timing/failure.
- Require status/score/winner parity against a separate recomputation oracle,
  deterministic receipt verification, tamper rejection, stale-state rejection
  after evidence/config/context changes and bounded cache/resource usage.
- Define any success threshold before measurement. Publish null, adverse and
  inconclusive outcomes. Synthetic results remain synthetic; no corpus, model,
  human or production claim without corresponding authorized evidence.

Paid-runtime budget remains **$0**. Prefer deterministic local workloads. Any
provider calls, paid infrastructure or package/website publication require
explicit authorization. The R&D pass stays deferred while the numbered release
campaign continues; it is not an extra campaign job or a website change.
