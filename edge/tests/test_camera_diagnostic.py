from edge.camera_diagnostic import (
    ResolutionInfo,
    capture_resolution_info,
    evaluate_camera_placement,
)
from edge.detector import Detection


def test_evaluate_camera_placement_requires_visible_egg() -> None:
    feedback = evaluate_camera_placement((720, 1280, 3), [])

    assert feedback.ok is False
    assert feedback.headline == "No eggs detected"


def test_evaluate_camera_placement_accepts_centered_detection() -> None:
    feedback = evaluate_camera_placement(
        (720, 1280, 3),
        [
            Detection(
                x1=500,
                y1=250,
                x2=700,
                y2=500,
                confidence=0.91,
                class_id=0,
                label="egg",
            )
        ],
    )

    assert feedback.ok is True
    assert feedback.headline == "Placement looks good"


def test_capture_resolution_info_uses_actual_frame_shape() -> None:
    class DummyFrame:
        shape = (480, 640, 3)

    resolution = capture_resolution_info(DummyFrame())

    assert resolution == ResolutionInfo(width=640, height=480)


def test_evaluate_camera_placement_flags_off_center_small_detection() -> None:
    feedback = evaluate_camera_placement(
        (720, 1280, 3),
        [
            Detection(
                x1=25,
                y1=40,
                x2=50,
                y2=65,
                confidence=0.88,
                class_id=0,
                label="egg",
            )
        ],
    )

    assert feedback.ok is False
    assert feedback.headline == "Adjust camera placement"
    assert any("frame edge" in detail for detail in feedback.details)
    assert any("too far away" in detail for detail in feedback.details)
    assert any("left of center" in detail for detail in feedback.details)
    assert any("high in the frame" in detail for detail in feedback.details)
