from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import json
import os


def public_dir() -> Path:
    here = Path(__file__).resolve().parent
    return (here / ".." / "public").resolve()


def _path(name: str) -> Path:
    d = public_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / name


def load_json(name: str, default: Any) -> Any:
    p = _path(name)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(name: str, data: Any) -> None:
    p = _path(name)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)

