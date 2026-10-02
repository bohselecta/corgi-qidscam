# Security

Supported version: 0.2.0. All execution is local and offline; no provider,
telemetry or shell is invoked by solve/verify/inspect. Treat archives as local
plaintext data: evidence and contexts can disclose sensitive content, and CIDs
can leak equality. Receipts are not signatures or guarantees of evidence truth.

Strict import limits and DAG checks are documented in `docs/PROOF-FORMAT.md`.
CLI writes atomically to the explicit user-requested path; do not use privileged
paths. An output pair is not transactional. Terminal control/bidi characters are
escaped. No archive extraction or browser rendering occurs.

Untrusted workloads still require external wall-time and memory limits. The
in-memory implementation is not a multi-tenant service, and it does not import
warm caches. Do not turn supplied weights into a trust decision without a
calibrated evaluator and source policy.

Report vulnerabilities privately to the owner of
[bohselecta/corgi-qidscam](https://github.com/bohselecta/corgi-qidscam) via private
vulnerability reporting when enabled. Its availability has not been verified.
Do not publish private evidence/credentials or weaponized data in a public issue.
Zero runtime dependencies means no third-party runtime dependency audit is
applicable. Packaging uses setuptools and wheel, separately recorded build tools.
