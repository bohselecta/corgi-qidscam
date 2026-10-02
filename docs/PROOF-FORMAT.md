# Portable proof/trace format

Envelope: `qids-cam/archive/v1`, exact fields `schema`, `root`, `nodes`.
`nodes` maps lowercase `sha256:` plus 64 hex digits to records with exactly
`schema: qids-cam/node/v1`, nonempty `kind`, object `payload`, and `links`.
Links are sorted unique CIDs. Every referenced record must exist. Every record
must be reachable from root; orphans, cycles and extra fields are rejected.

The envelope is JSON, not an executable archive. There are no paths to extract.

## Hash codec

Node CID = `sha256:` + hex(SHA256(UTF8(`qids-cam-node-v1`) + NUL +
canonical UTF-8 JSON of the entire record)). JSON keys sort lexicographically,
no separator whitespace, Unicode retained (`ensure_ascii=False`), no NaN/Inf.
Arrays retain order. Python finite float spelling is normative for this codec;
negative zero becomes `0.0`. Integers and floats in arbitrary metadata are
distinct encodings; typed confidence/phase/prior fields normalize to floats.
No Unicode normalization, fuzzy equality, JCS or IPLD compatibility is claimed.
`qids_cam.canonical` and `tests/test_canonical.py` provide executable vectors.

Context CID hashes canonical constraints with namespace
`qids-cam-constraint-context-v1`. Arbitrary metadata should include evaluator,
corpus and policy revisions when those determine evidence meaning.

## Execution receipt

Root kind `solve-proof`, payload `proof_schema: qids-cam/solve-proof/v2`,
`algorithm_version: 0.2.0`. It links the compiled `problem`, `solve-input`,
`constraint-context`, `execution-trace`, `resolved-states` and candidate-result
nodes. Input retains the complete problem (including aliases) and constraints.
Payload references those nodes, exact solver config, winner, all candidate
outcomes and deterministic metrics. Trace retains ordered events/subjects/CIDs,
status, rounded scores and explanation text. States retain evaluated
propositions, scores and dependency CIDs; skipped work is not fabricated.

Local vector components/scores are rounded to 12 decimal places; resolved and
candidate scores to 12; trace scores to 8. Time is excluded. Proof reproducibility
has been verified on Linux/Python 3.12.14, not all floating-point platforms.

`verify` first checks every node using only archive contents, then recreates the
cold execution and requires an identical proof root. A separate reference
checks candidate status/score/winner. `verify --hash-only` supports generic and
historical DAGs without a semantic execution claim. A valid hash alone cannot
establish true observations, origin identity or a correct scoring policy.

## Limits and compatibility

64 MiB UTF-8 JSON, 100,000 archive nodes, 500,000 links. Problem: <=20,000 evidence
items, <=10,000 propositions, <=4,096 candidates, <=500,000 references; max DAG
depth 128; <=250,000 expanded occurrences per solve. Deep JSON, duplicate keys,
nonfinite values and malformed input fail. These bounds do not replace an
external process sandbox for hostile workloads.

Historical v0.1 envelopes remain hash-checkable. Historical solve roots omit
full input/trace and therefore cannot be promoted to replay-verified v2 proofs.
Re-solve with version 0.2 to produce a new receipt; never rewrite old roots.
