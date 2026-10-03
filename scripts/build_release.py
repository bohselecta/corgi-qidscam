"""Build local offline-install artifacts; this never uploads or publishes."""

import hashlib
import gzip
import io
import os
import shutil
import tarfile
from pathlib import Path

import setuptools.build_meta as backend

root = Path(__file__).resolve().parents[1]
os.chdir(root)
os.environ.setdefault("SOURCE_DATE_EPOCH", "1790899200")
epoch = int(os.environ["SOURCE_DATE_EPOCH"])
wheel = backend.build_wheel("wheels")
file = root / "wheels" / wheel
(root / "wheels/SHA256SUMS").write_text(
    hashlib.sha256(file.read_bytes()).hexdigest() + "  " + wheel + "\n"
)
dist = root / "dist"
dist.mkdir(exist_ok=True)
shutil.copy2(file, dist / wheel)
sdist = dist / backend.build_sdist("dist")
# Setuptools alone does not normalize sdist tar metadata and gzip headers.
buffer = io.BytesIO()
with tarfile.open(sdist, "r:gz") as source, tarfile.open(fileobj=buffer, mode="w",
                                                       format=tarfile.PAX_FORMAT) as target:
    for item in sorted(source.getmembers(), key=lambda m: m.name):
        item.uid = item.gid = 0
        item.uname = item.gname = ""
        item.mtime = epoch
        item.pax_headers = {}
        target.addfile(item, source.extractfile(item) if item.isfile() else None)
with sdist.open("wb") as handle, gzip.GzipFile(fileobj=handle, mode="wb",
                                             filename="", mtime=epoch) as compressed:
    compressed.write(buffer.getvalue())
(dist / "SHA256SUMS").write_text("".join(
    hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
    for p in sorted([dist / wheel, sdist])
))
print("Local artifacts built; no package upload or release created.")
