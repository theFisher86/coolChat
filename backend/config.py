#!/usr/bin/env python3
"""CoolChat Configuration - Database-backed with JSON backup support"""

import os
from typing import Dict, Optional
from enum import Enum
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import json
from pathlib import Path

load_dotenv()

# Database imports for settings persistence
from .database import SessionLocal
from .models import AppSettings

# Provider enums
class Provider(str, Enum):
    ECHO = "echo"
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    POLLINATIONS = "pollinations"

class ImageProvider(str, Enum):
    POLLINATIONS = "pollinations"
    DEZGO = "dezgo"

# Config models
class ProviderConfig(BaseModel):
    api_key: Optional[str] = None
    api_base: str = ""
    model: str = ""
    temperature: float = 0.7
    # Image provider specific fields
    lora_flux_1: Optional[str] = None
    lora_flux_2: Optional[str] = None
    lora_sd1_1: Optional[str] = None
    lora_sd1_2: Optional[str] = None
    lora1_strength: Optional[float] = None
    lora2_strength: Optional[float] = None
    transparent: Optional[bool] = None
    upscale: Optional[bool] = None
    width: Optional[int] = None
    height: Optional[int] = None
    steps: Optional[int] = None

class ImagesConfig(BaseModel):
    active: ImageProvider = ImageProvider.POLLINATIONS
    pollinations: ProviderConfig = Field(default_factory=ProviderConfig)
    dezgo: ProviderConfig = Field(default_factory=ProviderConfig)

class UserPersona(BaseModel):
    name: str = "User"
    description: str = ""
    personality: str = ""
    motivations: str = ""
    tracking: str = ""

class DebugConfig(BaseModel):
    log_prompts: bool = False
    log_responses: bool = False

class AppearanceConfig(BaseModel):
    primary: str = "#3B82F6"
    secondary: str = "#64748B"
    text1: str = "#E5E7EB"
    text2: str = "#CBD5E1"
    highlight: str = "#FFFFFF"
    lowlight: str = "#374151"
    phone_style: str = "normal"
    background_animations: list[str] = []

class AppConfig(BaseModel):
    active_provider: Provider = Provider.ECHO
    active_character_id: Optional[int] = None
    providers: Dict[str, ProviderConfig] = Field(default_factory=lambda: {
        Provider.ECHO.value: ProviderConfig(),
        Provider.OPENAI.value: ProviderConfig(api_base="https://api.openai.com/v1"),
        Provider.OPENROUTER.value: ProviderConfig(api_base="https://openrouter.ai/api/v1"),
        Provider.GEMINI.value: ProviderConfig(),
    })
    debug: Optional[DebugConfig] = None
    user_persona: Optional[UserPersona] = None
    max_context_tokens: int = 2048
    structured_output: bool = False
    images: ImagesConfig = Field(default_factory=ImagesConfig)
    theme: Optional[AppearanceConfig] = None
    active_lorebook_ids: Optional[list[int]] = None
    extensions: Optional[dict] = None

    # RAG Configuration (added)
    rag_provider: str = Field(default_factory=lambda: os.getenv("RAG_PROVIDER", "ollama"))
    rag_keyword_weight: float = 0.6
    rag_semantic_weight: float = 0.4
    rag_similarity_threshold: float = 0.5

def _ensure_config_path() -> Path:
    path = Path(__file__).parent.parent / "config.json"
    return path

def load_config() -> AppConfig:
    """Load configuration from database, with fallback to config.json"""
    # First try loading from database
    try:
        with SessionLocal() as db:
            setting = db.query(AppSettings).filter(AppSettings.key == "main_config").first()
            if setting:
                print(f"[Config] Loaded from database: active_provider={setting.value.get('active_provider', 'unknown')}")
                data = setting.value
                return AppConfig(**data)
            else:
                print("[Config] No config found in database, will try fallback")
    except Exception as e:
        print(f"[Config] Database load failed: {e}, trying fallback file")

    # Fallback to config.json if database load fails
    try:
        path = _ensure_config_path()
        if path.exists():
            data = json.loads(path.read_text())
            print(f"[Config] Loading from fallback file: {path.name} (active_provider={data.get('active_provider', 'unknown')})")
            # Migrate to database on first load
            try:
                with SessionLocal() as db:
                    existing = db.query(AppSettings).filter(AppSettings.key == "main_config").first()
                    if not existing:
                        setting = AppSettings(key="main_config", value=data)
                        db.add(setting)
                        db.commit()
                        print("[Config] Migrated fallback data to database")
                    else:
                        print("[Config] Migration skipped (database already has data)")
            except Exception as e:
                print(f"[Config] Migration failed: {e}")
            return AppConfig(**data)
        else:
            print(f"[Config] Fallback file not found: {path}, using default config")
            return AppConfig()
    except Exception as e:
        print(f"[Config] Fallback load failed: {e}, using default config")
        return AppConfig()

def save_config(config: AppConfig) -> None:
    """Save configuration to database and config.json for backup/sharing"""
    config_dict = config.model_dump()

    # Save to database (primary storage)
    try:
        with SessionLocal() as db:
            setting = db.query(AppSettings).filter(AppSettings.key == "main_config").first()
            if setting:
                setting.value = config_dict
                setting.updated_at = None  # Auto-update timestamp
            else:
                setting = AppSettings(key="main_config", value=config_dict)
                db.add(setting)
            db.commit()
    except Exception as e:
        print(f"Failed to save config to database: {e}")

    # Also save to config.json for backup and sharing
    try:
        path = Path(__file__).parent.parent / "config.json"
        path.write_text(json.dumps(config_dict, indent=2))
    except Exception as e:
        print(f"Failed to save config.json backup: {e}")

def mask_secret(value: Optional[str]) -> Optional[str]:
    """Mask sensitive values"""
    if not value:
        return None
    if len(value) <= 4:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]

# RAG-specific configuration helpers
class Config:
    """Application configuration with environment variable support"""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///backend/app.db")

    # Ollama Configuration
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "nomic-embed-text:latest")

    # Google Gemini Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "models/text-embedding-004")

    # RAG Configuration Defaults
    RAG_PROVIDER: str = os.getenv("RAG_PROVIDER", "ollama")
    RAG_KEYWORD_WEIGHT: float = float(os.getenv("RAG_KEYWORD_WEIGHT", "0.6"))
    RAG_SEMANTIC_WEIGHT: float = float(os.getenv("RAG_SEMANTIC_WEIGHT", "0.4"))
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.5"))
    RAG_TOP_K_CANDIDATES: int = int(os.getenv("RAG_TOP_K_CANDIDATES", "200"))
    RAG_BATCH_SIZE: int = int(os.getenv("RAG_BATCH_SIZE", "32"))
    RAG_AUTO_REGENERATE: bool = os.getenv("RAG_AUTO_REGENERATE", "true").lower() == "true"

    # Debug Configuration
    RAG_DEBUG: bool = os.getenv("RAG_DEBUG", "false").lower() == "true"
    RAG_LOG_LEVEL: str = os.getenv("RAG_LOG_LEVEL", "INFO")

    @classmethod
    def create_rag_config_dict(cls) -> dict:
        """Convert RAG config to dictionary for database insertion"""
        return {
            "provider": cls.RAG_PROVIDER,
            "ollama_base_url": cls.OLLAMA_BASE_URL,
            "ollama_model": cls.OLLAMA_MODEL,
            "gemini_api_key": cls.GEMINI_API_KEY or "",
            "gemini_model": cls.GEMINI_MODEL,
            "top_k_candidates": cls.RAG_TOP_K_CANDIDATES,
            "keyword_weight": cls.RAG_KEYWORD_WEIGHT,
            "semantic_weight": cls.RAG_SEMANTIC_WEIGHT,
            "similarity_threshold": cls.RAG_SIMILARITY_THRESHOLD,
            "batch_size": cls.RAG_BATCH_SIZE,
            "regenerate_on_content_update": cls.RAG_AUTO_REGENERATE,
            "embedding_dimensions": 384 if cls.RAG_PROVIDER == "ollama" else 768
        }

# Global instances
config = Config()

# Original app config instance for backward compatibility
app_config = AppConfig()
