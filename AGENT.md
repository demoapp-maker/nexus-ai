# Nexus AI Agent Playbook

Tujuan dokumen ini:
- membuat kontribusi agen coder tetap selaras arsitektur Nexus
- mencegah perubahan yang merusak perilaku inti
- mempercepat onboarding model lain tanpa trial and error berlebihan

## 1) Konteks sistem
Nexus adalah adaptive reasoning orchestration system, bukan chatbot linear.
Fokus utama:
- intent-aware
- domain-aware
- ambiguity-aware
- diagnosis-first ketika perlu
- governance dan observability aware

Komponen kunci:
- backend FastAPI: backend/main.py
- intent profiling: backend/logic/cognitive_router.py
- policy routing: backend/logic/routing_policy.py
- routing observability: backend/logic/routing_metrics.py
- model orchestration and tool execution: backend/logic/ai_service.py
- main chat UI: frontend/src/components/ChatInterface.tsx
- frontend proxy route: frontend/src/app/api/chat/stream/route.ts

## 2) Invariants yang tidak boleh dilanggar
1. Identitas asisten tetap Rohadi.
2. Endpoint chat utama tetap backend /chat/tools.
3. Format streaming SSE harus kompatibel:
- type info
- type text
- type tool_call
- type tool_result
- type error
- terminator data [DONE]
4. Grill-Me diperlakukan sebagai diagnostic escalation, bukan default mode.
5. Auto routing tetap policy-driven, bukan keyword if sederhana.
6. OmniRoute `auto`/configured routing menjadi provider utama; jangan meng-hardcode provider upstream di frontend. Fallback model mengikuti konfigurasi gateway dan tidak boleh memaksa model berbayar.
7. Frontend proxy harus meneruskan pesan error backend secara transparan.
8. Health indicator frontend harus tetap bisa membedakan online vs offline.

## 3) Kontrak routing kognitif
Urutan wajib pada /chat/tools:
1. Analyze intent profile
2. Build routing policy
3. Select effective model
4. Decide Grill-Me escalation
5. Emit routing info metadata
6. Execute model/tool loop with fallback
7. Log routing metrics

Jika ingin menambah mode baru:
- update schema IntentProfile
- update PolicyEngine selector
- update get_system_prompt_for_mode
- update test matrix

## 4) Kontrak kualitas kode
### Backend
- Hindari any-like structures yang tidak tervalidasi.
- Gunakan default aman untuk field intent agar tidak spam validation error.
- Jangan membuat fallback chain ke model berbayar sebagai default.
- Semua perubahan routing wajib punya jejak observability.

### Frontend
- Wajib lolos `npm run lint` dan `npm run typecheck`.
- Patuhi strict react-hooks rules:
- set-state-in-effect
- immutability
- purity
- refs
- Hindari mutable local accumulator di component handler.
- Hindari generic any pada payload streaming.
- Browser memakai URL relatif `/api/...`; URL backend hanya boleh digunakan oleh server-side proxy.

## 5) Definition of done untuk perubahan agent
Sebelum dianggap selesai, jalankan dari repository root:
1. Backend unit/security tests
- pytest -q
2. Static checks
- ruff check backend
3. Frontend quality gate
- cd frontend && npm run lint && npm run typecheck && npm run build
4. Smoke test end-to-end dengan backend aktif
- ./test_nexus_tools.sh
- python3 test_nexus_routing.py
- python3 test_cognitive_routing_matrix.py

Jika salah satu gagal, jangan merge.

## 6) Checklist perubahan aman
Setiap agen coder wajib cek:
- apakah perubahan mengubah intent schema
- apakah policy engine ikut diperbarui
- apakah metadata routing tetap dikirim
- apakah grill escalation rules tetap konsisten
- apakah metrics endpoint tetap hidup
- apakah fallback model tetap free-first

## 7) Anti-pattern yang harus dihindari
- Memindahkan routing logic ke if keyword sederhana.
- Menghapus policy engine untuk percepatan jangka pendek.
- Membungkus semua error menjadi pesan generik.
- Menonaktifkan fallback chain karena satu model gagal.
- Menambah mode baru tanpa test matrix.

## 8) Aturan operasional multi-agent
- Selalu gunakan path absolut saat menjalankan command proyek.
- Jangan asumsi cwd terminal stabil.
- Hindari mengedit banyak area arsitektur sekaligus tanpa test per tahap.
- Untuk perubahan besar, kirim metadata mode, confidence, dan ambiguity agar mudah audit.

## 9) Catatan kompatibilitas
Dokumen ini adalah sumber utama untuk AI agent coder.
Jika instruksi di tempat lain bertentangan, prioritaskan dokumen ini dan arsitektur aktif pada kode backend/logic.
