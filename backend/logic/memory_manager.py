from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from logic import simple_memory


class MemoryManager:
    """Memory facade with bounded asynchronous writes.

    A single worker prevents the unbounded one-thread-per-message behavior that
    previously caused SQLite lock contention and lost writes during shutdown.
    """

    def __init__(self) -> None:
        simple_memory.init_db()
        self._writer = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nexus-memory")

    @staticmethod
    def session_room(session_id: Optional[str]) -> str:
        value = str(session_id or "default")
        value = re.sub(r"[^A-Za-z0-9_.:-]", "_", value)[:128] or "default"
        return f"session_{value}"

    def mira_recall(self, query: str, room: str = "general") -> str:
        try:
            return simple_memory.recall_memory(query, room=room)
        except Exception as exc:
            print(f"[MEMORY] Recall error: {exc}")
            return ""

    def _store_worker(self, content: str, room: str) -> None:
        try:
            simple_memory.store_memory(content, room=room)
            print(f"[MEMORY] Stored memory in room: {room}")
        except Exception as exc:
            print(f"[MEMORY] Store error: {exc}")

    def mira_store(self, content: str, room: str = "general") -> bool:
        if not content:
            return False

        # Preserve the useful content field when callers pass structured event
        # JSON, but do not let malformed JSON break the write path.
        try:
            data = json.loads(content)
            if isinstance(data, dict) and isinstance(data.get("content"), str):
                content = data["content"]
        except (TypeError, ValueError):
            pass

        self._writer.submit(self._store_worker, str(content)[:20_000], room[:160])
        return True


memory_manager = MemoryManager()
