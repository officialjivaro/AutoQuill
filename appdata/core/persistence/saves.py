# appdata/core/persistence/saves.py
import json, os
from pathlib import Path
from typing import List, Optional

_BASE_DIR = Path(os.path.expanduser("~")) / "Jivaro" / "AutoQuill" / "Data" / "Saves"


def get_saves_dir() -> Path:
    _BASE_DIR.mkdir(parents=True, exist_ok=True)
    return _BASE_DIR


def list_saves() -> List[str]:
    return sorted(p.stem for p in get_saves_dir().glob("*.json"))


def save_config(cfg: dict, name: str) -> None:
    name = name.strip()
    if not name:
        return
    path = get_saves_dir() / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def load_config(name: str) -> Optional[dict]:
    name = name.strip()
    if not name:
        return None
    path = get_saves_dir() / f"{name}.json"
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None
