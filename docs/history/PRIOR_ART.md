# Prior Art and Research Boundaries

QIDS-CAM intentionally combines established ideas. This document states what each neighboring area contributes and what the project does—and does not—claim.

## 1. Merkle trees and Merkle DAGs

Merkle structures provide content-derived identity, tamper evidence, structural sharing, and efficient verification. IPFS is a prominent implementation of Merkle-DAG content addressing, where nodes link to other nodes by content identifier.

Relevant starting point:

- IPFS Docs, “Merkle DAGs”: https://docs.ipfs.tech/concepts/merkle-dag/

QIDS-CAM contribution boundary:

- **not claimed:** invention of Merkle trees, Merkle DAGs, hashes, or content-addressed storage;
- **proposed:** use a proposition’s semantic payload plus evidence/dependency CIDs as its exact computational identity, then bind destructive resolution to that identity and a constraint-context CID.

## 2. Quantum interference and amplitude amplification

Quantum algorithms use amplitudes and phase so computational paths can reinforce or cancel. Grover-style amplitude amplification uses interference to increase the probability of desired states.

Relevant starting points:

- IBM Quantum Learning, interference and quantum circuits: https://quantum.cloud.ibm.com/learning/
- L. K. Grover, “A fast quantum mechanical algorithm for database search,” 1996.

QIDS-CAM contribution boundary:

- **not claimed:** qubit simulation, physical superposition, measurement behavior, amplitude amplification, or quantum speedup;
- **borrowed intuition:** assign signed/phase-aware contributions to evidence and use cancellation as a classical elimination signal;
- **different capability:** persist the identity and reason for a destroyed state across later paths or solves.

## 3. Conflict-driven search and no-goods

SAT, CSP, answer-set solving, and related systems learn conflict clauses or no-goods so the solver does not revisit known-inconsistent regions. Conflict-Driven Clause Learning (CDCL) is a central example.

Relevant starting points:

- J. P. Marques-Silva and K. A. Sakallah, “GRASP: A Search Algorithm for Propositional Satisfiability,” 1999.
- J. Marques-Silva, I. Lynce, and S. Malik, “Conflict-Driven Clause Learning SAT Solvers,” in *Handbook of Satisfiability*, 2009.

QIDS-CAM contribution boundary:

- **not claimed:** invention of conflict learning, branch pruning, memoization, or fail-first search;
- **proposed:** represent the learned negative state as a reusable `(semantic proposition CID, context CID)` result embedded in a verifiable Merkle computation graph.

Unlike a general SAT clause database, the v0.1.0 no-good is an exact context-bound proposition result rather than a learned generalized clause.

## 4. Dynamic programming, memoization, and hash-consing

Dynamic programming and memoization reuse solved subproblems. Hash-consing canonicalizes structurally identical objects so they can share representation.

QIDS-CAM contribution boundary:

- **not claimed:** invention of cached subproblem evaluation or structural interning;
- **proposed:** make natural-language/AI reasoning propositions explicit immutable DAG nodes, expose the CIDs in execution receipts, and combine reuse with destructive conflict propagation.

## 5. Knowledge graphs, GraphRAG, and DAG-based RAG

Knowledge-graph and GraphRAG systems structure entities, relations, communities, and summaries to improve retrieval and global reasoning. Other research represents query plans, hierarchical summaries, or reasoning dependencies as DAGs.

Representative starting point:

- D. Edge et al., “From Local to Global: A Graph RAG Approach to Query-Focused Summarization,” 2024: https://arxiv.org/abs/2404.16130

QIDS-CAM contribution boundary:

- **not claimed:** invention of graph retrieval, knowledge graphs, hierarchical RAG, multi-hop decomposition, or DAG execution;
- **different focus:** exact content identity for repeated proposition subgraphs and reusable negative resolution, rather than graph construction or semantic retrieval alone.

A GraphRAG index and QIDS-CAM are complementary: the former can discover evidence and relationships; the latter can verify and destructively prune candidate reasoning states.

## 6. Provenance and verifiable RAG

Research and systems increasingly attach provenance, signatures, content hashes, or authenticated data structures to retrieved evidence and generated answers.

QIDS-CAM contribution boundary:

- **not claimed:** invention of cryptographic provenance or verifiable retrieval;
- **proposed:** include deterministic search outcomes and negative computation in the content-addressed execution object, not only the source corpus.

The solve root is an integrity receipt. It does not establish the truth of an evidence statement or the correctness of an NLI judgment.

## 7. Conflict-aware RAG

RAG systems may retrieve mutually inconsistent sources. Existing work addresses contradiction detection, evidence attribution, source reliability, and synthesis under disagreement.

QIDS-CAM contribution boundary:

- **not claimed:** first contradiction-aware RAG system;
- **proposed:** when an adapter resolves a proposition as destructively contradicted, persist that result under exact content/context identity and propagate it through all dependent candidate paths.

## 8. Concise novelty statement

The project’s research proposition is:

> A classical AI reasoning system can treat contradiction as reusable negative computation by content-addressing proposition subgraphs, binding destructive results to explicit constraint contexts, and propagating those results across every candidate path that reaches the same CID, while emitting a recursively verifiable solve root.

The repository demonstrates that proposition with an inspectable implementation and an ablation benchmark. Whether the approach produces meaningful quality/cost gains on real RAG and agent workloads remains an empirical question.

## 9. Citation ethics

Researchers adopting the formulation should cite Hayden Lindley and this repository even when replacing the reference implementation. Implementers should separately cite the foundational techniques they use: Merkle structures, conflict-driven search, graph RAG, NLI, and any external datasets or models.
