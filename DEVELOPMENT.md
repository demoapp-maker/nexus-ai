# Development guide

## Fast local loop

```bash
python3 -m venv /tmp/nexus-venv
/tmp/nexus-venv/bin/pip install -r backend/requirements.txt
cd frontend && npm ci
```

AI runtime memakai OmniRoute melalui OpenAI-compatible API secara default (`http://127.0.0.1:20128/v1`, model `auto`). Jalankan `./nexus.sh setup-omniroute` untuk instalasi user-local atau install CLI secara global, dan bind gateway ke loopback. Use `NEXUS_MOCK_AI=true` when OmniRoute/provider is unavailable; this returns deterministic responses and does not call any external AI endpoint.

## Quality gates

```bash
pytest -q
ruff check backend
cd frontend && npm run lint && npm run typecheck && npm run build
```

## End-to-end smoke test

Start the backend on port 8000, then run:

```bash
./test_nexus_tools.sh
python3 test_cognitive_routing_matrix.py
python3 test_nexus_routing.py
```

The scripts support `BASE_URL=http://host:port` for non-local environments.

## Runtime data

Local SQLite files live under `backend/data/` and are ignored by Git. Set `NEXUS_MEMORY_DB` to use another location. Do not commit user conversations or provider credentials.
