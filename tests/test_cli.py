from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from qids_cam.cli import main


class CLITests(unittest.TestCase):
    def test_packaged_demo_runs_without_source_example_path(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["demo"])
        self.assertEqual(code, 0)
        self.assertIn("winner                      cache_stampede", output.getvalue())

    def test_demo_archive_can_be_verified(self) -> None:
        with TemporaryDirectory() as directory:
            archive = Path(directory) / "proof.json"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["demo", "--archive", str(archive)]), 0)
                self.assertEqual(main(["verify", str(archive)]), 0)


if __name__ == "__main__":
    unittest.main()
