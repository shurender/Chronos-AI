# ⏳ Chronos Engine
**AMD Developer Hackathon: ACT II | Unicorn Track**

Chronos Engine is an AI-powered Decision Intelligence digital twin platform. It ingests your past data (Slack, GitHub, Notion) to build a memory graph, then runs a structured simulation — a heuristic MVP engine plus a lightweight multi-agent council — to explore a handful of evidence-backed plausible timeline branches per decision, optimizing for "Expected Regret." Chronos explores plausible futures from available evidence; it does not predict the future, and it is not a guaranteed forecast.

---

## 📍 Current MVP Status

| Component | Status |
|---|---|
| Memory graph extraction (Slack/GitHub/Notion → nodes/edges) | ✅ Implemented |
| Forecast engine (`/forecast/decision`, `/simulate`) | ⚠️ Heuristic MVP — deterministic, seeded, not ML-trained |
| External evidence layer (`/evidence`) | ⚠️ Demo pack — curated local JSON, not live web search |
| Multi-agent council (Historian/Behavioral/Domain/Market/Risk/Strategist) | ⚠️ Lightweight MVP — deterministic structured functions, not autonomous LLM agents yet |
| Future Self chat (`/avatar/chat`) | ⚠️ Grounded MVP — Groq-backed when `GROQ_API_KEY` is set, deterministic labelled fallback otherwise |
| AMD GPU / vLLM / ROCm execution | ⚙️ Provider adapter in place (`LLM_PROVIDER=vllm`); ships a live vLLM endpoint yourself — see [AMD/vLLM deployment mode](#-amdvllm-deployment-mode) |

This is a working MVP built to demonstrate the architecture end-to-end, not a production-scale system. Every simulated output is heuristic and explorable, not a guaranteed prediction.

---

## 🚀 Tech Stack

**Frontend**
* **Framework:** React 19 + Vite
* **Styling:** Tailwind CSS v4
* **State Management:** Zustand
* **Graph Visualization:** React Flow + Dagre (Auto-layout)
* **Icons:** Lucide React

**Backend & AI**
* **API Framework:** FastAPI + Uvicorn
* **AI Orchestration:** LangGraph + LangChain
* **LLM Provider:** Groq (Llama 3)
* **Vector Store:** ChromaDB (Local SQLite)
* **Embeddings:** Local Sentence-Transformers (CPU optimized)
* **Graph Logic:** NetworkX

---

## 📦 Local Setup Instructions

To run Chronos Engine locally, you need to spin up both the **Frontend** and the **Backend** in two separate terminal windows.

### Prerequisites
1. Install [Node.js](https://nodejs.org/) (for the frontend).
2. Install [Python 3.10+](https://www.python.org/) (for the backend).

---

### 🟢 Terminal 1: Start the Backend (FastAPI)

**Navigate to the root directory:**
   ```bash
   cd Chronos-AI-main
   ```
## 1. Create and activate a virtual environment:
### On Mac/Linux:
```bash
python -m venv .venv
source .venv/bin/activate 
```
### On Windows:
```bash
python -m venv .venv
.\.venv\Scripts\activate
```



### 2. Install Python dependencies:
(We use the CPU version for local dev to avoid massive CUDA downloads)
```bash
pip install -r requirements-cpu.txt
```
### 3. Set up your API Key:
Create a new file named .env in the root folder (Chronos-AI-main/.env) and add your Groq API key:
```bash
GROQ_API_KEY=
FIREWORKS_API_KEY=
TAVILY_API_KEY=
```
### 4. Start the API server:
```bash
uvicorn backend.api:app --reload --port 8000
```
The backend is now running at http://localhost:8000. (Interactive API docs available at /docs)

### 🔵 Terminal 2: Start the Frontend (Vite)

### 1. Navigate to the frontend directory:
 ```bash
   cd Chronos-AI-main/Frontend
 ```
### 2. Install Node dependencies:
(Required fresh install for Tailwind v4)
```bash
npm install
```
### 3. Configure the backend URL:
```bash
copy .env.example .env
```
Ensure `Frontend/.env` contains:
```bash
VITE_API_BASE_URL=http://localhost:8000
```
### 4. Run the development server:
```bash
npm run dev
```

🔗 Using the App

   1. Open your browser and navigate to: http://localhost:5173

   2. You will be greeted by the Landing Page. Click Launch App.

   3. Proceed through the wizard. When you arrive at Step 2 and click "Run Simulation", the Frontend will communicate with the Python backend via CORS, fetching the live Memory Graph data and pinging the Decision Forecast engine!

---

## 🐳 Docker & tooling

### Full stack with Docker Compose

Runs backend (`:8000`) + frontend (`:5173`) with **mock/demo providers — no API keys needed**:

```bash
docker compose up --build
```

- Copy `.env.example` → `.env` to override providers/keys (Compose auto-loads it).
- All data stores (Chroma, graph, provenance/simulation SQLite, JSON stores) are centralized on the `chronos_data` volume under `/data`.
- Open http://localhost:5173 (the browser talks to the backend at `localhost:8000`).

### Make targets

| Command | Does |
|---|---|
| `make backend` | Run FastAPI (hot reload) on `:8000` |
| `make frontend` | Run Vite dev server on `:5173` |
| `make smoke` / `make test-backend` | `python -m backend.smoke_test` |
| `make evals` | `python -m backend.evals.run_evals` |
| `make test-frontend` | `npm run build` (type-check gate) |
| `make docker-up` | `docker compose up --build` |
| `make install` | Install backend + frontend deps |

### Health checks

- `GET /health` — liveness (process up).
- `GET /health/ready` — readiness (graph loaded + storage writable; `503` if not).
- `GET /health/dependencies` — detailed report: graph node count, evidence provider(s), LLM provider health, storage-path writability, demo mode.

### Demo mode vs production-ish mode

| | Demo (default) | Production-ish |
|---|---|---|
| `LLM_PROVIDER` | `mock` (offline) | `groq` / `vllm` (needs key or local endpoint) |
| `EVIDENCE_PROVIDER` | `demo` (curated local pack) | `uploaded` / `hybrid` |
| `CORS_ORIGINS` | `http://localhost:5173` | your real origin(s), never `*` |
| `DEMO_MODE` | `true` | `false` |

CI (`.github/workflows/ci.yml`) always runs in mock/deterministic mode, so it needs **no secrets**: backend smoke test + eval subset, frontend `npm run build`, and checks that `node_modules`/`.env` are not committed.

---

## 🛠️ Troubleshooting

**Backend won't start / start the API server:**
```bash
uvicorn backend.api:app --reload --port 8000
```
Run a quick smoke test before a demo to confirm the whole backend chain works end-to-end:
```bash
python -m backend.smoke_test
```
It imports `backend.api`, then hits `/graph`, `/simulate`, `/evidence`, and `/avatar/chat` via an in-process `TestClient` (no server needs to be running) and exits non-zero on any failure.

**Frontend won't start / build:**
```bash
cd Frontend
npm install
npm run dev      # local dev server on :5173
npm run build    # production build / type-check gate
```

**`GROQ_API_KEY` is optional:** the Future Self chat (`/avatar/chat`) uses Groq when `GROQ_API_KEY` is set in `.env`. Without it, the endpoint returns a deterministic, clearly-labelled fallback response (`llmBacked: false`) instead of crashing — the rest of the app (graph, `/simulate`, `/evidence`) does not need this key at all.

**The Memory Graph is empty (`/graph` returns 0 nodes):** that's expected on a fresh clone — nothing has been ingested yet. Run the ingestion pipeline to populate it from the bundled sample chunks:
```bash
python -m backend.main
```
This indexes `backend/sample_chunks.jsonl` into Chroma, runs extraction, and writes `backend/graph.gpickle`. Pass `--chunks path/to/other.jsonl` to ingest a different file, or `--no-viz` to skip the pyvis HTML export.

**Reset the graph / vector store** (e.g. after bad test data): delete the generated stores and re-run ingestion.
```bash
rm -rf backend/graph.gpickle backend/chroma_db
python -m backend.main
```
`/graph`, `/simulate`, and `/evidence` degrade gracefully (empty results, not errors) with no graph present, so a reset never breaks the app — it just returns to the "no precedents found" state until you re-ingest.

---

## ⚡ LLM providers: CPU/Groq mode vs AMD/vLLM mode

Chat generation goes through a provider abstraction (`backend/LLM/`), selected with `LLM_PROVIDER`. Embeddings are selected independently with `EMBEDDING_PROVIDER`. Check the active setup at any time:

```bash
python -c "from backend import config; print(config.LLM_PROVIDER, bool(config.FIREWORKS_API_KEY), config.EVIDENCE_PROVIDER, bool(config.TAVILY_API_KEY))"
curl http://localhost:8000/debug/config
curl http://localhost:8000/llm/health
curl "http://localhost:8000/evidence/search?query=AI%20startup%20pivot&k=5"
```

**Current default — CPU / Groq mode:**
- `LLM_PROVIDER=groq` (chat via Groq; needs `GROQ_API_KEY`). Without the key, chat is unavailable — the extraction pipeline reports the missing key and Future Self returns its deterministic fallback. Nothing crashes.
- `EMBEDDING_PROVIDER=sentence_transformers` (local, CPU, no key).
- `LLM_PROVIDER=mock` gives a deterministic offline chat provider (no network, no key) for tests/demos.

### 🔴 AMD/vLLM deployment mode

The clean AMD/ROCm path is to run a local [vLLM](https://docs.vllm.ai) server (which serves an OpenAI-compatible API) on an AMD GPU, then point Chronos at it — no code changes, just env vars.

1. Serve a model with vLLM (on the ROCm build for AMD GPUs), exposing the OpenAI-compatible endpoint, e.g. `http://localhost:8000/v1`.
2. Configure Chronos:

   ```bash
   AMD_MODE=true
   LLM_PROVIDER=vllm
   VLLM_BASE_URL=http://localhost:8000/v1   # OpenAI-compatible /chat/completions
   VLLM_MODEL=your-served-model-name
   # Optional: keep embeddings local, or serve them too:
   # EMBEDDING_PROVIDER=openai_like          # uses VLLM_BASE_URL/embeddings
   ```

3. Restart the backend and verify with `GET /llm/health` (`chat.available` should be `true` when the endpoint is reachable).

**Switching providers** is env-only — no code changes:

| `LLM_PROVIDER` | Endpoint | Key var |
|---|---|---|
| `groq` | Groq cloud | `GROQ_API_KEY`, `GROQ_MODEL` |
| `fireworks` | Fireworks (OpenAI-compatible) | `FIREWORKS_API_KEY`, `FIREWORKS_MODEL` |
| `ollama` | Local Ollama `OLLAMA_BASE_URL/v1` | `OLLAMA_MODEL` |
| `vllm` | Local vLLM `VLLM_BASE_URL` (AMD/ROCm) | `VLLM_MODEL` |
| `mock` | None (deterministic offline) | — |

If a configured provider is unreachable or missing its key, `/llm/health` reports `available: false` with a clear reason rather than failing silently.

---

## ✅ Running evaluation checks

Beyond "it runs," an eval harness checks quality: evidence grounding, missing-context detection, MarketAgent refusal of unsupported claims, and simulation consistency.

```bash
python -m backend.evals.run_evals
```

- Runs in-process against a `TestClient` in **deterministic / mock mode** (no paid APIs; `LLM_PROVIDER=mock`, `EMBEDDING_PROVIDER=mock`).
- Attempts `/ingest/demo` (tolerates a 502 when `GROQ_API_KEY` is absent — evals still run against the evidence layer and heuristic engine).
- Runs each case in `backend/evals/eval_cases.json` through `/simulate` (and `/avatar/chat` for selected cases), scores metrics, prints a pass/fail table, and **exits non-zero if any critical case fails**.

Metrics include: `endpoint_success`, `schema_valid`, `timelines_count_valid`, `evidence_grounding_present`, `unsupported_claims_absent` (MarketAgent must not cite outside the evidence snapshot / must refuse when evidence is missing), `missing_context_detected`, `confidence_penalty_applied`, `recommendation_present`, `no_crash`, and (for avatar cases) `grounding_label_valid`.

Add or edit cases in `backend/evals/eval_cases.json` (schema: `backend/evals/eval_schema.py`).

---

## Live mode validation

Use the local live-mode harness when `.env` is configured with Fireworks/Tavily keys and you want to check the real provider path without adding secrets to CI:

```bash
python -m backend.scripts.live_mode_check --require-live-llm --require-live-evidence
```

Optional flags:
- `--require-live-llm` fails if the configured LLM is unavailable or `/avatar/chat` falls back.
- `--require-live-evidence` fails if Tavily/live evidence is unavailable.
- `--require-connectors` fails if GitHub/Slack/Notion are not authenticated locally.
- `--decision "Should I pivot to enterprise?"` changes the sample simulation prompt.
- `--verbose` prints redacted response details.
- `--frontend-build` also runs `cd Frontend && npm run build`.

The harness prints a `PASS` / `WARN` / `FAIL` checklist for config loading, `/llm/health`, `/evidence/providers/health`, `/evidence/search`, `/connectors/status`, `/graph/summary`, `/simulate`, and `/avatar/chat`. It never prints API key values and does not require Slack/GitHub/Notion OAuth unless `--require-connectors` is passed.
