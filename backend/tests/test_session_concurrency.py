import asyncio
import pytest

from backend.rag_service import EmbeddingService
from backend.database import engine


@pytest.mark.asyncio
async def test_sessions_close_under_concurrency():
    async def run_task():
        service = EmbeddingService()
        await service._get_db_config()

    await asyncio.gather(*[run_task() for _ in range(5)])
    assert engine.pool.checkedout() == 0
