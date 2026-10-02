# Implementing QIDS-CAM in a RAG or Agent System

## 1. Placement in a modern pipeline

QIDS-CAM is most useful after retrieval has produced evidence and after one or more candidate answers or plans have been proposed.

```text
user query
  → semantic / lexical / graph retrieval
  → claim and dependency extraction
  → candidate answer generation
  → QIDS-CAM compile + destructive verification
  → surviving candidate synthesis
  → answer + citations + proof root
```

It is not intended to replace vector search. Semantic retrieval discovers potentially relevant material; content addressing establishes exact identity for the material and reasoning state selected by the adapter.

## 2. Minimal adapter contract

The application must produce four object types:

### Evidence records

```json
{
  "key": "ev_42",
  "text": "Service metrics show a 91% cache miss rate.",
  "stance": 1,
  "confidence": 0.94,
  "source": "otel://prod/cache/miss-rate",
  "tags": ["telemetry", "cache"]
}
```

### Proposition records

```json
{
  "key": "claim_cache_miss",
  "statement": "The cache miss rate was abnormally high.",
  "evidence": ["ev_42"],
  "depends_on": [],
  "metadata": {"extractor": "nli-model-v3"}
}
```

### Candidate records

```json
{
  "key": "answer_cache_stampede",
  "label": "A cache stampede caused the outage.",
  "requires": ["claim_cache_miss", "claim_concurrency_spike"],
  "prior": 0.05
}
```

### Constraint context

```json
{
  "tenant": "example",
  "corpus_revision": "sha256:...",
  "as_of": "2026-08-17T00:00:00Z",
  "source_policy": "production-observability-v2",
  "entailment_model": "model-and-prompt-hash"
}
```

The context is content-addressed independently. Include every condition that could change whether a prior destructive result remains valid.

## 3. Claim construction

A robust adapter should not hash raw natural-language text alone and assume semantic equivalence. Canonical proposition construction should include:

- normalized claim text or a structured predicate;
- exact source-span CIDs;
- dependency CIDs;
- temporal and entity scope;
- extractor/model/prompt version;
- evaluation policy version;
- relevant metadata.

Two claims should share a CID only when the application is willing to reuse the exact same resolution for both.

## 4. Stance and confidence

Possible stance sources include:

- an NLI classifier;
- an LLM structured-output evaluator;
- rules over structured telemetry;
- database constraints;
- human annotations;
- an ensemble.

Keep the source of the score auditable. Confidence should represent the adapter’s calibrated belief in the evidence relationship, not merely an LLM’s verbal certainty.

For a first integration, use phase `0°` for support and `180°` for opposition. Intermediate phases should be introduced only with a declared interpretation and evaluation protocol.

## 5. Candidate generation

Candidates may be:

- answer hypotheses;
- alternative plans;
- root-cause diagnoses;
- tool-use trajectories;
- document interpretations;
- architectural designs;
- theorem branches.

Each candidate declares the propositions that must survive for the candidate to remain viable. This explicit dependency contract is what enables one destroyed proposition to prune many candidates.

## 6. Run the reference solver

```python
from qids_cam import Problem, QIDSCAMSolver

problem = Problem.from_dict(problem_payload)
solver = QIDSCAMSolver()
result = solver.solve(problem, constraints=context_payload)

survivors = [
    candidate
    for candidate in result.candidate_results
    if candidate.status != "destroyed"
]
```

Use `result.winner` as a deterministic reference ranking, or pass the survivors and scores back to an LLM for final synthesis. Do not allow the synthesizer to silently reintroduce a destroyed requirement; include the destructive trace in its context or enforce candidate selection structurally.

## 7. Persist content-addressed memory

The reference solver stores memory only for one solve. A production deployment should externalize two tables or keyspaces:

```text
resolved_state[(proposition_cid, context_cid)] → proposition_result
no_good[(proposition_cid, context_cid)]       → destroyed_result + reason
```

Recommended fields:

- proposition CID;
- context CID;
- status and score;
- destructive dependency CID, when any;
- evidence and dependency links;
- algorithm/evaluator version;
- created time;
- expiration or policy scope;
- signature/tenant ownership;
- validation status.

A distributed implementation can place immutable nodes in a content-addressed store and mutable lookup pointers in a conventional database.

## 8. Source updates and invalidation

Content addressing avoids broad invalidation:

- unchanged evidence retains its CID;
- changed evidence gets a new CID;
- ancestor propositions whose links change receive new CIDs;
- unaffected subgraphs retain prior identities and results.

Do not delete prior immutable nodes merely because a new corpus revision exists. Instead, bind solves and no-goods to a corpus/context CID and apply retention policy separately.

## 9. Proof receipts

Return at least:

```json
{
  "answer": "...",
  "candidate": "answer_cache_stampede",
  "problem_root": "sha256:...",
  "solve_root": "sha256:...",
  "evidence_cids": ["sha256:..."],
  "destroyed_alternatives": [
    {"candidate": "...", "reason_cid": "sha256:..."}
  ]
}
```

The root proves that the represented execution has not been altered. It does not prove source truth. Preserve the distinction in user interfaces and governance documents.

## 10. Measuring value

Track at least:

- proposition expansions;
- retrieval/model calls avoided;
- tokens avoided;
- no-good hit rate;
- memo hit rate;
- candidate branches pruned;
- answer quality and calibration;
- false destruction rate;
- stale no-good rate;
- proof verification failures;
- storage and lookup cost.

The critical guardrail is **false destruction**: a system that saves work by incorrectly eliminating the correct answer is worse, not better. Always report answer parity or task-quality deltas next to efficiency metrics.

## 11. Suggested first real benchmark

Choose a dataset or internal workload containing repeated evidence and mutually inconsistent candidate claims. Freeze:

1. retrieval corpus;
2. chunking and source identifiers;
3. claim extraction prompt/model;
4. contradiction classifier;
5. candidate generation;
6. all four QIDS-CAM ablations;
7. quality metric;
8. token, call, expansion, and latency accounting.

Evaluate cold-cache and warm-cache conditions separately. A content-addressed memory system should be judged both within one solve and across repeated queries/corpus overlap.

## 12. Security and multi-tenant concerns

Content identifiers can reveal equality across records even when content is hidden. In sensitive deployments:

- use tenant-scoped namespaces or keyed digests where equality leakage is unacceptable;
- do not expose raw CIDs as proof of content ownership without a disclosure analysis;
- separate public immutable evidence from private pointers and access policy;
- sign imported no-good records;
- reject untrusted archives that exceed size/depth limits;
- include evaluator and policy versions in context identity;
- prevent one tenant from poisoning another tenant’s negative memory.

## 13. Minimal example

Run:

```bash
python -m examples.rag_adapter
```

The example simulates a retriever/NLI adapter, builds a problem, solves it, prints destroyed alternatives, exports a proof archive, and verifies the archive without any external service.
