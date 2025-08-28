from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any
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


class ProviderConfig(BaseModel):
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7


class UserPersona(BaseModel):
    name: str = "User"
    description: str = ""
    personality: str = ""
    motivations: str = ""
    tracking: str = ""


class DebugConfig(BaseModel):
    log_prompts: bool = False
    log_responses: bool = False


class AppConfig(BaseModel):
    active_provider: str = Provider.ECHO
    providers: Dict[str, ProviderConfig]
    active_character_id: Optional[int] = None
    user_persona: UserPersona = UserPersona()
    debug: DebugConfig = DebugConfig()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _default_providers() -> Dict[str, ProviderConfig]:
    return {
        Provider.ECHO: ProviderConfig(),
        Provider.OPENAI: ProviderConfig(api_base="https://api.openai.com/v1", model=DEFAULT_MODEL),
        Provider.OPENROUTER: ProviderConfig(api_base="https://openrouter.ai/api/v1", model="openrouter/auto"),
        Provider.GEMINI: ProviderConfig(api_base="https://generativelanguage.googleapis.com/v1beta/openai", model="gemini-1.5-flash"),
    }


def load_config(path: Optional[Path] = None) -> AppConfig:
    cfg_path = path or _default_config_path()
    if not cfg_path.exists():
        # Create with defaults
        cfg = AppConfig(active_provider=Provider.ECHO, providers=_default_providers())
        save_config(cfg, cfg_path)
        return cfg
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        # Migrate from old flat schema if needed
        if isinstance(data, dict) and "providers" not in data and "provider" in data:
            old = data
            active = old.get("provider", Provider.ECHO)
            provs = _default_providers()
            pc = provs.get(active, ProviderConfig())
            # Copy fields where present
            pc.api_key = old.get("api_key")
            pc.api_base = old.get("api_base", pc.api_base)
            pc.model = old.get("model", pc.model)
            try:
                pc.temperature = float(old.get("temperature", pc.temperature))
            except Exception:
                pass
            migrated = AppConfig(active_provider=active, providers=provs)
            # Save migration back
            save_config(migrated, cfg_path)
            return migrated
        # Ensure default fields exist when older config versions are read
        if "providers" in data and "active_provider" in data:
            # backfill nested fields
            if "user_persona" not in data:
                data["user_persona"] = UserPersona().model_dump()
            if "debug" not in data:
                data["debug"] = DebugConfig().model_dump()
        return AppConfig(**data)
    except Exception:
        # On error, fallback to defaults but do not overwrite user's file
        return AppConfig(active_provider=Provider.ECHO, providers=_default_providers())


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
