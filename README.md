# Nexus AI — Rohadi Edition

Nexus AI adalah asisten AI strategis berbasis FastAPI + Next.js. Backend memakai cognitive routing, policy-driven response modes, tool calling, web research, Grill-Me/TGM, dan memory per session.

> Status: development/production-ready baseline. Provider AI tetap membutuhkan API key yang valid, kecuali menggunakan `NEXUS_MOCK_AI=true` untuk smoke test lokal.

## Arsitektur singkat

```text
Browser
  │ same-origin Next.js proxy
  ▼
frontend (Next.js 16) ──► backend (FastAPI/SSE)
                              ├─ CognitiveRouter + PolicyEngine
                              ├─ AIService (OpenRouter/Alibaba/DuckAI)
                              ├─ WebSearchTool (bounded public fetch)
                              ├─ Grill-Me v2
                              └─ SQLite memory per session
```

Endpoint utama:

- `GET /health` — liveness.
- `GET /ready` — database readiness.
- `POST /chat/tools` — canonical cognitive-routing SSE chat.
- `POST /chat/stream` — compatibility alias ke `/chat/tools`.
- `POST /chat` — non-streaming chat.
- `POST /chat/grill` — explicit Grill-Me mode.
- `POST /research/autonomous` — bounded research workflow.
- `POST /planning/task` — task planning.
- `/admin/*` — wajib menggunakan `X-Admin-Token`.

## Menjalankan secara lokal

### 1. Backend

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Isi OPENROUTER_API_KEY dan ADMIN_PANEL_TOKEN bila diperlukan
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Jika `DATABASE_URL` kosong, backend otomatis memakai SQLite lokal di `backend/data/nexus_config.db`. Memory percakapan disimpan di `backend/data/nexus_memory.db`.

Untuk smoke test tanpa provider eksternal:

```bash
NEXUS_MOCK_AI=true ADMIN_PANEL_TOKEN=local-admin \
  python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend

```bash
cd frontend
npm ci
npm run dev -- --hostname 0.0.0.0 --port 5008
```

Frontend hanya memanggil route relatif `/api/...`. Proxy Next.js meneruskan request ke `BACKEND_URL`, sehingga browser tidak perlu mengakses `localhost` secara langsung.

Untuk production:

```bash
npm run build
BACKEND_URL=http://127.0.0.1:8000 npm run start -- --hostname 0.0.0.0 --port 5008
```

### 3. PM2

```bash
./nexus.sh build
./nexus.sh start
./nexus.sh status
./nexus.sh logs
```

Path PM2 dihitung relatif terhadap lokasi repo; tidak ada asumsi `/root/nexus-ai`.

## Konfigurasi penting

Lihat `backend/.env.example`. Variable terpenting:

- `DATABASE_URL` — kosong untuk SQLite lokal, PostgreSQL untuk production.
- `NEXUS_MEMORY_DB` — path memory; path relatif dihitung dari folder `backend`.
- `CORS_ORIGINS` — daftar origin frontend dipisahkan koma.
- `ADMIN_PANEL_TOKEN` — wajib untuk mengaktifkan endpoint admin.
- `NEXUS_CONFIG_ENCRYPTION_KEY` — Fernet key wajib jika API key disimpan melalui `/admin/config`.
- `RATE_LIMIT_PER_MINUTE` dan `MAX_REQUEST_BODY_BYTES` — abuse protection.
- `ENABLE_GLOBAL_MEMORY=false` — default untuk mencegah kebocoran lintas session.
- `NEXUS_MOCK_AI=false` — hanya untuk development/smoke test.

API key tidak dikembalikan oleh endpoint admin; hanya status `api_key_set` yang ditampilkan.

## Pengujian dan quality gate

```bash
# Backend unit/security tests
pytest -q

# Static checks
ruff check backend

# Frontend
cd frontend
npm run lint
npm run typecheck
npm run build

# Saat backend test server aktif
cd ..
./test_nexus_tools.sh
python3 test_cognitive_routing_matrix.py
python3 test_nexus_routing.py
```

Untuk menjalankan smoke test end-to-end tanpa biaya provider:

```bash
NEXUS_MOCK_AI=true ADMIN_PANEL_TOKEN=test-admin \
  PYTHONPATH=backend python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Security notes

- Jangan mengaktifkan global memory pada deployment multi-tenant tanpa anonymization dan consent.
- `fetch_url` hanya menerima HTTP(S) ke host publik, membatasi redirect dan ukuran response.
- Tool calculation tidak memakai `eval`.
- Admin endpoint fail-closed jika token belum dikonfigurasi.
- Gunakan reverse proxy/WAF rate limiter bersama limiter process-local untuk production berskala banyak worker.

## Struktur repository

- `backend/main.py` — FastAPI app dan canonical SSE pipeline.
- `backend/logic/ai_service.py` — provider abstraction, streaming, tool aggregation, fallback.
- `backend/logic/cognitive_router.py` — intent profile dan deterministic fallback.
- `backend/logic/routing_policy.py` — policy selection.
- `backend/logic/memory_manager.py` — scoped memory queue.
- `backend/tools/web_search_tool.py` — search dan bounded public fetch.
- `backend/tools/grill_me_skill_v2.py` — stateful diagnostic Grill-Me.
- `frontend/src/components/ChatInterface.tsx` — UI chat utama.
- `frontend/src/app/api/chat/*` — same-origin backend proxy.
