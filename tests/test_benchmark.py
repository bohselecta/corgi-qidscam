from __future__ import annotations

import unittest

from qids_cam.benchmark import run_benchmark


class BenchmarkTests(unittest.TestCase):
    def test_medium_benchmark_has_parity_and_reduces_work(self) -> None:
        result = run_benchmark("medium", seed=7)
        self.assertTrue(result["answer_parity"])
        self.assertGreater(result["ratios"]["expansion_reduction_vs_exhaustive"], 10.0)
        self.assertGreater(
            result["ratios"]["expansion_reduction_vs_destructive_only"], 2.0
        )
        full = result["runs"]["qids-cam"]
        self.assertGreater(full["nogood_hits"], 0)
        self.assertGreater(full["avoided_requirements"], 0)


if __name__ == "__main__":
    unittest.main()
