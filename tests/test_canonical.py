from __future__ import annotations

import math
import unittest

from qids_cam.canonical import CanonicalizationError, canonical_json, cid_for


class CanonicalTests(unittest.TestCase):
    def test_mapping_order_does_not_change_cid(self) -> None:
        left = {"b": 2, "a": [3, 1]}
        right = {"a": [3, 1], "b": 2}
        self.assertEqual(canonical_json(left), canonical_json(right))
        self.assertEqual(cid_for(left), cid_for(right))

    def test_content_change_changes_cid(self) -> None:
        self.assertNotEqual(cid_for({"value": 1}), cid_for({"value": 2}))

    def test_non_finite_float_is_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            canonical_json({"bad": math.nan})


if __name__ == "__main__":
    unittest.main()
