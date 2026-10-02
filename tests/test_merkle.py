from __future__ import annotations

import copy
import unittest

from qids_cam.merkle import MerkleStore


class MerkleStoreTests(unittest.TestCase):
    def test_deduplicates_identical_nodes(self) -> None:
        store = MerkleStore()
        first = store.put("evidence", {"text": "same"})
        second = store.put("evidence", {"text": "same"})
        self.assertEqual(first, second)
        self.assertEqual(len(store), 1)

    def test_archive_round_trip_verifies(self) -> None:
        store = MerkleStore()
        leaf = store.put("leaf", {"value": 1})
        root = store.put("root", {"name": "r"}, links=(leaf,))
        archive = store.export_archive(root)
        restored = MerkleStore.from_archive(archive)
        self.assertTrue(restored.verify(root, recursive=True))

    def test_tampered_archive_is_rejected(self) -> None:
        store = MerkleStore()
        root = store.put("root", {"value": 1})
        archive = copy.deepcopy(store.export_archive(root))
        archive["nodes"][root]["payload"]["value"] = 2
        with self.assertRaises(ValueError):
            MerkleStore.from_archive(archive)


if __name__ == "__main__":
    unittest.main()
