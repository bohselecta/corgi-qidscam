# Product preservation inventory — QIDS-CAM 0.2.0 repair

Source reviewed: `bohselecta/qids-cam`, `main`,
`4d1ed8aed06153080147e862bbae75886001b672` (read-only, locally push-guarded).
Public baseline: `bohselecta/corgi-qidscam`, `main`, commit `6030570`.
Inventory locked before the browser repair on 2026-10-02.

| Meaningful source surface | Disposition | Public implementation / reason |
| --- | --- | --- |
| Content-addressed Python graph-search library | PRESERVE | Keep public v2 validation, scoring, pruning, canonical IDs and context isolation. |
| CLI solve / archive / compare / benchmark | PRESERVE | Keep offline first success and readable terminal inspection. |
| Portable Merkle proof format and verifier | PRESERVE | Keep v2 replay plus independent reference; export the same archive into the explorer. |
| Live browser mechanism demonstration | REIMPLEMENT | Replace the incompatible historical JS solver with a browser explorer of verified Python v2 receipts. Keep visual dependencies, alias reuse, destruction, no-goods and trace navigation. |
| Browser explanatory landing page | FINISH | Lead README with real explorer output and an offline browser journey. Explain measured synthetic benefit and neutral/adverse evidence together. |
| Matched ablations and shared-graph benchmark | PRESERVE | Keep frozen v0.1 artifacts and all 105 v2 rows, including unfavorable timings and no-learning/null findings. |
| RAG boundary example | PRESERVE | Keep fixed synthetic adapter; never label it empirical model/corpus evidence. |
| Architecture, implementation guide and prior art | PRESERVE | Keep original historical copies and current v2 format/architecture/positioning docs. |
| Whitepaper / archival manuscript and bibliography | EXTRACT | Retain source manuscript and bibliography as dated historical research with original claims explicitly distinguished from v2 measured evidence. No peer-review or acceptance claim. |
| Authorship, citation, license and research governance | PRESERVE | Keep Apache-2.0, Hayden Lindley attribution and integrity/contribution/security guidance. |
| Old hosted domain, Vercel configuration, SEO and duplicate `/live` site | RETIRE | These identify the source deployment and incompatible historical format. Offline standalone HTML is the release's portable browser surface; any new hosting requires publication approval. |
| Historical Docker wrapper and npm static-server manifest | RETIRE | They package the old browser/deployment surface; replace with a dependency-free standalone export that works from the installed Python wheel. Browser access remains usable without a historical site dependency. |
| Future cross-session/model-driven research | PRESERVE | Keep explicit unrun boundaries and R&D backlog; no paid runs or new scientific results claimed. |

Acceptance: supplied archive → full Python verification → self-contained HTML →
inspect candidate requirements and proposition aliases → navigate trace →
inspect exact archived payload/context → independently run `verify` on the JSON.
Every node/status/metric shown must derive from that archive. Evidence truth is
always outside the receipt's verification claim.
