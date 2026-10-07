from types import SimpleNamespace

from logic.admin_settings import (
    _default_runtime_config,
    _is_legacy_openrouter_default,
    _normalize_base_url,
    get_provider_headers,
    normalize_provider,
)
from logic.ai_service import AIService


def test_omniroute_is_the_default_openai_compatible_gateway(monkeypatch):
    monkeypatch.delenv("DEFAULT_AI_PROVIDER", raising=False)
    monkeypatch.delenv("OMNIROUTE_URL", raising=False)
    monkeypatch.delenv("OMNIROUTE_API_KEY", raising=False)
    monkeypatch.delenv("OMNIROUTE_MODEL", raising=False)

    config = _default_runtime_config()

    assert config["provider"] == "omniroute"
    assert config["base_url"] == "http://127.0.0.1:20128/v1/chat/completions"
    assert config["model"] == "auto"
    assert "Authorization" not in get_provider_headers(config)


def test_legacy_generated_openrouter_config_is_migration_safe():
    generated_default = SimpleNamespace(
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1/chat/completions",
        api_key="",
        model="openrouter/free",
        fallback_models=[],
    )
    explicit_config = SimpleNamespace(
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1/chat/completions",
        api_key="encrypted-key",
        model="openrouter/free",
        fallback_models=[],
    )

    assert _is_legacy_openrouter_default(generated_default)
    assert not _is_legacy_openrouter_default(explicit_config)


def test_omniroute_aliases_and_url_normalization():
    assert normalize_provider("OpenAI-Compatible") == "omniroute"
    assert normalize_provider("omni_route") == "omniroute"
    assert (
        _normalize_base_url("omniroute", "http://gateway:20128/v1")
        == "http://gateway:20128/v1/chat/completions"
    )
    assert (
        _normalize_base_url(
            "omniroute", "http://gateway:20128/v1/chat/completions"
        )
        == "http://gateway:20128/v1/chat/completions"
    )


def test_omniroute_auto_model_replaces_legacy_router_models(monkeypatch):
    monkeypatch.setenv("DEFAULT_AI_PROVIDER", "omniroute")
    monkeypatch.setenv("OMNIROUTE_MODEL", "auto")
    service = AIService()
    config = {
        "provider": "omniroute",
        "base_url": "http://127.0.0.1:20128/v1/chat/completions",
        "api_key": "",
        "model": "auto",
    }

    assert service.resolve_model("qwen/qwen3-coder:free", config) == "auto"
    assert service.resolve_model("openrouter/free", config) == "auto"
    assert service.resolve_model("auto/fast", config) == "auto/fast"
    assert (
        service.resolve_model(
            "auto",
            {
                "provider": "openrouter",
                "model": "openrouter/free",
            },
        )
        == "openrouter/free"
    )


def test_non_streaming_request_uses_openai_chat_completions_contract(monkeypatch):
    service = AIService()
    config = {
        "provider": "omniroute",
        "base_url": "http://omniroute.internal/v1/chat/completions",
        "api_key": "gateway-secret",
        "model": "auto",
        "fallback_models": [],
        "extra_headers": {},
    }
    monkeypatch.setattr(service, "_load_runtime_config", lambda: config)
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "gateway-ok"}}]}

    def fake_post(url, json, headers, timeout):
        captured.update(
            {"url": url, "payload": json, "headers": headers, "timeout": timeout}
        )
        return FakeResponse()

    monkeypatch.setattr("logic.ai_service.requests.post", fake_post)

    response = service.call_ai("hello", model="openrouter/free")

    assert response == "gateway-ok"
    assert captured["url"] == "http://omniroute.internal/v1/chat/completions"
    assert captured["payload"]["model"] == "auto"
    assert captured["payload"]["messages"][-1] == {
        "role": "user",
        "content": "hello",
    }
    assert captured["headers"]["Authorization"] == "Bearer gateway-secret"
