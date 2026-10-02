# Architecture — 0.2.0

The graph is a validated DAG. Local aliases are excluded from evidence and
proposition semantic payloads; dependency/evidence CID lists are sorted, and
outbound DAG links are sorted/deduplicated. Semantically identical aliases
share resolved computation. Input aliases are retained separately in the receipt.

Local score is the confidence-weighted real component of supplied phase vectors
(default phase 0 for supporting and pi for opposing stance), divided by total
weight. No weight means score 0. Scores at/below -0.20 are destroyed; absolute
score at/below .08 is uncertain. Evidence-plus-dependency score uses dependency
weight .65; dependency-only score is their mean. Fatal local contradiction and
any destroyed dependency are fatal in all modes. Candidate score is mean
required score plus prior, clamped to [-1,1]; destroyed requirement yields -1.
Max (score, candidate key) selects the surviving/uncertain winner.

Destructive mode avoids descendants after local failure and requirements after
a failed requirement. Stance-based hazard ordering is a heuristic and can be
adverse when explicitly supplied phases disagree with stance. Memo/no-good keys
bind proposition CID, context CID and full configuration CID. Both caches start
empty on every solve; learned no-goods last for that run. There is no warm-cache
claim or unverified persisted-negative-state API in this release.

A context is identity/provenance, not a constraint language. Scoring receives
only the graph and configuration. Evaluation precisions and the codec are in
the portable format. Receipt roots include deterministic work counts and trace;
wall time stays outside the proof. Different strategies produce different roots
because their executions differ even when their answer matches.

`MerkleStore` copies content on insertion and retrieval. Its independent hash
checker iteratively checks all reachable links and rejects cycles/missing data.
The import boundary requires exact schema fields and a complete reachable DAG.
The solve-proof verifier checks context binding, deterministic replay and a
separately expressed simple alias-memoized reference. The reference shares data
and parameter types, but has its own traversal/scoring implementation and no
CID compilation, pruning, no-good learning or receipt creation.

CLI inspection is deliberately text-based. It needs no browser, JavaScript or
web server and displays actual validated archives. Both user-requested result
and archive writes are atomic individually; a result/archive pair is not a
multi-file transaction. On a later write failure, an earlier valid output may
remain and can be independently checked.
