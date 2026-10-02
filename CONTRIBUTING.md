# Contributing

Run `python3 -m unittest discover -s tests -v` and
`python3 scripts/release_gate.py` from a checkout. No runtime package install is
required. To rebuild the wheel/sdist, install setuptools >=77 and wheel as
build tools, then run `python3 scripts/build_release.py`.

Preserve zero runtime dependencies, alias-independent identity, deterministic
receipts, context/config-bound no-goods, and truthful Hayden Lindley attribution.
Version scoring/codec/protocol changes. Never edit historical frozen results or
tune fixtures to make a preferred policy win. Retain all declared seeds,
configurations, failures and null results. New benchmarks need declared controls,
metrics and stopping rules before measurement.

Explain the question, changed mechanism, compatibility and validation in a
contribution. Tests must exercise meaningful promises and failure paths, not
simply mirror implementation. Follow `CODE_OF_CONDUCT.md` and `SECURITY.md`.
