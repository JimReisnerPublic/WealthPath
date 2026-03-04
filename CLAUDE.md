# WealthPath

AI-powered income and wealth projection planner using SCF data, Monte Carlo simulation,
and Azure OpenAI via **LangChain + LangGraph** (replacing Semantic Kernel).

## Build & Run

```bash
py -m pip install -e ".[dev]"                     # install with dev deps
py -m uvicorn wealthpath.main:app --reload        # run API server
py -m pytest -v                                   # run tests
py scripts/seed_scf_sample.py -n 5000            # generate larger synthetic data
```

## Architecture

- **`src/` layout** — all source under `src/wealthpath/`; prevents accidental root imports
- **Hatchling** build system (PEP 621 `pyproject.toml`)
- **Three core services**: `SCFDataService`, `SimulationEngine`, `AIEngine` — each independently testable
- **FastAPI DI** via `@lru_cache` singletons in `dependencies.py`, overridable in tests via `app.dependency_overrides`
- **API versioning** — domain routes under `/api/v1`; health endpoints at root (`/healthz`, `/readyz`)

## AI Layer (`agent/`)

The `agent/` package is the Python-ecosystem equivalent of what Semantic Kernel + AutoGen
provide on the Microsoft stack.

| Microsoft Stack | Python Equivalent (this project) |
|---|---|
| `Kernel` + `AzureChatCompletion` | `AzureChatOpenAI` in `llm_factory.py` |
| `@kernel_function` Plugin | `@tool` function in `agent/tools/` |
| `kernel.invoke_prompt()` | LCEL chain: `prompt \| llm \| StrOutputParser()` |
| AutoGen `AssistantAgent` | LangGraph `create_react_agent` in `planning_agent.py` |
| SK Handlebars YAML templates | LangChain YAML templates in `agent/prompts/` |

### Two interaction patterns

**1. LCEL chain** (`POST /api/v1/chat/explain`)
Structured prompt → LLM → string output. Good for deterministic, single-turn responses.
```python
chain = prompt | llm | StrOutputParser()
result = await chain.ainvoke({...})
```

**2. LangGraph ReAct agent** (`POST /api/v1/chat/plan`)
Autonomous tool-calling loop. The LLM decides which tools to invoke (cohort lookup,
projection) and iterates until it can answer. This is the AutoGen equivalent.
```python
agent = create_react_agent(llm, tools, state_modifier=system_message)
result = await agent.ainvoke({"messages": [HumanMessage(content=question)]})
```

## Code Conventions

- Python 3.10+ with `from __future__ import annotations`
- Pydantic v2 `BaseModel` for all request/response schemas (in `models/`)
- Type hints everywhere; use `| None` union syntax (not `Optional`)
- Tests use `pytest` with fixtures defined in `tests/conftest.py`
- No Azure OpenAI credentials needed for tests — `AIEngine` gracefully degrades when unconfigured

## Documentation Practice

The developer is learning the Python AI ecosystem from a .NET/C# + Semantic Kernel + AutoGen background.
Treat documentation as a first-class deliverable alongside code.

**When writing or modifying code, always:**

1. **Keep comparison comments in source.** When a pattern has a direct SK/AutoGen/.NET equivalent,
   include a short inline comment showing both sides. These comments are the most valuable learning
   artifact and should not be removed during refactoring.
   ```python
   # SK:  kernel.add_service(AzureChatCompletion(...))
   # LC:  llm = AzureChatOpenAI(...)   ← LLM is a plain object, not a registry entry
   ```

2. **Update `docs/` when a new concept is introduced.** If we add a new pattern (e.g. a new
   LangGraph node type, a new FastAPI technique, a new Pydantic feature), add or extend the
   relevant doc in `docs/`. Do not wait to be asked.
   - New Python language feature → `docs/python-primer.md`
   - New FastAPI pattern → `docs/fastapi.md`
   - New LangChain / LCEL pattern → `docs/langchain.md`
   - New LangGraph / agent pattern → `docs/langgraph.md`

3. **Record gotchas when we hit them.** If something behaves unexpectedly for a C# developer
   (e.g. mutable default arguments, `is` vs `==`, async differences), add it to the relevant
   doc's gotchas section so it isn't forgotten.

4. **Doc updates go in the same response as the code change** — not as a separate follow-up step.

## Current Work

> This section is updated at the end of each session so the next session can resume without
> re-reading the full conversation. When the user says "update CLAUDE.md with where we left
> off", rewrite the block below with current state.

### Status: Phase 5 (Azure Deployment) — complete ✅ | Phase 6 (Polish) — in progress 🔄

**What's done:**
- FastAPI backend with `src/` layout, hatchling build, Pydantic v2 models
- Three core services: `SCFDataService` (SCF survey data), `SimulationEngine` (Monte Carlo), `AIEngine`
- Semantic Kernel replaced with **LangChain + LangGraph** throughout
- Real SCF data support: `scripts/load_scf_data.py` processes Federal Reserve SCF 2022 Stata file → Parquet
- **Phase 2 ML surrogate model — complete ✅**
  - Retrained with 12 features including `guaranteed_income_fraction`; R²=0.9817, MAE=0.034
  - `data/surrogate_model.joblib` — trained model artifact (gitignored, loaded from Blob in prod)
  - `POST /api/v1/plan/evaluate` — ~1ms with surrogate model; falls back to Monte Carlo
  - MLflow experiment tracking working locally (`mlruns/` gitignored)
- **Phase 3 React frontend — complete ✅**
  - `frontend/` — Vite + React + TypeScript + Tailwind CSS v4 + shadcn/ui
  - Smoke tested end-to-end: form → surrogate result → SHAP drivers all working
- **Phase 4 — dropped ✅** — stateless by design; no user data stored anywhere
- **Azure OpenAI — complete ✅**
  - `gpt-5-mini` (Global Standard) deployed to existing `guituitive-aoai` resource in `rg-notefinder-app-prod`
  - Shared with Guituitive (Guituitive already live on gpt-5-mini in production)
  - **API version:** `2024-10-21` — the Azure OpenAI REST API version (distinct from the model version `2025-08-07`)
- **Blob Storage model loading — complete ✅**
  - `surrogate_model_service.py` has `load_from_blob()` method
  - `dependencies.py` auto-selects blob vs local based on `AZURE_STORAGE_CONNECTION_STRING` env var
  - `surrogate_model.joblib` uploaded to `stwealthpath/models` blob container
- **GitHub repo — pushed ✅**
  - Public repo; `docs/learning/`, `Implementation_Plan.md`, data files, secrets all gitignored
  - `.github/workflows/deploy-api.yml` — builds & deploys API on push to main (src/**, Dockerfile, pyproject.toml)
  - `.github/workflows/deploy-frontend.yml` — may be superseded by Azure-generated workflow (see below)
- **Azure infrastructure — complete ✅**
  - `rg-wealthpath` resource group created (eastus)
  - `stwealthpath` storage account + `models` container + model blob uploaded
  - `crwealthpath` ACR created; initial image built and pushed
  - `cae-wealthpath` Container Apps environment created
  - `ca-wealthpath-api` Container App created with env vars; secrets `aoai-key` + `storage-conn` set
  - `swa-wealthpath` Static Web App created via portal, connected to GitHub repo (auto-generated workflow)
- **Keys rotated ✅** — both Azure OpenAI key and storage account key were exposed in chat and should be rotated
- **AZURE_OPENAI_ENDPOINT** fixed — was placeholder, now set to `https://eastus.api.cognitive.microsoft.com/`
- **VITE_API_BASE_URL** set in SWA app settings — points to Container App FQDN
- **SWA workflow conflict resolved ✅** — pulled Azure's auto-generated workflow; removed redundant `deploy-frontend.yml`
- **`AZURE_CREDENTIALS` GitHub secret added ✅** — `deploy-api.yml` CI/CD is fully functional
- **`gpt-4o-mini` deployment retired ✅** — cleaned up from `guituitive-aoai` resource
- **Streaming AI chat — complete ✅** (design decisions in section below)
  - `POST /api/v1/chat/stream` — SSE streaming via LangGraph `astream_events()`
  - `ChatPanel` component — multi-turn conversation, typewriter streaming, tool-call status display
  - Local smoke tested end-to-end
  - `ca-wealthpath-api` Container App env var `AZURE_OPENAI_API_VERSION=2024-10-21` applied

**To run locally (no Azure required):**
```bash
# Terminal 1 — API  (from wealthpath/ directory)
py -m uvicorn wealthpath.main:app --reload

# Terminal 2 — Frontend  (from wealthpath/ directory)
cd frontend && npm run dev
# → http://localhost:5173
```

**What's next — Phase 6 Polish:**
1. **Merge streaming branch to main and deploy**
2. **README polish** — live demo link, architecture diagram, SK-vs-LC comparison table
3. **Observability** — LangChain callback logging for production AI visibility
4. **Future refactor** (deferred): move Python source into `backend/` folder to match `frontend/` layout

---

### Chat streaming — design decisions (agreed)

**Goal:** Add a contextual multi-turn chat panel below the evaluation results.

**API:**
- Replace `/api/v1/chat/explain` and `/api/v1/chat/plan` with a single `POST /api/v1/chat/stream`
- Response: `text/event-stream` (SSE) via FastAPI `StreamingResponse`
- Three event types:
  ```
  data: {"type": "status", "text": "Looking up cohort data..."}   ← agent tool call in progress
  data: {"type": "token",  "text": "Retiring at 65 "}             ← LLM output token
  data: {"type": "done"}                                           ← sentinel
  ```
- Uses `agent.astream_events()` (LangGraph) to get both tool-call events and token-level streaming

**Request model — breaking change from existing `ChatRequest`:**
```python
# New shape (replaces question: str)
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    household: HouseholdProfile
    messages: list[ChatMessage]   # full conversation history; last entry is the new question
    context: dict | None          # optional evaluation result for grounding
```

**Multi-turn:** History accumulates client-side; full `messages` list is sent with every request. Server remains stateless. Cap at last ~10 messages if context window becomes a concern (not needed for demo).

**Frontend:**
- New `ChatPanel` component — appears below the main layout only after an evaluation result exists
- Conversation display: user bubbles right-aligned, assistant bubbles left-aligned with typewriter streaming
- Tool status events render as a transient italic line above the growing assistant bubble
- SSE client: raw `fetch` + `ReadableStream` (no library — simpler to explain in interviews)
- `App.tsx` passes `result` + `household` as props to `ChatPanel` for context grounding

**Layout:**
```
┌─────────────────────────────────────────────────┐
│ PlanForm  │  ResultsCard                         │
│           │  CohortCard                          │
├───────────┴─────────────────────────────────────┤
│ ChatPanel (full width, shown after first result) │
│  user:  "What if I retire at 65?"               │
│  agent: [Analyzing cohort data...]              │
│          "Retiring at 65 raises your score..."  │
│  [Ask about your results...          ] [Send]   │
└─────────────────────────────────────────────────┘
```

**Build order:**
1. `models/chat.py` — new `ChatMessage` + updated `ChatRequest`
2. `services/ai_engine.py` — new `stream_chat()` async generator method
3. `api/routers/chat.py` — new `/stream` route; keep old routes as non-streaming fallbacks (don't delete yet)
4. `frontend/src/components/ChatPanel.tsx` — new component
5. `frontend/src/App.tsx` — wire in `ChatPanel`

**Open design decisions:**

*Savings granularity refactor — complete ✅*
`has_retirement_account` was replaced with `investable_savings: float` in `HouseholdProfile`.
Employer match fields and `social_security_start_age` / `pension` / `other_income` are
frontend-only — collapsed into `savings_rate` and `social_security_annual` before the API call.

*Known dead fields (benign, low priority):*
- `education: EducationLevel` in Python `HouseholdProfile` — absent from TypeScript, ignored by surrogate
- `net_worth` sent in `HouseholdProfile` but surrogate uses `investable_savings` for its savings features

*Note on Monte Carlo fallback:*
The `_monte_carlo_fallback` in `evaluate.py` uses `SimulationEngine`, which only models wealth
accumulation (no retirement phase, no spending, no SS). Not a proper retirement success simulation.
The proper two-phase simulation lives in `scripts/generate_training_data.py::simulate_success_probability()`
and is only used offline. If a live MC fallback is ever needed, extract that function into a service.

Deferred: pension COLA flag (nominal vs real), two-person retirement/longevity ages,
per-account return rates, Roth vs traditional tax treatment.

**Key files to know:**
- [frontend/src/](frontend/src/) — React frontend source
- [frontend/src/components/PlanForm.tsx](frontend/src/components/PlanForm.tsx) — main form (4 sections)
- [frontend/src/components/ResultsCard.tsx](frontend/src/components/ResultsCard.tsx) — results + SHAP drivers
- [frontend/src/types/api.ts](frontend/src/types/api.ts) — TypeScript types mirroring Pydantic models
- [src/wealthpath/agent/](src/wealthpath/agent/) — all AI orchestration code
- [src/wealthpath/services/surrogate_model_service.py](src/wealthpath/services/surrogate_model_service.py) — ML model serving
- [src/wealthpath/api/routers/evaluate.py](src/wealthpath/api/routers/evaluate.py) — `/plan/evaluate` endpoint
- [scripts/generate_training_data.py](scripts/generate_training_data.py) — SCF-anchored training data generation
- [scripts/train_surrogate_model.py](scripts/train_surrogate_model.py) — XGBoost training
- [docs/overview.md](docs/overview.md) — product overview (start here)
- [docs/data-sources.md](docs/data-sources.md) — SCF data and training data pipeline
- [docs/learning/ml-model.md](docs/learning/ml-model.md) — ML surrogate model concepts
- [docs/learning/training-data-pipeline.md](docs/learning/training-data-pipeline.md) — synthetic data generation, Monte Carlo phases, success definition
- [docs/learning/ml-training-reference.md](docs/learning/ml-training-reference.md) — ML deep dive (gradient boosting, SHAP)
- [docs/learning/interview-prep.md](docs/learning/interview-prep.md) — interview talking points
- [docs/learning/](docs/learning/) — all developer learning notes and diagrams
