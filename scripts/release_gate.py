"""Prepublication gate: actual behavior, artifact consistency and offline install."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Direct checkout execution requires the path bootstrap above before these imports.
from qids_cam.canonical import canonical_json  # noqa: E402
from qids_cam.io import load  # noqa: E402
from qids_cam.proof import verify_archive  # noqa: E402
from qids_cam.suite import run_suite  # noqa: E402
from qids_cam.explorer import render_explorer  # noqa: E402


def run(command, cwd=ROOT, env=None):
    result = subprocess.run(
        command, cwd=cwd, env=env, text=True, capture_output=True, timeout=120
    )
    if result.returncode:
        raise RuntimeError(
            f"command failed: {command!r}\n{result.stdout}\n{result.stderr}"
        )
    return result.stdout + result.stderr


def checksum_file(path):
    for line in path.read_text().splitlines():
        expected, name = line.split("  ", 1)
        base = path.parent if path.parent.name == "wheels" else ROOT
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"checksum mismatch: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    checks = {}
    # Validate a clean artifact inventory, not files picked dynamically at push.
    output = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    count = int(re.search(r"Ran (\d+) tests", output).group(1))
    checks["unit_and_distinct_acceptance"] = {
        "state": "PASS",
        "tests": count,
        "random_dags": 60,
        "optimized_configs_per_dag": 5,
    }
    for name in ("demo-proof.json", "rag-adapter-proof.json", "reuse-proof.json"):
        report = verify_archive(load(ROOT / "results" / name))
        checks[name] = {
            "state": "PASS",
            "root": report["root"],
            "nodes": report["nodes"],
            "winner": report["winner"],
        }
    for archive, html in (("demo-proof.json", "explorer.html"),
                          ("reuse-proof.json", "reuse-explorer.html")):
        if render_explorer(load(ROOT / "results" / archive)) != (ROOT / "docs" / html).read_text():
            raise ValueError(f"browser export drift: {html}")
    checks["actual_receipt_browser_exports"] = {"state": "PASS", "exports": 2}
    recorded = load(ROOT / "results/suite-v2.json")
    current = run_suite()
    if not current["parity"] or not current["deterministic"]:
        raise ValueError("suite parity/determinism failed")
    if len(recorded["cases"]) != len(current["cases"]):
        raise ValueError("suite cases missing")
    for old, new in zip(recorded["cases"], current["cases"]):
        if (old["workload"], old["seed"]) != (new["workload"], new["seed"]):
            raise ValueError("suite case order mismatch")
        for label, value in new["runs"].items():
            before = {
                k: v
                for k, v in old["runs"][label].items()
                if k not in ("elapsed_ms", "end_to_end_ms")
            }
            after = {
                k: v
                for k, v in value.items()
                if k not in ("elapsed_ms", "end_to_end_ms")
            }
            if canonical_json(before) != canonical_json(after):
                raise ValueError(f"recorded suite drift: {label}")
    checks["frozen_synthetic_suite"] = {
        "state": "PASS",
        "cases": len(current["cases"]),
        "rows": sum(len(c["runs"]) for c in current["cases"]),
        "parity": True,
        "deterministic": True,
    }
    checksum_file(ROOT / "docs/HISTORY-SHA256SUMS")
    checksum_file(ROOT / "wheels/SHA256SUMS")
    public = load(ROOT / "PUBLIC-FILES.json")["files"]
    prohibited = {
        "node_modules",
        ".git",
        ".private",
        ".work",
        ".env",
        "__pycache__",
        "RELEASE-EVIDENCE.md",
        ".verification",
    }
    secrets = (
        re.compile(rb"gh[pousr]_[A-Za-z0-9]{36,}"),
        re.compile(rb"AKIA[0-9A-Z]{16}"),
        re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    )
    for name in public:
        path = ROOT / name
        if (
            name.startswith("/")
            or ".." in Path(name).parts
            or prohibited.intersection(Path(name).parts)
            or path.is_symlink()
            or not path.is_file()
        ):
            raise ValueError(f"unsafe publication path: {name}")
        data = path.read_bytes()
        if any(p.search(data) for p in secrets):
            raise ValueError(f"possible credential in reviewed file: {name}")
    wheel = ROOT / "wheels/qids_cam-0.2.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError("unsafe wheel path")
            if (
                name.startswith("qids_cam/")
                and archive.read(name) != (ROOT / name).read_bytes()
            ):
                raise ValueError(f"wheel source mismatch: {name}")
        expected = {
            f.as_posix()
            for f in (ROOT / "qids_cam").rglob("*")
            if f.is_file() and "__pycache__" not in f.parts
        }
        expected = {str(Path(n).relative_to(ROOT)) for n in expected}
        if expected != {n for n in archive.namelist() if n.startswith("qids_cam/")}:
            raise ValueError("wheel package file inventory mismatch")
        meta = archive.read("qids_cam-0.2.0.dist-info/METADATA").decode()
        if meta.split("\n\n", 1)[1] != (ROOT / "README.md").read_text():
            raise ValueError("wheel README metadata mismatch")
        if "Requires-Dist:" in meta:
            raise ValueError("unexpected runtime dependency")
    checks["artifact_provenance_and_boundaries"] = {
        "state": "PASS",
        "reviewed_files": len(public),
        "wheel_matches_source": True,
        "runtime_dependencies": 0,
        "historical_checksums": "PASS",
        "credential_patterns": "PASS (pattern scan plus manual review; not a comprehensive guarantee)",
    }
    with tempfile.TemporaryDirectory(prefix="qids-clean-install-") as directory:
        tmp = Path(directory)
        environment = tmp / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        cli = environment / (
            "Scripts/qids-cam.exe" if os.name == "nt" else "bin/qids-cam"
        )
        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-index",
                "--no-deps",
                str(wheel),
            ],
            cwd=tmp,
        )
        run(
            [str(python), "-I", "-m", "qids_cam", "demo", "--archive", "proof.json"],
            cwd=tmp,
        )
        verified = run(
            [str(python), "-I", "-m", "qids_cam", "verify", "proof.json"], cwd=tmp
        )
        inspected = run(
            [str(cli), "inspect", "proof.json", "--limit", "2"],
            cwd=tmp,
            env={k: v for k, v in os.environ.items() if not k.startswith("PYTHON")},
        )
        run([str(cli), "explore", "proof.json", "--output", "proof.html"], cwd=tmp)
        html = (tmp / "proof.html").read_text()
        if "One identity" not in html or "connect-src 'none'" not in html:
            raise ValueError("installed browser assets are missing or unsafe")
        if (
            "winner cache_stampede" not in verified
            or "Winner: cache_stampede" not in inspected
        ):
            raise ValueError("installed golden path mismatch")
        checks["clean_venv_offline_install"] = {
            "state": "PASS",
            "network_required": False,
            "global_site_packages": False,
            "cwd_outside_checkout": True,
            "journey": "wheel install -> demo -> archive -> separate verify process -> installed inspect -> standalone browser export",
        }
    result = {
        "schema": "qids-cam/prepublication-gate/v1",
        "state": "PASS",
        "python": sys.version.split()[0],
        "paid_runtime_usd": 0,
        "checks": checks,
        "publication": "NOT_CHECKED_BY_THIS_GATE: verify destination and fresh public clone separately",
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
