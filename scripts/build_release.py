"""Build local offline-install artifacts; this never uploads or publishes."""

import hashlib
import os
from pathlib import Path

import setuptools.build_meta as backend

root = Path(__file__).resolve().parents[1]
os.chdir(root)
os.environ.setdefault("SOURCE_DATE_EPOCH", "1790899200")
wheel = backend.build_wheel("wheels")
file = root / "wheels" / wheel
(root / "wheels/SHA256SUMS").write_text(
    hashlib.sha256(file.read_bytes()).hexdigest() + "  " + wheel + "\n"
)
backend.build_sdist("dist")
print("Local artifacts built; no package upload or release created.")
