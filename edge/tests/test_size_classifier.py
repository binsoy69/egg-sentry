import unittest

from edge.config import SizeThresholds
from edge.size_classifier import SizeClassifier, count_sizes


class SizeClassifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = SizeClassifier(
            thresholds=SizeThresholds(
                small_max=0.0020,
                medium_max=0.0030,
                large_max=0.0042,
                xl_max=0.0055,
            ),
            edge_margin_pixels=10,
            aspect_ratio_min=0.5,
            aspect_ratio_max=2.0,
        )
        self.frame_shape = (1000, 1000, 3)

    def test_classifies_by_threshold_band(self) -> None:
        self.assertEqual(self.classifier.classify((100, 100, 140, 140), self.frame_shape).size, "small")
        self.assertEqual(self.classifier.classify((100, 100, 150, 150), self.frame_shape).size, "medium")
        self.assertEqual(self.classifier.classify((100, 100, 160, 160), self.frame_shape).size, "large")
        self.assertEqual(
            self.classifier.classify((100, 100, 170, 170), self.frame_shape).size,
            "extra-large",
        )
        self.assertEqual(self.classifier.classify((100, 100, 180, 180), self.frame_shape).size, "jumbo")

    def test_threshold_boundaries_roll_into_the_next_class(self) -> None:
        self.assertEqual(self.classifier.classify((100, 100, 150, 140), self.frame_shape).size, "medium")
        self.assertEqual(self.classifier.classify((100, 100, 160, 150), self.frame_shape).size, "large")
        self.assertEqual(
            self.classifier.classify((100, 100, 170, 160), self.frame_shape).size,
            "extra-large",
        )
        self.assertEqual(self.classifier.classify((100, 100, 110, 650), self.frame_shape).size, "unknown")

    def test_marks_extreme_aspect_ratio_as_unknown(self) -> None:
        result = self.classifier.classify((100, 100, 120, 180), self.frame_shape)
        self.assertEqual(result.size, "unknown")
        self.assertEqual(result.reason, "aspect_ratio_out_of_bounds")

    def test_marks_edge_touching_boxes_as_unknown(self) -> None:
        result = self.classifier.classify((5, 100, 55, 150), self.frame_shape)
        self.assertEqual(result.size, "unknown")
        self.assertEqual(result.reason, "touches_frame_edge")

    def test_count_sizes_filters_zero_entries(self) -> None:
        classifications = [
            self.classifier.classify((100, 100, 140, 140), self.frame_shape),
            self.classifier.classify((100, 100, 150, 150), self.frame_shape),
            self.classifier.classify((5, 100, 55, 150), self.frame_shape),
        ]
        self.assertEqual(count_sizes(classifications), {"small": 1, "medium": 1, "unknown": 1})


if __name__ == "__main__":
    unittest.main()

