import base64
import json

from app.services import quality_service as qs


def test_get_original_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(qs, "ORIGINAL_PATH", tmp_path / "missing.avif")
    assert qs.get_original() is None


def test_get_original_present(monkeypatch, tmp_path):
    original = tmp_path / "orig.avif"
    original.write_bytes(b"fake-avif-bytes")
    monkeypatch.setattr(qs, "ORIGINAL_PATH", original)

    result = qs.get_original()

    assert result["mimeType"] == "image/avif"
    assert base64.b64decode(result["base64"]) == b"fake-avif-bytes"


def test_save_and_list_training_data(monkeypatch, tmp_path):
    train_dir = tmp_path / "train"
    val_dir = tmp_path / "val"
    train_dir.mkdir()
    val_dir.mkdir()
    monkeypatch.setattr(qs, "TRAIN_DIR", train_dir)
    monkeypatch.setattr(qs, "VAL_DIR", val_dir)

    b64 = base64.b64encode(b"image-bytes").decode()
    saved_path = qs.save_training_data("y_001.jpg", b64, "train", "y")

    assert saved_path == str(train_dir / "y_001.jpg")

    listing = qs.list_training_data()
    assert len(listing["train"]) == 1
    assert listing["train"][0]["label"] == "y"
    assert listing["val"] == []


def test_get_config_defaults_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(qs, "CONFIG_PATH", tmp_path / "thresholds.json")
    config = qs.get_config()
    assert config == {
        "similarity_threshold": 0.72,
        "trained": False,
        "train_accuracy": None,
        "val_accuracy": None,
    }


def test_save_and_get_config(monkeypatch, tmp_path):
    config_path = tmp_path / "thresholds.json"
    monkeypatch.setattr(qs, "CONFIG_PATH", config_path)

    qs.save_config({"similarity_threshold": 0.8, "trained": True})

    assert json.loads(config_path.read_text()) == {"similarity_threshold": 0.8, "trained": True}
    assert qs.get_config() == {"similarity_threshold": 0.8, "trained": True}
