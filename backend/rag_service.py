#!/usr/bin/env python3
"""RAG Embedding Service Module"""

import asyncio
import base64
import logging
from datetime import datetime
from typing import List, Optional, Any, Union
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from .models import RAGConfig, LoreEntry
from .rag_providers import create_provider, EmbeddingProvider
from .database import get_db

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class EmbeddingConfig:
    """Configuration for embedding operations"""
    provider: str
    model: str
    dimensions: int
    batch_size: int
    top_k_candidates: int
    keyword_weight: float
    semantic_weight: float
    similarity_threshold: float
    regenerate_on_update: bool

    @classmethod
    def from_db_config(cls, config: RAGConfig) -> 'EmbeddingConfig':
        return cls(
            provider=config.provider,
            model=config.ollama_model if config.provider == "ollama" else config.gemini_model,
            dimensions=config.embedding_dimensions,
            batch_size=config.batch_size,
            top_k_candidates=config.top_k_candidates,
            keyword_weight=config.keyword_weight,
            semantic_weight=config.semantic_weight,
            similarity_threshold=config.similarity_threshold,
            regenerate_on_update=bool(config.regenerate_on_content_update)
        )


class EmbeddingService:
    """Service for managing vector embeddings"""

    def __init__(self, db_session: Optional[Session] = None):
        self._db = db_session
        self._config: Optional[EmbeddingConfig] = None
        self._provider: Optional[EmbeddingProvider] = None

    async def _ensure_initialized(self):
        """Ensure provider and config are loaded"""
        if self._config is None or self._provider is None:
            await self._load_config()
            self._provider = create_provider(await self._get_db_config())

    async def _load_config(self):
        """Load configuration from database"""
        if self._config is not None:
            return

        config_record = await self._get_db_config()
        self._config = EmbeddingConfig.from_db_config(config_record)

    async def _get_db_config(self) -> RAGConfig:
        """Get RAG configuration from database"""
        db = self._db if self._db else next(get_db())
        try:
            config = db.query(RAGConfig).first()
            if not config:
                # Create default config if none exists
                config = RAGConfig()
                db.add(config)
                db.commit()
                db.refresh(config)
            return config
        finally:
            if not self._db:
                db.close()

    async def generate_embedding(self, text: str) -> str:
        """Generate embedding and return as base64 encoded string"""
        await self._ensure_initialized()

        embedding_array = await self._provider.generate_embedding(text)
        return base64.b64encode(embedding_array.tobytes()).decode('utf-8')

    async def generate_embeddings_batch(self, texts: List[str]) -> List[str]:
        """Generate embeddings for multiple texts"""
        await self._ensure_initialized()

        embedding_arrays = await self._provider.generate_embeddings_batch(texts)
        return [
            base64.b64encode(arr.tobytes()).decode('utf-8')
            for arr in embedding_arrays
        ]

    async def generate_lore_entry_embedding(self, lore_entry: LoreEntry) -> str:
        """Generate embedding for a lore entry using title + content"""
        # Combine title and content for embedding
        text = f"{lore_entry.title or ''} {lore_entry.content}".strip()
        logger.info(f"Generating embedding for lore entry {lore_entry.id}: '{text[:50]}...'")

        embedding_b64 = await self.generate_embedding(text)

        # Update the lore entry in database
        db = self._db if self._db else next(get_db())
        try:
            entry = db.query(LoreEntry).filter(LoreEntry.id == lore_entry.id).first()
            if entry:
                await self._load_config()
                entry.embedding = embedding_b64
                entry.embedding_model = self._config.model
                entry.embedding_dimensions = self._config.dimensions
                entry.embedding_updated_at = datetime.now()
                entry.embedding_provider = self._provider.provider_name

                db.commit()
                logger.info(f"Updated embedding for lore entry {lore_entry.id}")
        finally:
            if not self._db:
                db.close()

        return embedding_b64

    def decode_embedding(self, embedding_b64: str) -> np.ndarray:
        """Decode base64 embedding back to numpy array"""
        if not embedding_b64:
            return np.array([])

        try:
            embedding_bytes = base64.b64decode(embedding_b64)
            return np.frombuffer(embedding_bytes, dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to decode embedding: {e}")
            return np.array([])

    def encode_embedding(self, embedding_array: np.ndarray) -> str:
        """Encode numpy array to base64 string"""
        return base64.b64encode(embedding_array.tobytes()).decode('utf-8')

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        if a.size == 0 or b.size == 0:
            return 0.0

        # Ensure same dimensions
        min_dim = min(len(a), len(b))
        a_norm = a[:min_dim]
        b_norm = b[:min_dim]

        # Compute cosine similarity
        dot_product = np.dot(a_norm, b_norm)
        norm_a = np.linalg.norm(a_norm)
        norm_b = np.linalg.norm(b_norm)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    async def batch_process_lore_entries(self, entries: List[LoreEntry]):
        """Process multiple lore entries for embedding generation"""
        await self._ensure_initialized()

        texts = [f"{entry.title or ''} {entry.content}".strip() for entry in entries]
        embedding_strings = await self.generate_embeddings_batch(texts)

        # Update database
        db = self._db if self._db else next(get_db())
        try:
            for entry, embedding_b64 in zip(entries, embedding_strings):
                entry_db = db.query(LoreEntry).filter(LoreEntry.id == entry.id).first()
                if entry_db:
                    entry_db.embedding = embedding_b64
                    entry_db.embedding_model = self._config.model
                    entry_db.embedding_dimensions = self._config.dimensions
                    entry_db.embedding_updated_at = datetime.now()
                    entry_db.embedding_provider = self._provider.provider_name

            db.commit()
            logger.info(f"Batch processed {len(entries)} lore entries")
        finally:
            if not self._db:
                db.close()

    async def get_similar_entries(self, query_embedding: str, limit: int = 10) -> List[LoreEntry]:
        """Find lore entries similar to query embedding"""
        await self._ensure_initialized()

        query_vector = self.decode_embedding(query_embedding)

        # Get all entries with embeddings
        db = self._db if self._db else next(get_db())
        try:
            # Use flexible dimension matching - prefer config dimensions, but allow backward compatibility
            entries_exact = db.query(LoreEntry).filter(
                LoreEntry.embedding.isnot(None),
                LoreEntry.embedding_dimensions == self._config.dimensions
            ).all()

            entries_compatible = db.query(LoreEntry).filter(
                LoreEntry.embedding.isnot(None),
                LoreEntry.embedding_dimensions == query_dims
            ).all()

            # Combine and deduplicate
            all_entries = list({entry.id: entry for entry in entries_exact + entries_compatible}.values())

            logger.info(f"Found {len(entries_exact)} entries with config dimensions, "
                       f"{len(entries_compatible)} with query dimensions")

            similarities = []
            for entry in all_entries:
                try:
                    entry_vector = self.decode_embedding(entry.embedding)
                    similarity = self.cosine_similarity(query_vector, entry_vector)
                    if similarity >= self._config.similarity_threshold:
                        similarities.append((entry, similarity))
                except Exception as e:
                    logger.warning(f"Error processing embedding for entry {entry.id}: {e}")

            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Return top results
            similar_entries = [entry for entry, _ in similarities[:limit]]
            logger.info(f"Found {len(similar_entries)} similar entries for query")
            return similar_entries

        finally:
            if not self._db:
                db.close()

    async def close(self):
        """Close provider resources"""
        if self._provider and hasattr(self._provider, 'close'):
            await self._provider.close()

    @property
    def config(self) -> EmbeddingConfig:
        return self._config

    @property
    def provider(self) -> EmbeddingProvider:
        return self._provider


# Global service instance
_rag_service: Optional[EmbeddingService] = None

def get_rag_service(db_session: Optional[Session] = None) -> EmbeddingService:
    """Get or create the RAG service instance"""
    global _rag_service
    if _rag_service is None or (db_session and db_session != _rag_service._db):
        _rag_service = EmbeddingService(db_session)
    return _rag_service

async def initialize_rag_service():
    """Initialize the RAG service with configuration"""
    service = get_rag_service()
    await service._ensure_initialized()
    return service