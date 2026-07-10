# Chronos Backend API Contract

Frozen reference for the outsourced UI. Full TypeScript types live in
[`Frontend/src/api/contracts.ts`](../Frontend/src/api/contracts.ts).

- **Base URL (local):** `http://localhost:8000`
- **Content type:** `application/json` (except `POST /ingest/upload`, which is `multipart/form-data`).
- **Errors:** FastAPI envelope — `{ "detail": <string | object> }`. Validation errors are `422`; not-found is `404`; ingestion-with-no-LLM is `502`.
- **Demo mode:** default. Deterministic/mock providers; **no API key required** for anything except LLM-backed *extraction* (ingestion) and *optional* LLM chat/agents.

> ⚠️ **Breaking API changes MUST update BOTH this file and `Frontend/src/api/contracts.ts`.**
> Additive fields are backward-compatible; renaming/removing a field is breaking.

Legend: **Demo?** = works in default demo mode · **Key?** = requires `GROQ_API_KEY` (or a configured LLM provider).

---

## Ingestion

### `POST /ingest/demo`
- **Purpose:** Parse the bundled demo GitHub/Slack/Notion sources into the memory graph.
- **Demo?** Yes · **Key?** Yes for full extraction — without a key, source records are created but graph extraction fails (`502`).
- **Request:** _none_
- **Response `200`** (`IngestionRun`):
```json
{ "run_id": "uuid", "source_type": "demo", "status": "succeeded",
  "started_at": "ISO", "completed_at": "ISO", "chunks_created": 12,
  "nodes_created": 30, "edges_created": 18, "warnings": [], "errors": [], "source_summary": {} }
```
- **Error `502`:** `{ "detail": { "run_id": "uuid", "errors": ["chunk ...: GROQ_API_KEY is not set."] } }`
- **curl:** `curl -X POST localhost:8000/ingest/demo`

### `POST /ingest/github`
- **Purpose:** Ingest public commits/issues from a GitHub repo (no OAuth; optional `GITHUB_TOKEN` raises rate limits).
- **Demo?** Needs network · **Key?** Yes for extraction (as above).
- **Request** (`IngestGithubRequest`): `{ "repo": "owner/repo", "include_issues": true, "max_items": 30 }`
- **Response `200`:** `IngestionRun` (see above).
- **Error `502`:** unreachable / rate-limited / extraction failed → `{ "detail": { "run_id": "...", "errors": [...] } }`
- **curl:** `curl -X POST localhost:8000/ingest/github -H 'Content-Type: application/json' -d '{"repo":"pallets/flask"}'`

### `POST /ingest/upload`
- **Purpose:** Ingest uploaded files (`.pdf`, `.md`, `.json`).
- **Demo?** Yes · **Key?** Yes for extraction.
- **Request:** `multipart/form-data` with one or more `files`.
- **Response `200`:** `IngestionRun`.
- **curl:** `curl -X POST localhost:8000/ingest/upload -F 'files=@notes.md'`

---

## Graph & query

### `GET /graph`
- **Purpose:** Full memory graph as plain nodes/edges (for visualization).
- **Demo?** Yes · **Key?** No. (Empty `{nodes:[],edges:[]}` until something is ingested.)
- **Response `200`** (`GraphResponse`): `{ "nodes": [{ "id": "...", "node_type": "decision", "label": "...", "evidence_type": "fact", "confidence": 0.9 }], "edges": [{ "source": "...", "target": "...", "edge_type": "causal" }] }`
- **curl:** `curl localhost:8000/graph`

### `GET /query/similar?q=<text>&k=5`
- **Purpose:** Similar past decisions from the chunk store.
- **Demo?** Yes · **Key?** No (local/mock embeddings).
- **Response `200`:** `{ "items": [{ "chunk_id": "...", "snippet": "...", "distance": 0.42, "source_type": "...", "timestamp": "...", "project": "..." }] }`
- **curl:** `curl 'localhost:8000/query/similar?q=pivot&k=5'`

---

## Intake

### `POST /intake/analyze`
- **Purpose:** Detect missing decision context, produce clarifying questions + a confidence penalty.
- **Demo?** Yes · **Key?** No (deterministic).
- **Request** (`IntakeAnalyzeRequest`): `{ "decisionQuestion": "Should I pivot?", "decisionType": "Startup", "horizon": "3 years", "risk": 60, "goal": "...", "geography": "US", "options": ["A","B"], "evidenceCount": 5, "precedentCount": 3 }`
- **Response `200`** (`IntakeAnalysis`):
```json
{ "completenessScore": 0.52, "missingFields": ["geography","options"],
  "assumptions": ["Assuming a 3-year horizon."],
  "clarifyingQuestions": [{ "category": "geography_domain", "question": "...", "why_it_matters": "..." }],
  "canProceed": true, "confidencePenalty": 0.48, "reason": "Some context is missing..." }
```
- **curl:** `curl -X POST localhost:8000/intake/analyze -H 'Content-Type: application/json' -d '{"decisionQuestion":"Should I pivot?"}'`

---

## Digital Twin

### `POST /digital-twin/build`
- **Purpose:** Structured profile (skills/resources/constraints/goals/behavior + risk/execution style) from graph + intake + evidence.
- **Demo?** Yes · **Key?** No (deterministic).
- **Request** (`DigitalTwinBuildRequest`): `{ "decisionQuestion": "...", "decisionType": "Startup", "goal": "...", "constraints": "...", "geography": "US", "options": ["A"], "useGraph": true, "useEvidence": true }`
- **Response `200`** (`DigitalTwinProfile`):
```json
{ "profile_id": "uuid", "created_at": "ISO", "subject_type": "individual",
  "inferred_skills": [], "resources": [], "constraints": [], "goals": [], "behavioral_patterns": [],
  "decision_history_summary": "...", "risk_profile": { "level": "moderate", "score": 0.5, "rationale": [] },
  "execution_style": { "style": "...", "rationale": [] }, "team_topology": null,
  "missing_information": ["No geography/context provided."], "contradictions": [],
  "confidenceBreakdown": { "graphCoverage": 0.0, "evidenceCoverage": 1.0, "intakeCompleteness": 0.5, "overallConfidence": 0.4 },
  "source_chunk_ids": [], "external_evidence_ids": [], "methodology": "..." }
```
- **Error `404`:** `GET /digital-twin/{profile_id}` with an unknown id.
- **curl:** `curl -X POST localhost:8000/digital-twin/build -H 'Content-Type: application/json' -d '{"decisionQuestion":"Should I pivot?","goal":"grow"}'`

---

## Simulation

### `POST /simulate`
- **Purpose:** The core call. Returns 3 branches (Conservative/Balanced/Aggressive) OR one branch per option (+ optional hybrid), each with milestones, assumptions, confidence, agent council, evidence snapshot, intake analysis, provenance, and a safety label.
- **Demo?** Yes · **Key?** No (deterministic council by default; `AGENT_MODE=llm` optionally enriches with an LLM but falls back safely).
- **Request** (`SimulationRequest`): `{ "name": "Should I pivot to enterprise?", "type": "Startup", "horizon": "3 years", "risk": 55, "goal": "...", "geography": "US", "options": ["Pivot","Stay"] }`
  - Only `name` is required. `options` accepts plain strings or full `DecisionOption` objects.
- **Response `200`** (`SimulationResponse`) — key top-level fields:
```json
{ "metadata": { "generatedAt": "ISO", "schemaVersion": "1.0.0", "query": "...", "horizonMonths": 36 },
  "timelines": [ /* TimelineBranch[] — id, title, probabilityScore, expectedRegret, confidenceBreakdown,
                    milestones, assumptions, riskFactors, failureModes, leadingIndicators,
                    decisionCheckpoints, claimIds, optionId, ... */ ],
  "recommendedTimelineId": "branch_balanced",
  "externalEvidenceUsed": [ /* EvidenceItem[] snapshot */ ], "isDemoEvidence": true, "evidenceProvider": "demo",
  "agentCouncil": { "agents": [], "consensusScore": 0.62, "mode": "deterministic", "isDeterministic": true, "traces": [] },
  "digitalTwinProfileId": "uuid", "digitalTwinSummary": "...",
  "intakeAnalysis": { /* IntakeAnalysis */ },
  "simulationId": "uuid", "provenanceSummary": { "simulationId": "...", "totalClaims": 16, "claimsByType": {} },
  "safety": { "disclaimer": "...", "high_stakes": false, "category": "Startup", "professional_advice_warning": null },
  "methodology": "Structured heuristic simulation, not a guaranteed prediction. ..." }
```
- **Error `422`:** empty `name`.
- **curl:** `curl -X POST localhost:8000/simulate -H 'Content-Type: application/json' -d '{"name":"Should I pivot?","type":"Startup"}'`

### `GET /simulations?limit=50&offset=0`
- **Purpose:** List persisted simulations (newest first).
- **Demo?** Yes · **Key?** No.
- **Response `200`:** `{ "items": [{ "simulation_id": "uuid", "created_at": "ISO", "query": "...", "recommendedTimelineId": "branch_balanced" }] }`
- **curl:** `curl localhost:8000/simulations`

### `GET /simulations/{simulation_id}`
- **Purpose:** Full stored snapshot (request, response, evidence, twin, council, assumptions, provenance refs).
- **Demo?** Yes · **Key?** No.
- **Response `200`:** `{ "simulation_id": "...", "created_at": "ISO", "request": {}, "response": { /* SimulationResponse */ }, "evidence_snapshot": [], "digital_twin_snapshot": {}, "agent_council_snapshot": {}, "assumptions": [], "provenance_refs": {}, "methodology_version": "heuristic-mvp-1", "engine_version": "1.0.0" }`
- **Error `404`:** unknown id.
- **Related:** `POST /simulations/{id}/replay { "replay_mode": "original_evidence" | "fresh_evidence" }`, `DELETE /simulations/{id}`.

---

## Evidence

### `GET /evidence`
- **Purpose:** Full curated demo evidence pack.
- **Demo?** Yes · **Key?** No.
- **Response `200`** (`EvidenceSearchResponse`): `{ "query": null, "domain": null, "provider": "demo", "isDemoPack": true, "items": [ /* EvidenceItem[] */ ] }`
- **curl:** `curl localhost:8000/evidence`

### `GET /evidence/search?query=<text>&domain=<opt>&k=5`
- **Purpose:** Search evidence via the active provider (`EVIDENCE_PROVIDER`).
- **Demo?** Yes · **Key?** No.
- **Response `200`:** `EvidenceSearchResponse` (`provider` reflects the active provider; `isDemoPack` true only for `demo`).
- **curl:** `curl 'localhost:8000/evidence/search?query=runway%20risk&k=3'`

### `POST /evidence/upload`
- **Purpose:** Add user-supplied evidence (stored locally, `evidence_type=user_supplied`).
- **Demo?** Yes · **Key?** No.
- **Request** (`EvidenceUploadRequest`): `{ "summary": "Our pilot renewed at 2x seats", "tags": ["pilot","renewal"], "confidence": 0.7 }` (either `summary` or `text` required).
- **Response `200`** (`EvidenceItem`) with `source_kind: "uploaded"`, `is_demo_source: false`.
- **Error `422`:** neither `summary` nor `text` provided.
- **curl:** `curl -X POST localhost:8000/evidence/upload -H 'Content-Type: application/json' -d '{"summary":"pilot renewed"}'`

---

## Future Self chat

### `POST /avatar/chat`
- **Purpose:** Answer as the user's "Future Self" within a selected timeline, grounded in memory + evidence, labelled by grounding.
- **Demo?** Yes · **Key?** Optional — uses Groq when `GROQ_API_KEY` is set (`llmBacked: true`), else a deterministic, clearly-labelled fallback (`llmBacked: false`). Never fails for lack of a key.
- **Request** (`AvatarChatRequest`): `{ "message": "What should I prioritize?", "decisionQuestion": "Should I pivot?", "selectedTimelineId": "branch_balanced", "graphNodeIds": [] }`
- **Response `200`** (`AvatarChatResponse`):
```json
{ "content": "The simulation suggests ...", "referencedNodeIds": ["..."],
  "citations": [{ "nodeId": "...", "label": "...", "excerpt": "...", "url": null }],
  "groundingLabel": "mixed", "confidence": 0.61, "llmBacked": false, "claim_id": "uuid" }
```
- **curl:** `curl -X POST localhost:8000/avatar/chat -H 'Content-Type: application/json' -d '{"message":"What first?","decisionQuestion":"Should I pivot?"}'`

---

## Health

### `GET /health`
- **Purpose:** Liveness (process up).
- **Demo?** Yes · **Key?** No.
- **Response `200`:** `{ "status": "ok" }`
- **Related:** `GET /health/ready` (`{ "ready": true }` or `503`), `GET /health/dependencies` (graph/evidence/LLM/storage report).
- **curl:** `curl localhost:8000/health`

### `GET /llm/health`
- **Purpose:** Active LLM + embedding provider status.
- **Demo?** Yes · **Key?** No.
- **Response `200`** (`LlmHealthResponse`):
```json
{ "llm_provider": "groq", "embedding_provider": "sentence_transformers", "amd_mode": false,
  "chat": { "provider": "groq", "model": "llama-3.3-70b-versatile", "available": false,
            "supports_structured_output": true, "supports_embeddings": false, "detail": "GROQ_API_KEY missing — chat unavailable" },
  "embedding": { "provider": "sentence_transformers", "model": "all-MiniLM-L6-v2", "available": true } }
```
- **curl:** `curl localhost:8000/llm/health`
