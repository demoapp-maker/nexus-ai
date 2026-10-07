import os
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict

from config.database import AIProviderConfig, SessionLocal, engine
from logic import simple_memory
from logic.routing_metrics import routing_metrics
from logic.secrets import SecretConfigError, decrypt_secret, encrypt_secret
from sqlalchemy import text

_PROVIDER_ALIASES = {
    "omni-route": "omniroute",
    "omni_route": "omniroute",
    "openai-compatible": "omniroute",
    "openai_compatible": "omniroute",
}


def normalize_provider(value: str) -> str:
    provider = (value or "").strip().lower()
    return _PROVIDER_ALIASES.get(provider, provider)


def _normalize_base_url(provider: str, base_url: str) -> str:
    provider = normalize_provider(provider)
    value = (base_url or "").strip().rstrip("/")
    if not value:
        if provider == "alibaba":
            value = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        elif provider == "openrouter":
            value = "https://openrouter.ai/api/v1"
        elif provider == "omniroute":
            value = os.getenv("OMNIROUTE_URL", "http://127.0.0.1:20128/v1")
        else:
            value = "https://api.openai.com/v1"

    if value.endswith("/chat/completions"):
        return value

    return f"{value}/chat/completions"


def _default_runtime_config() -> Dict[str, Any]:
    provider = normalize_provider(os.getenv("DEFAULT_AI_PROVIDER", "omniroute"))
    if provider == "omniroute":
        base_url = os.getenv("OMNIROUTE_URL", "http://127.0.0.1:20128/v1")
        api_key = os.getenv("OMNIROUTE_API_KEY", "")
        model = os.getenv("OMNIROUTE_MODEL", "auto")
        referer = os.getenv("OMNIROUTE_REFERER", "")
        title = os.getenv("OMNIROUTE_TITLE", "Nexus AI")
    elif provider == "alibaba":
        base_url = os.getenv("ALIBABA_AI_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
        api_key = os.getenv("ALIBABA_AI_KEY", os.getenv("ALIBABA_API_KEY", ""))
        model = os.getenv("ALIBABA_AI_MODEL", "qwen-plus")
        referer = os.getenv("ALIBABA_AI_REFERER", "")
        title = os.getenv("ALIBABA_AI_TITLE", "Nexus AI")
    elif provider == "duckai":
        base_url = os.getenv("DUCKAI_URL", "http://localhost:3000/v1")
        api_key = os.getenv("DUCKAI_API_KEY", "")
        model = os.getenv("DUCKAI_MODEL", "gpt-4o-mini")
        referer = os.getenv("DUCKAI_REFERER", "")
        title = os.getenv("DUCKAI_TITLE", "Nexus AI")
    elif provider == "openrouter":
        base_url = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        referer = os.getenv("OPENROUTER_REFERER", "https://nexus-ai.local")
        title = os.getenv("OPENROUTER_TITLE", "Nexus AI")
    else:
        base_url = os.getenv("OPENAI_COMPATIBLE_URL", "http://127.0.0.1:20128/v1")
        api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY", "")
        model = os.getenv("OPENAI_COMPATIBLE_MODEL", "auto")
        referer = os.getenv("OPENAI_COMPATIBLE_REFERER", "")
        title = os.getenv("OPENAI_COMPATIBLE_TITLE", "Nexus AI")

    return {
        "provider": provider,
        "base_url": _normalize_base_url(provider, base_url),
        "api_key": api_key,
        "model": model,
        "fallback_models": [],
        "referer": referer,
        "title": title,
        "extra_headers": {},
        "source": "environment",
    }


def _environment_api_key(provider: str) -> str:
    provider = normalize_provider(provider)
    if provider == "omniroute":
        return os.getenv("OMNIROUTE_API_KEY", "")
    if provider == "openrouter":
        return os.getenv("OPENROUTER_API_KEY", "")
    if provider == "alibaba":
        return os.getenv("ALIBABA_AI_KEY", os.getenv("ALIBABA_API_KEY", ""))
    if provider == "duckai":
        return os.getenv("DUCKAI_API_KEY", "")
    return os.getenv("OPENAI_COMPATIBLE_API_KEY", "")


def _environment_model(provider: str) -> str:
    provider = normalize_provider(provider)
    if provider == "omniroute":
        return os.getenv("OMNIROUTE_MODEL", "auto")
    if provider == "openrouter":
        return os.getenv("OPENROUTER_MODEL", "openrouter/free")
    if provider == "alibaba":
        return os.getenv("ALIBABA_AI_MODEL", "qwen-plus")
    if provider == "duckai":
        return os.getenv("DUCKAI_MODEL", "gpt-4o-mini")
    return os.getenv("OPENAI_COMPATIBLE_MODEL", "auto")


def _row_to_config(row: AIProviderConfig) -> Dict[str, Any]:
    extra_headers = row.extra_headers or {}
    if not isinstance(extra_headers, dict):
        extra_headers = {}

    fallback_models = row.fallback_models or []
    if not isinstance(fallback_models, list):
        fallback_models = []

    try:
        stored_api_key = decrypt_secret(row.api_key or "")
    except SecretConfigError:
        # Keep health/config endpoints usable while making the provider appear
        # unconfigured until the encryption key is supplied.
        stored_api_key = ""
    provider = normalize_provider(row.provider)
    env_api_key = _environment_api_key(provider)

    return {
        "provider": provider,
        "base_url": _normalize_base_url(provider, row.base_url),
        "api_key": stored_api_key or env_api_key,
        "model": row.model,
        "fallback_models": fallback_models,
        "referer": row.referer or "",
        "title": row.title or "Nexus AI",
        "extra_headers": extra_headers,
        "source": "database",
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _is_legacy_openrouter_default(row: AIProviderConfig) -> bool:
    """Identify the old auto-created default without touching explicit configs."""
    base_url = str(row.base_url or "").rstrip("/")
    return (
        normalize_provider(str(row.provider or "")) == "openrouter"
        and not row.api_key
        and str(row.model or "") in {"", "openrouter/free"}
        and base_url
        in {
            "https://openrouter.ai/api/v1",
            "https://openrouter.ai/api/v1/chat/completions",
        }
        and not (row.fallback_models or [])
    )


def ensure_default_ai_config() -> Dict[str, Any]:
    session = SessionLocal()
    try:
        row = session.query(AIProviderConfig).filter(AIProviderConfig.is_active.is_(True)).order_by(AIProviderConfig.updated_at.desc()).first()
        defaults = _default_runtime_config()
        if row:
            if (
                defaults["provider"] == "omniroute"
                and _is_legacy_openrouter_default(row)
            ):
                row.provider = defaults["provider"]
                row.base_url = defaults["base_url"]
                row.model = defaults["model"]
                row.fallback_models = defaults["fallback_models"]
                row.referer = defaults["referer"]
                row.title = defaults["title"]
                row.extra_headers = defaults["extra_headers"]
                session.commit()
                session.refresh(row)
            return _row_to_config(row)

        defaults = _default_runtime_config()
        config = AIProviderConfig(
            provider=defaults["provider"],
            base_url=defaults["base_url"],
            # Environment keys are read at runtime; database-managed keys are
            # encrypted only through update_ai_config().
            api_key="",
            model=defaults["model"],
            fallback_models=defaults["fallback_models"],
            referer=defaults["referer"],
            title=defaults["title"],
            extra_headers=defaults["extra_headers"],
            is_active=True,
        )
        session.add(config)
        session.commit()
        session.refresh(config)
        return _row_to_config(config)
    finally:
        session.close()


def get_active_ai_config() -> Dict[str, Any]:
    session = SessionLocal()
    try:
        row = session.query(AIProviderConfig).filter(AIProviderConfig.is_active.is_(True)).order_by(AIProviderConfig.updated_at.desc()).first()
        if row:
            return _row_to_config(row)
        return _default_runtime_config()
    finally:
        session.close()


def update_ai_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        row = session.query(AIProviderConfig).filter(AIProviderConfig.is_active.is_(True)).order_by(AIProviderConfig.updated_at.desc()).first()
        if row is None:
            row = AIProviderConfig(is_active=True)
            session.add(row)

        provider = normalize_provider(str(payload.get("provider") or "omniroute"))
        base_url = _normalize_base_url(provider, str(payload.get("base_url") or ""))
        fallback_models = payload.get("fallback_models") or []
        if isinstance(fallback_models, str):
            fallback_models = [item.strip() for item in fallback_models.split(",") if item.strip()]
        if not isinstance(fallback_models, list):
            fallback_models = []

        previous_provider = row.provider if row.id is not None else None
        row.provider = provider
        row.base_url = base_url
        if "api_key" in payload and payload.get("api_key") is not None:
            submitted_key = str(payload.get("api_key") or "")
            row.api_key = encrypt_secret(submitted_key) if submitted_key else ""
        elif previous_provider and previous_provider != provider:
            # Never accidentally send a key for provider A to provider B.
            row.api_key = ""
        row.model = str(payload.get("model") or _environment_model(provider))
        row.fallback_models = fallback_models
        row.referer = str(payload.get("referer") or "")
        row.title = str(payload.get("title") or "Nexus AI")
        extra_headers = payload.get("extra_headers") or {}
        row.extra_headers = extra_headers if isinstance(extra_headers, dict) else {}
        row.is_active = True

        session.commit()
        session.refresh(row)
        return _row_to_config(row)
    finally:
        session.close()


def get_provider_headers(config: Dict[str, Any]) -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    api_key = str(config.get("api_key") or "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if config.get("provider") == "openrouter":
        headers["HTTP-Referer"] = config.get("referer") or "https://nexus-ai.local"
        headers["X-Title"] = config.get("title") or "Nexus AI"

    extra_headers = config.get("extra_headers") or {}
    if isinstance(extra_headers, dict):
        for key, value in extra_headers.items():
            if key and value is not None:
                headers[str(key)] = str(value)

    return headers


def get_mira_snapshot(limit: int = 10) -> Dict[str, Any]:
    simple_memory.init_db()
    db_path = simple_memory.DB_PATH
    snapshot: Dict[str, Any] = {
        "status": "healthy" if os.path.exists(db_path) else "missing",
        "db_path": db_path,
        "exists": os.path.exists(db_path),
        "total_memories": 0,
        "rooms": [],
        "recent_memories": [],
    }

    if not os.path.exists(db_path):
        return snapshot

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) AS total FROM memories")
        snapshot["total_memories"] = int(cursor.fetchone()["total"])

        cursor.execute(
            """
            SELECT room, COUNT(*) AS count, MAX(created_at) AS last_seen
            FROM memories
            GROUP BY room
            ORDER BY count DESC, last_seen DESC
            LIMIT ?
            """,
            (limit,),
        )
        snapshot["rooms"] = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT id, room, memory_type, created_at, substr(content, 1, 220) AS preview
            FROM memories
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        snapshot["recent_memories"] = [dict(row) for row in cursor.fetchall()]
        return snapshot
    finally:
        conn.close()


def build_admin_health_snapshot(started_at: datetime) -> Dict[str, Any]:
    db_health: Dict[str, Any]
    started = time.perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        db_health = {
            "status": "healthy",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except Exception as exc:
        db_health = {
            "status": "unhealthy",
            "error": str(exc),
        }

    config = get_active_ai_config()
    mira = get_mira_snapshot(limit=6)
    events = routing_metrics.snapshot(limit=10)

    return {
        "app": {
            "status": "healthy",
            "version": "0.2.0",
            "started_at": started_at.isoformat(),
            "uptime_seconds": round((datetime.utcnow() - started_at).total_seconds(), 2),
        },
        "database": db_health,
        "ai_provider": {
            "provider": config.get("provider"),
            "base_url": config.get("base_url"),
            "model": config.get("model"),
            "fallback_models": config.get("fallback_models", []),
            "api_key_set": bool(config.get("api_key")),
            "source": config.get("source"),
            "updated_at": config.get("updated_at"),
        },
        "mira": mira,
        "routing": {
            "recent_events": events,
            "total_events": len(routing_metrics._events),
        },
    }