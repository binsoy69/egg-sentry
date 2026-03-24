import json

from edge.config import load_config


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
