# ⏳ Chronos Engine
**AMD Developer Hackathon: ACT II | Unicorn Track**

## Demo Video

<video src="Frontend/public/demo-video.mp4" controls width="100%"></video>

If the video does not render inline on GitHub, open it directly: [Frontend/public/demo-video.mp4](Frontend/public/demo-video.mp4)

Chronos Engine is an AI-powered Decision Intelligence digital twin platform. It ingests your past data (Slack, GitHub, Notion) to build a memory graph, then runs a structured simulation — a heuristic MVP engine plus a lightweight multi-agent council — to explore a handful of evidence-backed plausible timeline branches per decision, optimizing for "Expected Regret." Chronos explores plausible futures from available evidence; it does not predict the future, and it is not a guaranteed forecast.

---

## 📍 Current MVP Status

| Component | Status |
|---|---|
| Memory graph extraction (Slack/GitHub/Notion → nodes/edges) | ✅ Implemented |
| Forecast engine (`/forecast/decision`, `/simulate`) | ⚠️ Heuristic MVP — deterministic, seeded, not ML-trained |
| External evidence layer (`/evidence`) | ✅ Demo, uploaded, Tavily, and hybrid modes. Tavily results are labelled as live external signals, not verified facts |
| Multi-agent council (Historian/Behavioral/Domain/Market/Risk/Strategist) | ⚠️ Lightweight MVP — deterministic by default, with optional LLM-enriched rationale via provider config |
| Future Self chat (`/avatar/chat`) | ✅ Provider-backed when configured (`fireworks`, `groq`, `ollama`, `vllm`) with deterministic/mock fallback |
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
* **LLM Provider:** Fireworks, Groq, Ollama, vLLM, or deterministic mock
* **Vector Store:** ChromaDB (Local SQLite)
* **Embeddings:** Local Sentence-Transformers (CPU optimized)
* **Graph Logic:** NetworkX

---

## Unicorn Track Pre-Screening Notes

**What we built:** Chronos Engine is a decision-intelligence app that ingests project/workspace context, builds a memory graph, simulates plausible future branches, and lets the user ask a Future Self advisor grounded in the selected timeline and citations.

**AMD / approved compute usage:** The live demo uses Fireworks AI as the hosted LLM provider (`LLM_PROVIDER=fireworks`, default model `accounts/fireworks/models/gpt-oss-120b`). The backend also includes an AMD ROCm/vLLM-ready path via the OpenAI-compatible provider adapter (`LLM_PROVIDER=vllm`, `VLLM_BASE_URL`, `VLLM_MODEL`, `AMD_MODE=true`) for running compatible open-weight models on AMD GPU infrastructure.

**Main implementation paths:**
* Frontend app: `Frontend/src/App.tsx`
* Frontend API client/contracts: `Frontend/src/api/`
* Backend API: `backend/api.py`
* Simulation engine: `backend/Decision_Graph/Forcast_engine.py`
* Future Self chat: `backend/Future_Self/avatar_engine.py`
* LLM providers: `backend/LLM/`
* Evidence providers: `backend/External_Evidence/`
* Connectors/ingestion: `backend/Connectors/`, `backend/Ingestion/`

**External services documented:** Fireworks AI, Tavily, GitHub public repo ingestion, Vercel frontend hosting, Render backend hosting, and optional AMD ROCm/vLLM serving.

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
### 3. Configure backend environment:
Copy the example env file, then add only the keys you want to use. Do not commit `.env`.
```bash
copy .env.example .env
```

Useful local live-mode values:
```bash
LLM_PROVIDER=fireworks
FIREWORKS_API_KEY=
EVIDENCE_PROVIDER=hybrid
TAVILY_API_KEY=
GITHUB_TOKEN=
DEMO_MODE=false
CORS_ORIGINS=http://localhost:5173
```

`GITHUB_TOKEN` is optional, but enables authenticated GitHub repo ingestion and private repo access. Public repos can also be ingested from the app by entering `owner/repo` or a GitHub URL under the GitHub card.
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

   2. You will be greeted by the Landing Page. Click Launch Program.

   3. Connect data by authenticating GitHub/Slack/Notion, entering a GitHub repo directly, uploading files, or using sample demo data.

   4. Define a decision and click "Run Simulation". The frontend calls the FastAPI backend, refreshes the Memory Graph, pulls relevant evidence, and renders simulated timeline branches.

### Upload support

The upload flow supports `.pdf`, `.txt`, `.md`, `.markdown`, and `.json`. Text PDFs require `pypdf` from `requirements-cpu.txt`. If a PDF has no selectable text, Chronos returns a clear warning instead of pretending ingestion succeeded silently. Extraction warnings, including possible contradictions, are summarized in the UI.

### Source labels

Chronos keeps source labels explicit:
- GitHub/Slack/Notion connector data is marked as authenticated/live when actually synced from those providers.
- Uploaded files are marked as user-supplied.
- Demo workspace data is marked as demo/local.
- Tavily evidence is marked as live external evidence, not a verified fact.

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
| `LLM_PROVIDER` | `mock` (offline) | `fireworks` / `groq` / `vllm` (needs key or local endpoint) |
| `EVIDENCE_PROVIDER` | `demo` (curated local pack) | `tavily` / `uploaded` / `hybrid` |
| `CORS_ORIGINS` | `http://localhost:5173` | your real origin(s), never `*` |
| `DEMO_MODE` | `true` | `false` |

CI (`.github/workflows/ci.yml`) always runs in mock/deterministic mode, so it needs **no secrets**: backend smoke test + eval subset, frontend `npm run build`, and checks that `node_modules`/`.env` are not committed.

---

## 🛠️ Troubleshooting

**Backend won't start / start the API server:**
```bash
uvicorn backend.api:app --reload --port 8000
```

If the frontend says `Failed to fetch` or `Backend disconnected`, confirm port `8000` is serving the API, not the static helper server:
```bash
curl http://localhost:8000/health
```
Expected response:
```json
{"status":"ok"}
```
If you get HTML instead, stop the process on port `8000` and restart with `uvicorn backend.api:app --reload --port 8000`.

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

**LLM keys are optional:** Future Self chat (`/avatar/chat`) uses the provider selected by `LLM_PROVIDER` when the matching key or local endpoint is configured. Without a live provider, the endpoint returns a deterministic, clearly labelled fallback response (`llmBacked: false`) instead of crashing.

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

## ⚡ LLM providers and live evidence

Chat generation goes through a provider abstraction (`backend/LLM/`), selected with `LLM_PROVIDER`. Embeddings are selected independently with `EMBEDDING_PROVIDER`. Check the active setup at any time:

```bash
python -c "from backend import config; print(config.LLM_PROVIDER, bool(config.FIREWORKS_API_KEY), config.EVIDENCE_PROVIDER, bool(config.TAVILY_API_KEY))"
curl http://localhost:8000/debug/config
curl http://localhost:8000/llm/health
curl "http://localhost:8000/evidence/search?query=AI%20startup%20pivot&k=5"
```

**Common local live mode:**
- `LLM_PROVIDER=fireworks` with `FIREWORKS_API_KEY` enables live Future Self chat.
- `EVIDENCE_PROVIDER=hybrid` with `TAVILY_API_KEY` combines Tavily live external signals with local/demo evidence when relevant.
- `EMBEDDING_PROVIDER=sentence_transformers` keeps embeddings local on CPU.
- `LLM_PROVIDER=mock` gives a deterministic offline chat provider (no network, no key) for tests/demos.

Evidence labels are preserved in responses and UI state: demo/local evidence is not presented as live web evidence, and Tavily results are treated as external signals rather than verified facts.

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
- Attempts `/ingest/demo` and still runs evals against the evidence layer and heuristic engine when optional live providers are unavailable.
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
