#!/usr/bin/env python3
"""CoolChat Configuration - Original + RAG Support"""

import os
from typing import Dict, Optional
from enum import Enum
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import json
from pathlib import Path

load_dotenv()

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
    background_animations: bool = True

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
    path = Path(__file__).parent.parent / "debug.json"
    return path

def load_config() -> AppConfig:
    """Load configuration from debug.json"""
    try:
        path = _ensure_config_path()
        if path.exists():
            data = json.loads(path.read_text())
            return AppConfig(**data)
        else:
            return AppConfig()
    except Exception:
        return AppConfig()

def save_config(config: AppConfig) -> None:
    """Save configuration to debug.json"""
    try:
        path = _ensure_config_path()
        path.write_text(config.model_dump_json(indent=2))
    except Exception as e:
        print(f"Failed to save config: {e}")

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
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///app.db")

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
