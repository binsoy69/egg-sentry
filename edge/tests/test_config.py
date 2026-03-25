import json

from edge.config import SizeThresholds, load_config, save_size_thresholds


def test_load_config_accepts_utf8_bom(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    payload = {
        "backend_api_base_url": "http://127.0.0.1:8000/api",
        "device_id": "cam-001",
        "device_api_key": "dev-cam-001-key",
        "model_path": "../models/counter-yolo26n.pt",
    }

    config_path.write_text(json.dumps(payload), encoding="utf-8-sig")

    config = load_config(config_path)

    assert config.backend_api_base_url == "http://127.0.0.1:8000/api"
    assert config.device_id == "cam-001"
    assert config.device_api_key == "dev-cam-001-key"


def test_save_size_thresholds_updates_only_threshold_block(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    payload = {
        "backend_api_base_url": "http://127.0.0.1:8000/api",
        "device_id": "cam-001",
        "device_api_key": "dev-cam-001-key",
        "model_path": "../models/counter-yolo26n.pt",
        "size_thresholds": {
            "small_max": 0.1,
            "medium_max": 0.2,
            "large_max": 0.3,
            "xl_max": 0.4,
        },
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    save_size_thresholds(
        SizeThresholds(
            small_max=0.0021,
            medium_max=0.0031,
            large_max=0.0041,
            xl_max=0.0051,
        ),
        config_path,
    )

    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["backend_api_base_url"] == payload["backend_api_base_url"]
    assert saved["device_id"] == payload["device_id"]
    assert saved["size_thresholds"] == {
        "small_max": 0.0021,
        "medium_max": 0.0031,
        "large_max": 0.0041,
        "xl_max": 0.0051,
    }
