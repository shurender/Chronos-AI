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
| AMD GPU / vLLM / ROCm execution | 🗺️ Planned adapter — not wired up in this hackathon build |

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
GROQ_API_KEY=gsk_your_api_key_here
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
### 3. Run the development server:
```bash
npm run dev
```

🔗 Using the App

   1. Open your browser and navigate to: http://localhost:5173

   2. You will be greeted by the Landing Page. Click Launch App.

   3. Proceed through the wizard. When you arrive at Step 2 and click "Run Simulation", the Frontend will communicate with the Python backend via CORS, fetching the live Memory Graph data and pinging the Decision Forecast engine!

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
