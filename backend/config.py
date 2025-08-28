from __future__ import annotations

from pathlib import Path
from typing import Optional
from pydantic import BaseModel
import json
import os


DEFAULT_MODEL = "gpt-4o-mini"


def _default_config_dir() -> Path:
    # Prefer XDG if available, else ~/.coolchat
    xdg = os.getenv("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "coolchat"
    return Path.home() / ".coolchat"


def _default_config_path() -> Path:
    env = os.getenv("COOLCHAT_CONFIG_PATH")
    if env:
        return Path(env)
    return _default_config_dir() / "config.json"


class Provider(str):
    ECHO = "echo"
    OPENAI = "openai"  # OpenAI or compatible endpoint
    OPENROUTER = "openrouter"  # OpenRouter (OpenAI-compatible)
    GEMINI = "gemini"  # Google Generative Language API


class AppConfig(BaseModel):
    provider: str = Provider.ECHO
    api_key: Optional[str] = None
    api_base: str = "https://api.openai.com/v1"
    model: str = DEFAULT_MODEL
    temperature: float = 0.7


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_config(path: Optional[Path] = None) -> AppConfig:
    cfg_path = path or _default_config_path()
    if not cfg_path.exists():
        # Create with defaults
        cfg = AppConfig()
        save_config(cfg, cfg_path)
        return cfg
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return AppConfig(**data)
    except Exception:
        # On error, fallback to defaults but do not overwrite user's file
        return AppConfig()


def save_config(cfg: AppConfig, path: Optional[Path] = None) -> None:
    cfg_path = path or _default_config_path()
    ensure_parent(cfg_path)
    cfg_path.write_text(cfg.model_dump_json(indent=2), encoding="utf-8")


def mask_secret(secret: Optional[str]) -> Optional[str]:
    if not secret:
        return secret
    if len(secret) <= 6:
        return "*" * len(secret)
    return secret[:3] + "*" * (len(secret) - 7) + secret[-4:]
