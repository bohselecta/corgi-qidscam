# QIDS-CAM Architecture

## 1. Purpose

QIDS-CAM is a reference architecture for classical destructive reasoning over a content-addressed directed acyclic graph. It separates three concerns that are often collapsed in AI systems:

1. **Identity:** What exact evidence, proposition, candidate, or solve result is this?
2. **Resolution:** Does the state survive support/opposition and dependency constraints?
3. **Search:** Which state should be expanded next, and what can be pruned?

The Merkle layer answers the first question. The destructive solver answers the second and third.

## 2. System layers

```text
┌─────────────────────────────────────────────────────────────┐
│ Application adapter                                         │
│ RAG, incident analysis, planning, theorem search, diagnosis │
└───────────────────────┬─────────────────────────────────────┘
                        │ Problem schema
┌───────────────────────▼─────────────────────────────────────┐
│ Compilation layer                                           │
│ canonical JSON → evidence CIDs → proposition DAG → root CID │
└───────────────────────┬─────────────────────────────────────┘
                        │ CompiledProblem
┌───────────────────────▼─────────────────────────────────────┐
│ Destructive reasoning layer                                 │
│ signed aggregation → fail-first → dependency destruction    │
│ → candidate pruning → winner selection                      │
└───────────────────────┬─────────────────────────────────────┘
                        │ Resolved states
┌───────────────────────▼─────────────────────────────────────┐
│ Persistent computation layer                                │
│ CID memo cache + context-bound no-good cache                 │
└───────────────────────┬─────────────────────────────────────┘
                        │ Results and links
┌───────────────────────▼─────────────────────────────────────┐
│ Verification layer                                          │
│ candidate-result nodes → solve-proof root → archive verify  │
└─────────────────────────────────────────────────────────────┘
```

## 3. Domain schema

### Evidence

An evidence object contains:

- a local key used only by the input document;
- human-readable text;
- stance `+1` or `-1`;
- confidence in `[0, 1]`;
- a source identifier;
- an optional phase angle in degrees;
- optional tags.

Evidence identity is derived from all semantic fields except the input key.

### Proposition

A proposition contains:

- a statement;
- zero or more evidence references;
- zero or more proposition dependencies;
- metadata.

The input alias is deliberately omitted from the hashed payload. Two aliases compile to one CID when their semantic content and linked CIDs are identical.

### Candidate

A candidate hypothesis contains:

- a label;
- a list of required proposition CIDs;
- an optional prior.

A candidate is destroyed when any required proposition is destroyed. Otherwise its score is the bounded prior plus the mean requirement score.

### Problem

A problem contains the query, candidate CIDs, metadata, and its own root CID. The schema rejects missing references and proposition cycles before solving.

## 4. Canonical identity

The reference content identifier is:

```text
CID = "sha256:" + SHA256(namespace || NUL || canonical_json(value))
```

Canonical JSON has these rules:

- object keys are sorted;
- separators contain no insignificant whitespace;
- UTF-8 is used directly;
- sets are canonicalized by element serialization order;
- negative zero becomes zero;
- NaN and infinity are rejected;
- mapping keys must be strings.

This format is intentionally small and inspectable. It is not claimed to be a full IPLD codec. A production backend may substitute DAG-CBOR/CIDv1 while preserving the semantic hashing contract.

## 5. Merkle-DAG store

`MerkleStore.put(kind, payload, links)`:

1. deduplicates and sorts outbound links;
2. hashes `{schema, kind, payload, links}`;
3. checks for impossible same-CID/different-record collisions;
4. stores one immutable node per CID;
5. returns the CID.

The store supports:

- lookup by CID;
- recursive re-hash verification;
- reachable-subgraph enumeration;
- portable JSON archive export;
- strict archive import and root verification.

The current implementation is in memory. The interface can be mapped to IPFS, an object store, SQLite, PostgreSQL, RocksDB, or a distributed CAS.

## 6. Evidence aggregation

For evidence item `j` with confidence `w_j` and phase `θ_j`, the local complex amplitude is:

```text
A = Σ_j w_j · exp(iθ_j)
```

By default:

- supporting evidence uses phase `0`;
- opposing evidence uses phase `π`;
- explicit adapter-supplied phases override the default.

The local score is the normalized real residual:

```text
local_score = clamp(Re(A) / Σ_j w_j, -1, 1)
```

Coherence is recorded for inspection:

```text
coherence = |A| / Σ_j w_j
```

This is ordinary classical vector arithmetic. It is described as interference-inspired because opposing vectors can cancel; it is not a quantum-state simulation.

## 7. Destructive proposition evaluation

For proposition `p`:

1. Compute `(p.CID, constraint_context.CID)`.
2. Return a learned no-good immediately when present.
3. Otherwise return a memoized result when present.
4. Count an expansion and aggregate local evidence.
5. If the local score is already below `destroy_below`, destroy before expanding dependencies.
6. Otherwise order dependencies by estimated hazard when fail-first is enabled.
7. Recursively resolve dependencies.
8. If any dependency is destroyed, destroy `p` and record the destructive dependency CID.
9. Otherwise combine the local score and dependency mean.
10. Memoize the result; if destroyed, learn it as a no-good.

Default status thresholds:

```text
score <= -0.20       destroyed
|score| <= 0.08      uncertain
otherwise            survives
```

The thresholds are configuration parameters, not universal constants.

## 8. Fail-first ordering

The hazard heuristic estimates which requirement is most likely to destroy a branch:

```text
hazard(p) = local_opposition(p) - local_support(p)
            + 0.8 × max(hazard(child))
```

Candidates and proposition dependencies are evaluated in descending hazard order. This is analogous to testing the most constraining or failure-prone branch first. The heuristic is deliberately simple so its contribution is inspectable.

## 9. Content-addressed memoization

Ordinary memoization often keys on local object identity or a caller-selected string. QIDS-CAM keys on:

```text
(proposition_semantic_CID, constraint_context_CID)
```

This enables reuse across aliases and across any path that reaches the exact same proposition subgraph under the same constraint context.

A memo entry can store surviving, uncertain, or destroyed resolution. A no-good entry stores only destroyed resolution and is checked first.

## 10. Context-bound no-goods

A contradiction may be valid only under a specific policy, time, user, environment, or assumption set. QIDS-CAM therefore hashes the constraint object independently and binds negative reuse to the pair:

```text
no_good_key = (proposition_CID, context_CID)
```

This avoids treating all contradictions as globally valid. Future versions may support explicit subsumption and scoped context lattices; v0.1.0 requires exact context identity.

## 11. Candidate pruning

Candidate requirements are fail-first ordered. Once one is destroyed:

- the candidate is destroyed;
- remaining requirements are not evaluated;
- skipped work is counted as `avoided_requirements`;
- the candidate result links to its immutable candidate CID.

The exhaustive configuration intentionally continues through all requirements so the ablation exposes the contribution of pruning.

## 12. Proof object

After all candidates are resolved, QIDS-CAM creates immutable candidate-result nodes and a solve-proof node containing:

- solver configuration;
- problem root;
- constraint-context CID;
- winning candidate key;
- deterministic metrics;
- algorithm version.

Wall-clock time is excluded. The proof root therefore depends on the problem, configuration, context, deterministic execution outputs, and algorithm version—not machine speed.

The exported archive includes every reachable node. Verification recomputes every node CID and checks that every outbound link resolves.

This is a **computation receipt**, not a formal proof that natural-language evidence is true. It proves integrity and reproducibility of the represented execution.

## 13. Reference components

| File | Responsibility |
|---|---|
| `qids_cam/canonical.py` | deterministic serialization and CID generation |
| `qids_cam/merkle.py` | immutable node store, archive import/export, verification |
| `qids_cam/schema.py` | validated domain input and cycle checks |
| `qids_cam/solver.py` | compilation, aggregation, pruning, memo/no-good reuse, proof root |
| `qids_cam/benchmark.py` | deterministic workload generation and four ablations |
| `qids_cam/cli.py` | user-facing execution and verification commands |
| `web/app.js` | independent browser implementation of the same core concept |

## 14. Production extension points

### Storage

Replace the in-memory map with a CAS implementing `put`, `get`, `verify`, and reachability. Preserve canonicalization and namespace/version markers.

### Claim extraction

Insert an LLM or symbolic parser before `Problem` construction. Store the extraction prompt/model/config and source spans in evidence metadata so the resulting identity captures the chosen semantics.

### Entailment and contradiction

Replace supplied stance/confidence with an NLI model, LLM jury, rule engine, or calibrated ensemble. Treat classifier version and policy as part of the context CID.

### Retrieval

Use vector/BM25/graph retrieval to discover evidence. Merkle identity should complement, not replace, semantic retrieval.

### Distributed reuse

Persist memo/no-good records keyed by CID pair. Add authorization, TTL/policy rules, and lineage before sharing across tenants.

### Learning

Train fail-first ordering on historical destruction utility while retaining a deterministic inference mode for benchmark reproducibility.

## 15. Non-goals

QIDS-CAM v0.1.0 is not:

- a quantum computer or quantum simulator;
- a general theorem prover;
- a replacement for embeddings or retrieval indexes;
- a guarantee that the surviving candidate is factually correct;
- a production distributed object store;
- a claim of asymptotic quantum advantage;
- a proof that every RAG workload contains reusable subgraphs.
