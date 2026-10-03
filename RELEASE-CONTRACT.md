# QIDS-CAM release contract — 0.2.0

Original v2 contract frozen 2026-10-02; product-preservation repair addendum
locked before browser implementation. Scientific protocol/solver semantics unchanged. Publisher: Corgi-verse Software.

Target: researchers and engineers investigating repeated contradiction-aware candidate graphs.
Value: evaluate a classical evidence graph, reuse exact content-addressed states, prune contradicted paths, and inspect a portable, independently checked execution receipt.

## Scope and invariants

C01: Python library and CLI run offline with standard library only, Python >=3.10. Linux/Python 3.12 is the tested platform; other supported Python versions are CI targets, not observed results.
C02: alias-independent proposition CIDs; canonical namespaced SHA-256; immutable stored content; cycles, duplicate identities, invalid types and nonfinite numbers fail before solve.
C03: fatal local contradiction and destroyed dependency have identical semantics in every ablation; pruning changes work, never candidate survival or winner. Stable ordering and cold solves give deterministic proof roots. Learned no-goods are scoped to exact proposition + context + evaluation configuration; each solve starts fresh.
C04: solve -> archive -> fresh-process verify/replay works with no sibling checkout. Receipt binds full input, constraints, config, candidate outcomes, resolved states and trace. Hash verification is independent of the solver; replay checks deterministic execution. Neither proves evidence truth or is a formal theorem prover.
C05: strict versioned JSON archive, bounded loader, complete reachable DAG, schema/content/link checks; modified, missing, orphan or cyclic data fails. No archive extraction, script execution, networking or provider calls.
C06: CLI inspector plus a standalone offline browser proof explorer display the actual verified v2 archive. Browser dependencies, merged aliases, destroyed/surviving/unevaluated states, candidate requirements/skips, context/no-good/reuse counts, exact node/evidence inspection and keyboard trace navigation derive only from retained receipt data. Python performs full verification at export; HTML records that result without claiming browser-independent verification or evidence truth. Archive downloads preserve Python numeric spelling and pass separate verification. Local evidence is never sent anywhere. Explorer bounded at 5000 nodes / 20000 trace events; larger archives use the CLI.
C07: frozen historical source protocol/results remain byte-identical. New synthetic protocol declares high sharing, low sharing, low contradiction, unique/no contradiction and order-adversarial cases, named ablations, simple reference and alias-memoized baselines, fixed seeds, full answer/status/score parity, deterministic operation counts and diagnostic end-to-end runtime.
C08: installable wheel/sdist, README first success, metadata, Apache-2.0 attribution, changelog, citation, security guidance, release gate and real desktop/mobile browser evidence with terminal output secondary. Browser acceptance uses optional Node/Playwright development tools, never Python runtime dependencies. CI targets Python 3.10–3.14; hosted results remain pending until the approved repair is pushed.

Exclusions: model/RAG extraction or paid runs; corpus/human/production quality claims; quantum speedup; similarity-based reuse; distributed storage; cross-session cache import (untrusted persisted no-goods would require separate verified provenance); website/deployment; invented human acceptance.

## Acceptance

Unit/regression tests plus separately framed random-DAG reference comparison, frozen historic benchmark check, all five new workloads with seven configurations (four source ablations, two simple baselines, and a no-learning diagnostic) and seeds 7/19/41, tampering/malformed/cycle/resource-limit tests, subprocess golden journey and installed clean-clone test. Prepublication gates U01–U14 and R01–R04 must pass. U15/U16 require destination verification and a fresh public clone; they are
recorded separately in the campaign evidence, not inferred from this local gate. Record observed outcomes, including unfavorable comparisons; no thresholds requiring a performance win.

Execution envelope: local offline computation and explicit local output writes. No model/provider APIs, telemetry or automatic publication. Source repositories remain read-only references; the distribution destination is https://github.com/bohselecta/corgi-qidscam.
A later, separate-protocol R&D pass is tracked in docs/RND-BACKLOG.md; it does
not change this contract or the frozen v2 acceptance/results.
