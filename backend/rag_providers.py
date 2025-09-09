#!/usr/bin/env python3
"""RAG Embedding Providers Module"""

import asyncio
import base64
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Any

import httpx
import numpy as np

from .models import RAGConfig

# Configure logging
logger = logging.getLogger(__name__)

class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'ollama', 'gemini')"""
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text. Returns numpy array of floats."""
        pass

    @abstractmethod
    def get_dimensions(self) -> int:
        """Return the expected dimensions for this provider's embeddings"""
        pass

    async def generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts. Default implementation calls single method."""
        tasks = [self.generate_embedding(text) for text in texts]
        return await asyncio.gather(*tasks)


class OllamaProvider(EmbeddingProvider):
    """Embedding provider for Ollama local models"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text:latest"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._dimensions = 384  # Default for nomic-embed-text
        self._client = None

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def get_dimensions(self) -> int:
        return self._dimensions

    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding using Ollama API"""
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(self._dimensions, dtype=np.float32)

        try:
            payload = {
                "model": self.model,
                "prompt": text.strip()
            }

            response = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                raise Exception(f"Ollama API returned {response.status_code}: {response.text}")

            result = response.json()

            if "embedding" not in result:
                logger.error(f"Unexpected Ollama response format: {result}")
                raise Exception("Invalid response format from Ollama API")

            embedding = np.array(result["embedding"], dtype=np.float32)

            # Validate dimensions
            if embedding.shape[0] != self._dimensions:
                logger.warning(f"Dimension mismatch: expected {self._dimensions}, got {embedding.shape[0]}")
                self._dimensions = embedding.shape[0]

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding with Ollama: {e}")
            # Return zero vector as fallback
            return np.zeros(self._dimensions, dtype=np.float32)

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


class GeminiProvider(EmbeddingProvider):
    """Embedding provider for Google Gemini"""

    def __init__(self, api_key: str, model: str = "models/text-embedding-004"):
        self.api_key = api_key
        self.model = model
        self._dimensions = 768  # Google embedding-004 dimensions
        self._client = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://generativelanguage.googleapis.com",
                timeout=30.0
            )
        return self._client

    def get_dimensions(self) -> int:
        return self._dimensions

    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding using Gemini API"""
        if not text or not text.strip():
            return np.zeros(self._dimensions, dtype=np.float32)

        if not self.api_key:
            logger.error("Gemini API key not configured")
            return np.zeros(self._dimensions, dtype=np.float32)

        try:
            # Prepare content for Gemini API
            content = {
                "parts": [{"text": text.strip()}]
            }

            payload = {
                "content": content,
                "taskType": "RETRIEVAL_DOCUMENT" if len(text) > 500 else "RETRIEVAL_QUERY"
            }

            response = await self.client.post(
                f"/v1beta/{self.model}:embedContent?key={self.api_key}",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                raise Exception(f"Gemini API returned {response.status_code}: {response.text}")

            result = response.json()

            if "embedding" not in result or "values" not in result["embedding"]:
                logger.error(f"Unexpected Gemini response format: {result}")
                raise Exception("Invalid response format from Gemini API")

            embedding = np.array(result["embedding"]["values"], dtype=np.float32)

            # Validate dimensions
            if embedding.shape[0] != self._dimensions:
                logger.warning(f"Dimension mismatch: expected {self._dimensions}, got {embedding.shape[0]}")
                self._dimensions = embedding.shape[0]

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding with Gemini: {e}")
            return np.zeros(self._dimensions, dtype=np.float32)

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


def create_provider(config: RAGConfig) -> EmbeddingProvider:
    """Factory function to create the appropriate provider based on config"""

    if config.provider == "ollama":
        return OllamaProvider(
            base_url=config.ollama_base_url,
            model=config.ollama_model
        )
    elif config.provider == "gemini":
        if not config.gemini_api_key:
            logger.warning("Gemini provider selected but no API key configured")
            raise ValueError("Gemini API key is required for Gemini provider")
        return GeminiProvider(
            api_key=config.gemini_api_key,
            model=config.gemini_model
        )
    else:
        # Default to Ollama
        logger.warning(f"Unknown provider '{config.provider}', falling back to Ollama")
        return OllamaProvider(
            base_url=config.ollama_base_url,
            model=config.ollama_model
        )