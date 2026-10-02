# Frozen synthetic evaluation protocol — v2

Frozen 2026-10-02 before new workload measurements. Algorithm 0.2.0.
Historical v0.1 protocol and results remain unchanged under `docs/history/` and
`results/history/`. A local fatal contradiction now remains fatal in exhaustive
modes as well as pruning modes. No observations means neutral local score 0, never positive evidence. Proofs bind the input and trace. Consequently v2
roots must not be compared as if they were historical v0.1 roots.

Hypothesis: exact repeated graph content plus destructive pruning reduces
proposition evaluations relative to exhaustive and destructive-only traversal
when contradictory subgraphs recur. Low reuse/contradiction weakens this benefit.
A simple memoized evaluator may match evaluations at much lower runtime cost.
No-goods may add no work reduction beyond caching destroyed states.

Fixed seeds: 7, 19, 41. No holdout, human or model data. All are synthetic,
labelled confidence/phase fixtures; supplied observations are not calibrated.
Five workloads: historical medium high-sharing topology; low sharing (32
candidates each with four unique requirements, one locally contradicted
requirement per third candidate); low contradiction (four shared groups, only
one group has one contradicted requirement); unique/no contradiction; adverse
ordering (each candidate has one fatal positive-stance/180-degree observation
first, three surviving negative-stance/0-degree observations after it, so the
stance hazard heuristic orders the actual failure last).

Configurations: four historical search/memory ablations with corrected common
semantics; full without learned no-goods as an additional diagnostic; independent
simple recursive evaluator; simple alias-memoized evaluator. The latter two omit
CID compilation and receipts, an explicit runtime work-boundary difference.
All modes share evidence semantics, thresholds and priors. Primary metrics:
proposition expansions and candidate status/score/winner parity. Scores compared
at absolute tolerance 1e-10 (defined before measurements). Work counts and roots
repeat exactly. The reference evaluator is independently expressed, not a new
instance of the optimized recursion.

One complete end-to-end execution per case/config records wall-clock time, and
one repeated execution checks deterministic counts and roots. Runtime is local
single-run diagnostic evidence, not a statistical speed claim; generation is
excluded, compilation/trace/receipt/internal hash checking included for QIDS
modes. All seeds/configurations are retained. No performance pass threshold.
Receipt verification uses fresh-process replay plus the separate reference.
Future real corpus evaluations need a separate frozen protocol.
