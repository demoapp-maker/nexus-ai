import json

import httpx
import pytest
from logic.ai_service import AIService
from logic.security import SlidingWindowRateLimiter, validate_public_http_url


def test_admin_tool_url_rejects_private_targets():
    with pytest.raises(ValueError):
        validate_public_http_url("http://127.0.0.1:8000/admin/config")
    with pytest.raises(ValueError):
        validate_public_http_url("file:///etc/passwd")


def test_rate_limiter_has_a_bounded_window():
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("client", 100.0)
    assert limiter.allow("client", 101.0)
    assert not limiter.allow("client", 102.0)
    assert limiter.allow("client", 161.0)


@pytest.mark.asyncio
async def test_provider_tool_call_deltas_are_aggregated():
    response = httpx.Response(
        200,
        content=(
            b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","type":"function","function":{"name":"web_","arguments":"{\\"q"}}]}}]}\n\n'
            b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"name":"search","arguments":"uery\\":\\"nexus\\"}"}}]}}]}\n\n'
            b'data: [DONE]\n\n'
        ),
    )
    service = AIService()
    events = []
    async for kind, value in service._consume_sse(response):
        events.append((kind, value))

    assert len(events) == 1
    kind, calls = events[0]
    assert kind == "tool_calls"
    assert calls[0]["id"] == "call_1"
    assert calls[0]["function"]["name"] == "web_search"
    assert json.loads(calls[0]["function"]["arguments"]) == {"query": "nexus"}


def test_calculator_does_not_execute_python():
    service = AIService()
    assert service._safe_calculate("2 + 3 * 4") == 14
    with pytest.raises((ValueError, SyntaxError)):
        service._safe_calculate("__import__('os').system('id')")
