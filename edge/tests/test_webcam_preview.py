from edge.webcam_preview import (
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    ResolutionInfo,
    capture_resolution_info,
    parse_args,
    parse_source,
)


class DummyCapture:
    def __init__(self, width: float, height: float, fps: float) -> None:
        self.values = {
            3: width,
            4: height,
            5: fps,
        }

    def get(self, prop: int) -> float:
        return self.values.get(prop, 0.0)


class DummyFrame:
    shape = (720, 1280, 3)


def test_parse_source_supports_index_and_device_path() -> None:
    assert parse_source("0") == 0
    assert parse_source("/dev/video0") == "/dev/video0"


def test_parse_args_requests_1080p_by_default() -> None:
    args = parse_args([])

    assert args.width == DEFAULT_WIDTH == 1920
    assert args.height == DEFAULT_HEIGHT == 1080


def test_capture_resolution_info_uses_capture_properties() -> None:
    info = capture_resolution_info(DummyCapture(640.0, 480.0, 30.0), DummyFrame())

    assert info == ResolutionInfo(width=640, height=480, fps=30.0)
    assert info.label == "640x480 @ 30.0 FPS"


def test_capture_resolution_info_falls_back_to_frame_shape() -> None:
    info = capture_resolution_info(DummyCapture(0.0, 0.0, 0.0), DummyFrame())

    assert info == ResolutionInfo(width=1280, height=720, fps=None)
    assert info.label == "1280x720"
