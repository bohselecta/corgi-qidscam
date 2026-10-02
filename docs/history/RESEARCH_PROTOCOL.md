# QIDS-CAM v0.1.0 Frozen Research Protocol

**Protocol status:** frozen for the v0.1.0 reference result  
**Originator and research director:** Hayden Lindley  
**Implementation license:** Apache-2.0

## 1. Research question

Does combining destructive pruning with exact content-addressed proposition identity reduce repeated proposition evaluation in a graph-shaped reasoning workload, beyond either mechanism alone, while preserving the selected answer?

## 2. Hypothesis

For candidate-search workloads containing repeated proposition subgraphs and repeated fatal contradictions, full QIDS-CAM will perform fewer proposition expansions than:

1. independent exhaustive evaluation;
2. destructive pruning without content-addressed memory.

The expected benefit should increase as candidate count grows while the number of unique shared subgraphs grows more slowly.

## 3. Tested system

Algorithm version: `0.1.0`

Default parameters:

```text
destroy_below      = -0.20
uncertain_band     =  0.08
dependency_weight  =  0.65
phase aggregation  = enabled
fail-first          = enabled in destructive configurations
```

## 4. Benchmark generator

The benchmark is deterministic under a seed. The frozen reference seed is `7`.

It creates:

- reusable positively supported leaf propositions;
- reusable positively supported composite modules;
- a smaller set of trap leaves with weak support and two strong opposing observations;
- trap modules that depend on one trap leaf and two good leaves;
- one expected winning candidate containing only good modules;
- many losing candidates containing several good modules plus one shared trap module.

The trap requirement appears last in input order. A destructive solver must use its hazard ordering to move likely failure toward the front.

## 5. Frozen scales

| Scale | Candidates | Good leaves | Good modules | Trap groups | Requirements per candidate |
|---|---:|---:|---:|---:|---:|
| small | 16 | 16 | 8 | 3 | 4 |
| medium | 128 | 48 | 24 | 8 | 7 |
| large | 1,024 | 96 | 48 | 16 | 9 |

## 6. Ablations

### A. Independent exhaustive

- content-addressed memoization disabled;
- destructive pruning disabled;
- learned no-goods disabled;
- fail-first disabled;
- every occurrence is reevaluated.

### B. Destructive only

- content-addressed memoization disabled;
- destructive pruning enabled;
- learned no-goods disabled;
- fail-first enabled.

### C. Merkle memory only

- content-addressed memoization enabled;
- destructive pruning disabled;
- learned no-goods disabled;
- fail-first disabled.

### D. Full QIDS-CAM

- content-addressed memoization enabled;
- destructive pruning enabled;
- learned no-goods enabled;
- fail-first enabled.

Signed/phase-aware evidence aggregation remains enabled in all configurations so the ablation isolates search and memory behavior rather than changing the evidence semantics.

## 7. Primary metric

`proposition_expansions`: the number of times a proposition is evaluated after cache/no-good checks.

This is a deterministic work count and the primary comparison measure.

## 8. Secondary metrics

- `evidence_reads`
- `memo_hits`
- `nogood_hits`
- `learned_nogoods`
- `early_prunes`
- `avoided_requirements`
- `candidate_evaluations`
- `unique_merkle_nodes`
- answer parity
- proof-root reproducibility

`elapsed_ms` is recorded for local diagnostics but is not a primary result and must not be generalized across machines.

## 9. Correctness gates

A benchmark run passes only when:

1. every configuration selects `candidate_0000`;
2. `answer_parity` is true;
3. every generated proof DAG recursively verifies;
4. repeated execution with identical input/configuration produces identical problem and proof roots;
5. archive import rejects modified node content or a mismatched claimed CID.

## 10. Reference commands

```bash
python -m unittest discover -s tests -v
python scripts/run_benchmarks.py
python -m qids_cam benchmark --scale small  --seed 7
python -m qids_cam benchmark --scale medium --seed 7
python -m qids_cam benchmark --scale large  --seed 7
python -m qids_cam demo --archive results/demo-proof.json
python -m qids_cam verify results/demo-proof.json
```

## 11. Frozen reference outcomes

| Scale | Exhaustive | Destructive only | Merkle only | QIDS-CAM | vs exhaustive | vs destructive | Parity |
|---|---:|---:|---:|---:|---:|---:|---:|
| small | 256 | 76 | 30 | 22 | 11.6364× | 3.4545× | pass |
| medium | 3,584 | 536 | 88 | 51 | 70.2745× | 10.5098× | pass |
| large | 36,864 | 4,128 | 176 | 88 | 418.9091× | 46.9091× | pass |

Machine-readable outputs are stored in `results/benchmark-*.json`.

## 12. Interpretation rules

Permitted statements:

- The implementation demonstrates reusable destruction over exact content-addressed proposition identity.
- On the frozen synthetic suite, QIDS-CAM preserved answer parity and reduced proposition expansions relative to the named ablations.
- The increasing expansion ratio is consistent with the benchmark’s designed increase in repeated subgraph reuse.

Statements not supported by this protocol:

- QIDS-CAM provides quantum speedup.
- QIDS-CAM is faster on all RAG or agent workloads.
- Merkle hashing provides semantic similarity.
- The selected answer is guaranteed factually true.
- The benchmark proves production cost savings.
- The benchmark establishes a new complexity class.

## 13. Threats to validity

- The benchmark is synthetic and deliberately contains reusable structure.
- The hazard heuristic is aligned with the planted contradiction pattern.
- Evidence labels/confidences are generated, not produced by a noisy real classifier.
- Model-token and retrieval costs are not represented in v0.1.0.
- Only one frozen seed is used for the reference table, though the generator supports other seeds.
- Memory and no-good lookup are in-process dictionary operations.

## 14. Required next validation

A credible external evaluation should add at least one public dataset with:

- repeated multi-hop claims or contradictory evidence;
- a fixed retrieval corpus and candidate-generation procedure;
- calibrated answer quality metrics;
- token/model-call accounting;
- wall-clock reporting across multiple runs and machines;
- all four ablations;
- a predeclared exclusion rule for malformed or cyclic problem graphs;
- independent reproduction from a tagged release.

## 15. Change control

Changes to benchmark topology, thresholds, scoring, identity semantics, or ablation definitions require a new protocol version. Prior result files must remain available and must not be silently regenerated under changed semantics.
