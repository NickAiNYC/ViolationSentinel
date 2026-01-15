"""
Unit tests for Token Bucket Rate Limiter

Tests cover:
- Token bucket algorithm correctness
- Burst handling
- Per-user and per-endpoint limits
- Admin bypass
- Redis integration
- Concurrent requests
- Rate limit headers
"""

import pytest
import asyncio
import time
from infrastructure.rate_limiter import RateLimiter, RateLimitExceeded, RateLimitInfo


@pytest.fixture
async def limiter():
    """Create rate limiter instance for testing."""
    limiter = RateLimiter(
        redis_url="redis://localhost:6379",
        default_rate=10,
        default_window=10
    )
    await limiter.connect()
    yield limiter
    await limiter.close()


@pytest.mark.asyncio
async def test_initialization():
    """Test rate limiter initialization."""
    limiter = RateLimiter(default_rate=100, default_window=60)
    assert limiter.default_rate == 100
    assert limiter.default_window == 60
    assert len(limiter.admin_users) == 0


@pytest.mark.asyncio
async def test_successful_acquire(limiter):
    """Test successful token acquisition."""
    user_id = "test_user_1"
    endpoint = "/api/test"
    
    # First request should succeed
    info = await limiter.acquire(user_id, endpoint)
    
    assert info.limit == 10
    assert info.remaining == 9
    assert info.reset_at > int(time.time())


@pytest.mark.asyncio
async def test_burst_allowance(limiter):
    """Test burst handling (multiple requests in quick succession)."""
    user_id = "test_user_burst"
    endpoint = "/api/test"
    
    # Should be able to make 10 requests quickly (full bucket)
    for i in range(10):
        info = await limiter.acquire(user_id, endpoint)
        assert info.remaining == 9 - i
    
    # 11th request should fail
    with pytest.raises(RateLimitExceeded) as exc_info:
        await limiter.acquire(user_id, endpoint)
    
    assert exc_info.value.limit == 10
    assert exc_info.value.retry_after > 0


@pytest.mark.asyncio
async def test_token_refill(limiter):
    """Test that tokens refill over time."""
    user_id = "test_user_refill"
    endpoint = "/api/test"
    
    # Consume all tokens
    for _ in range(10):
        await limiter.acquire(user_id, endpoint)
    
    # Next request should fail
    with pytest.raises(RateLimitExceeded):
        await limiter.acquire(user_id, endpoint)
    
    # Wait for token refill (1 second = 1 token with rate 10/10s)
    await asyncio.sleep(1.5)
    
    # Should succeed now
    info = await limiter.acquire(user_id, endpoint)
    assert info.remaining >= 0


@pytest.mark.asyncio
async def test_per_endpoint_limits(limiter):
    """Test different limits for different endpoints."""
    user_id = "test_user_endpoints"
    
    # Set custom endpoint limits
    limiter.endpoint_limits["/api/fast"] = (20, 10)
    limiter.endpoint_limits["/api/slow"] = (5, 10)
    
    # Fast endpoint should allow 20 requests
    for i in range(20):
        info = await limiter.acquire(user_id, "/api/fast")
        assert info.limit == 20
    
    # Slow endpoint should allow 5 requests
    for i in range(5):
        info = await limiter.acquire(user_id, "/api/slow")
        assert info.limit == 5
    
    # Both should now be exhausted
    with pytest.raises(RateLimitExceeded):
        await limiter.acquire(user_id, "/api/fast")
    
    with pytest.raises(RateLimitExceeded):
        await limiter.acquire(user_id, "/api/slow")


@pytest.mark.asyncio
async def test_admin_bypass(limiter):
    """Test that admin users bypass rate limits."""
    admin_user = "admin_user"
    limiter.add_admin_user(admin_user)
    
    endpoint = "/api/test"
    
    # Admin should be able to make unlimited requests
    for _ in range(100):
        info = await limiter.acquire(admin_user, endpoint)
        assert info.remaining == 10  # Always shows full bucket


@pytest.mark.asyncio
async def test_check_limit_without_consuming(limiter):
    """Test checking limit status without consuming tokens."""
    user_id = "test_user_check"
    endpoint = "/api/test"
    
    # Check initial limit
    info1 = await limiter.check_limit(user_id, endpoint)
    assert info1.remaining == 10
    
    # Consume some tokens
    await limiter.acquire(user_id, endpoint, cost=3)
    
    # Check again (should show 7 remaining)
    info2 = await limiter.check_limit(user_id, endpoint)
    assert info2.remaining == 7


@pytest.mark.asyncio
async def test_reset_limit(limiter):
    """Test manual rate limit reset."""
    user_id = "test_user_reset"
    endpoint = "/api/test"
    
    # Consume all tokens
    for _ in range(10):
        await limiter.acquire(user_id, endpoint)
    
    # Should be exhausted
    with pytest.raises(RateLimitExceeded):
        await limiter.acquire(user_id, endpoint)
    
    # Reset limit
    await limiter.reset_limit(user_id, endpoint)
    
    # Should work again
    info = await limiter.acquire(user_id, endpoint)
    assert info.remaining == 9


@pytest.mark.asyncio
async def test_rate_limit_headers(limiter):
    """Test generation of rate limit headers."""
    info = RateLimitInfo(
        limit=100,
        remaining=75,
        reset_at=1234567890
    )
    
    headers = limiter.get_headers(info)
    
    assert headers["X-RateLimit-Limit"] == "100"
    assert headers["X-RateLimit-Remaining"] == "75"
    assert headers["X-RateLimit-Reset"] == "1234567890"


@pytest.mark.asyncio
async def test_concurrent_requests(limiter):
    """Test rate limiter with concurrent requests."""
    user_id = "test_user_concurrent"
    endpoint = "/api/test"
    
    # Launch 15 concurrent requests (limit is 10)
    tasks = [limiter.acquire(user_id, endpoint) for _ in range(15)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Count successes and failures
    successes = [r for r in results if isinstance(r, RateLimitInfo)]
    failures = [r for r in results if isinstance(r, RateLimitExceeded)]
    
    # Should have 10 successes and 5 failures
    assert len(successes) == 10
    assert len(failures) == 5


@pytest.mark.asyncio
async def test_cost_parameter(limiter):
    """Test custom token cost."""
    user_id = "test_user_cost"
    endpoint = "/api/test"
    
    # Consume 5 tokens at once
    info = await limiter.acquire(user_id, endpoint, cost=5)
    assert info.remaining == 5
    
    # Consume 5 more
    info = await limiter.acquire(user_id, endpoint, cost=5)
    assert info.remaining == 0
    
    # Next request should fail
    with pytest.raises(RateLimitExceeded):
        await limiter.acquire(user_id, endpoint)


@pytest.mark.asyncio
async def test_metrics(limiter):
    """Test metrics collection."""
    # Create some activity
    await limiter.acquire("user1", "/api/test1")
    await limiter.acquire("user2", "/api/test2")
    limiter.add_admin_user("admin1")
    
    metrics = await limiter.get_metrics()
    
    assert metrics["active_limits"] >= 2
    assert metrics["admin_users"] == 1
    assert metrics["configured_endpoints"] > 0


@pytest.mark.asyncio
async def test_per_user_isolation(limiter):
    """Test that users have independent rate limits."""
    endpoint = "/api/test"
    
    # User 1 consumes all tokens
    for _ in range(10):
        await limiter.acquire("user1", endpoint)
    
    # User 1 should be rate limited
    with pytest.raises(RateLimitExceeded):
        await limiter.acquire("user1", endpoint)
    
    # User 2 should still have full bucket
    info = await limiter.acquire("user2", endpoint)
    assert info.remaining == 9


if __name__ == "__main__":
    print("Running rate limiter tests...")
    print("=" * 60)
    
    # Run tests
    pytest.main([__file__, "-v", "-s"])
