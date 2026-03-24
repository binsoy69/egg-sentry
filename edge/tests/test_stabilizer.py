import unittest

from edge.stabilizer import CaptureSnapshot, RollingStabilizer, rolling_mode


class StabilizerTests(unittest.TestCase):
    def test_rolling_mode_returns_zero_for_empty_list(self) -> None:
        self.assertEqual(rolling_mode([]), 0)

    def test_rolling_mode_breaks_ties_by_most_recent_value(self) -> None:
        self.assertEqual(rolling_mode([2, 3]), 3)
        self.assertEqual(rolling_mode([1, 2, 1, 2]), 2)

    def test_stabilizer_returns_majority_count_and_sizes(self) -> None:
        stabilizer = RollingStabilizer(window_size=3)

        first = stabilizer.update(
            CaptureSnapshot(total_count=2, size_counts={"small": 1, "medium": 1})
        )
        self.assertEqual(first.total_count, 2)
        self.assertEqual(first.size_counts, {"small": 1, "medium": 1})

        second = stabilizer.update(
            CaptureSnapshot(total_count=3, size_counts={"small": 1, "medium": 2})
        )
        self.assertEqual(second.total_count, 3)
        self.assertEqual(second.size_counts, {"small": 1, "medium": 2})

        third = stabilizer.update(
            CaptureSnapshot(total_count=3, size_counts={"small": 1, "medium": 2})
        )
        self.assertEqual(third.total_count, 3)
        self.assertEqual(third.size_counts, {"small": 1, "medium": 2})

    def test_stabilizer_omits_zero_count_size_buckets(self) -> None:
        stabilizer = RollingStabilizer(window_size=2)
        result = stabilizer.update(CaptureSnapshot(total_count=0, size_counts={}))
        self.assertEqual(result.total_count, 0)
        self.assertEqual(result.size_counts, {})


if __name__ == "__main__":
    unittest.main()
