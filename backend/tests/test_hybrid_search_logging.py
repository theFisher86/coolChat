import base64
import logging
from types import SimpleNamespace

import numpy as np
import pytest

from backend.hybrid_search import HybridSearch
from backend.models import Lorebook, LoreEntry


class DummyEmbeddingService:
    def __init__(self):
        self._vector = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        self._embedding_b64 = base64.b64encode(self._vector.tobytes()).decode("utf-8")
        self.config = SimpleNamespace(
            provider="dummy",
            keyword_weight=0.5,
            semantic_weight=0.5,
            top_k_candidates=10,
            dimensions=3,
        )

    async def _ensure_initialized(self):
        return

    async def generate_embedding(self, text: str) -> str:
        return self._embedding_b64

    def decode_embedding(self, b64: str) -> np.ndarray:
        return np.frombuffer(base64.b64decode(b64), dtype=np.float32)

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return 1.0


@pytest.mark.asyncio
async def test_debug_logging_does_not_affect_search(caplog):
    dummy_service = DummyEmbeddingService()
    searcher = HybridSearch(embedding_service=dummy_service)

    lorebook = Lorebook(id=1, name="Test Book")
    entry = LoreEntry(
        id=1,
        lorebook=lorebook,
        title="Magic Wand",
        content="A magic wand glows brightly.",
        keywords=["magic"],
        secondary_keywords=[],
        logic="AND ANY",
        trigger=100.0,
        order=0.0,
        embedding=dummy_service._embedding_b64,
        embedding_dimensions=3,
    )
    entry.keyword_score = searcher._calculate_keyword_score(entry, ["magic"])

    async def fake_get_keyword_candidates(self, query, db_session, limit):
        return [entry]

    searcher._get_keyword_candidates = fake_get_keyword_candidates.__get__(searcher, HybridSearch)

    with caplog.at_level(logging.DEBUG):
        results = await searcher.search("magic", limit=5)

    assert len(results) == 1
    assert results[0]["title"] == "Magic Wand"
    assert any("HYBRID SEARCH" in record.message for record in caplog.records)
