import asyncio
from backend.routers.lore import RateLimiter


def test_rate_limiter_allows_within_limit():
    async def run():
        limiter = RateLimiter(requests_per_minute=2)
        assert await limiter.is_allowed("client") is True
        assert await limiter.is_allowed("client") is True
    asyncio.run(run())


def test_rate_limiter_throttles_when_exceeded():
    async def run():
        limiter = RateLimiter(requests_per_minute=2)
        await limiter.is_allowed("client")
        await limiter.is_allowed("client")
        assert await limiter.is_allowed("client") is False
    asyncio.run(run())
