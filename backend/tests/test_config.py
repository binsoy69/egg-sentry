import os

from app.config import Settings


def test_debug_accepts_release_string() -> None:
    previous = os.environ.get("DEBUG")
    os.environ["DEBUG"] = "release"
    try:
        settings = Settings()
    finally:
        if previous is None:
            os.environ.pop("DEBUG", None)
        else:
            os.environ["DEBUG"] = previous

    assert settings.debug is False
