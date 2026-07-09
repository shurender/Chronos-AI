# ⏳ Chronos Engine
**AMD Developer Hackathon: ACT II | Unicorn Track**

Chronos Engine is an AI-powered Decision Intelligence digital twin platform. It ingests your past data (Slack, GitHub, Notion) to build a memory graph, then uses a multi-agent parallel simulation engine to forecast thousands of future scenarios—optimizing for "Expected Regret."

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

🔵 Terminal 2: Start the Frontend (Vite)

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
