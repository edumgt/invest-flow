"""정품/불량품 검사 파일 저장소 및 classify.py 호출 래퍼."""
import base64
import json
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

from .. import config

DATA_ROOT = Path(config.DATA_ROOT)
ORIGINAL_PATH = DATA_ROOT / "50597846-precision-mechanics.avif"
TRAIN_DIR = DATA_ROOT / "train"
VAL_DIR = DATA_ROOT / "val"
MODEL_DIR = DATA_ROOT / "model"
CONFIG_PATH = MODEL_DIR / "thresholds.json"
CLASSIFY_PY = Path(__file__).resolve().parent.parent / "classify.py"

_IMAGE_EXT_RE = re.compile(r"\.(jpg|jpeg|png|webp)$", re.IGNORECASE)

for d in (TRAIN_DIR, VAL_DIR, MODEL_DIR):
    d.mkdir(parents=True, exist_ok=True)


def get_original() -> dict | None:
    if not ORIGINAL_PATH.exists():
        return None
    return {"base64": base64.b64encode(ORIGINAL_PATH.read_bytes()).decode(), "mimeType": "image/avif"}


def save_training_data(filename: str, b64: str, split: str, label: str) -> str:
    directory = VAL_DIR if split == "val" else TRAIN_DIR
    out_path = directory / filename
    out_path.write_bytes(base64.b64decode(b64))
    return str(out_path)


def list_training_data() -> dict:
    def _list(directory: Path, split: str) -> list[dict]:
        if not directory.exists():
            return []
        items = []
        for f in sorted(directory.iterdir()):
            if not _IMAGE_EXT_RE.search(f.name):
                continue
            label = "y" if f.name.startswith("y_") else "n" if f.name.startswith("n_") else "?"
            items.append({
                "filename": f.name,
                "split": split,
                "label": label,
                "base64": base64.b64encode(f.read_bytes()).decode(),
            })
        return items

    return {"train": _list(TRAIN_DIR, "train"), "val": _list(VAL_DIR, "val")}


def save_config(body: dict) -> str:
    CONFIG_PATH.write_text(json.dumps(body, indent=2, ensure_ascii=False))
    return str(CONFIG_PATH)


def get_config() -> dict:
    if not CONFIG_PATH.exists():
        return {
            "similarity_threshold": 0.72,
            "trained": False,
            "train_accuracy": None,
            "val_accuracy": None,
        }
    return json.loads(CONFIG_PATH.read_text())


def classify_image(b64: str, mime_type: str) -> dict:
    ext = ".png" if "png" in mime_type else ".webp" if "webp" in mime_type else ".jpg"
    tmp_path = Path(tempfile.gettempdir()) / f"qc_{uuid.uuid4()}{ext}"
    tmp_path.write_bytes(base64.b64decode(b64))

    env = {
        **os.environ,
        "ORIGINAL_IMAGE": str(ORIGINAL_PATH),
        "THRESHOLD_FILE": str(CONFIG_PATH),
        "OLLAMA_URL": config.OLLAMA_URL,
        "OLLAMA_VISION_MODEL": config.OLLAMA_VISION_MODEL,
    }
    try:
        proc = subprocess.run(
            ["python3", str(CLASSIFY_PY), str(tmp_path)],
            env=env, capture_output=True, text=True, timeout=180,
        )
        if proc.stderr:
            print(f"[classify] {proc.stderr.strip()}")
        return json.loads(proc.stdout.strip())
    finally:
        tmp_path.unlink(missing_ok=True)
