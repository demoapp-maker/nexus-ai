"""Lightweight episodic memory backed by SQLite.

The database path is absolute and configurable so the result does not depend on
which directory starts Uvicorn/PM2. The memory store is intentionally simple;
production deployments can replace this module with a shared vector store while
keeping the MemoryManager interface.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

BACKEND_ROOT = Path(__file__).resolve().parents[1]
_default_db = BACKEND_ROOT / "data" / "nexus_memory.db"
_configured_db = os.getenv("NEXUS_MEMORY_DB", "").strip()
if _configured_db:
    _configured_path = Path(_configured_db)
    DB_PATH = str(
        (_configured_path if _configured_path.is_absolute() else BACKEND_ROOT / _configured_path).resolve()
    )
else:
    DB_PATH = str(_default_db)


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    """Initialize SQLite database for memory storage."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT DEFAULT 'fact',
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_count INTEGER DEFAULT 0
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_room ON memories(room)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at)")
        conn.commit()


def store_memory(
    content: str,
    room: str = "general",
    memory_type: str = "fact",
    tags: Optional[List[str]] = None,
) -> None:
    """Store one memory entry."""
    if not content:
        return
    init_db()
    tags_json = json.dumps(tags or [], ensure_ascii=False)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO memories (room, content, memory_type, tags)
            VALUES (?, ?, ?, ?)
            """,
            (room, content, memory_type, tags_json),
        )
        conn.commit()


def recall_memory(
    query: str,
    room: str = "general",
    budget: int = 3000,
    limit: int = 5,
) -> str:
    """Recall keyword-matching memories and return bounded context."""
    if not query:
        return ""

    init_db()
    limit = max(1, min(int(limit), 20))
    budget = max(100, min(int(budget), 20_000))
    search_terms = [term.lower() for term in query.split() if len(term) > 2]

    conditions = []
    params: List[object] = [room]
    for term in search_terms:
        # Escape LIKE wildcards so a user cannot turn a term into a full scan.
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append("content LIKE ? ESCAPE '\\'")
        params.append(f"%{escaped}%")

    where_clause = " OR ".join(conditions) if conditions else "1=1"
    params.append(limit)

    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM memories
            WHERE room = ? AND ({where_clause})
            ORDER BY accessed_count DESC, created_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

        if not rows:
            rows = conn.execute(
                """
                SELECT * FROM memories
                WHERE room = ?
                ORDER BY created_at DESC
                LIMIT 2
                """,
                (room,),
            ).fetchall()

        if not rows:
            return ""

        result_parts: List[str] = []
        total_tokens = 0
        selected_ids: List[int] = []
        for row in rows:
            content = str(row["content"])
            token_estimate = max(1, len(content) // 4)
            if total_tokens + token_estimate > budget:
                break
            result_parts.append(f"[Memori {row['created_at']}]: {content}")
            total_tokens += token_estimate
            selected_ids.append(int(row["id"]))

        if selected_ids:
            conn.executemany(
                "UPDATE memories SET accessed_count = accessed_count + 1 WHERE id = ?",
                [(memory_id,) for memory_id in selected_ids],
            )
            conn.commit()

        return "\n\n".join(result_parts)


def list_memories(room: str = "general") -> List[Dict]:
    """List metadata for memories in a room."""
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, room, memory_type, tags, created_at, accessed_count
            FROM memories
            WHERE room = ?
            ORDER BY created_at DESC
            """,
            (room,),
        ).fetchall()
        return [dict(row) for row in rows]
