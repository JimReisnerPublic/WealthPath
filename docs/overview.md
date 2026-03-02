# WealthPath — Overview

WealthPath is a retirement readiness estimator. A user enters their financial
profile and immediately sees a probability of not running out of money in
retirement, key drivers of that outcome, and how they compare to similar
households from Federal Reserve survey data.

---

## Who It's For

Someone who wants a quick, honest answer to "am I on track?" without building
a full financial plan. WealthPath is a signal, not a substitute for a planner.

---

## User Journey

1. Open the app → see a blank two-column layout
2. Fill in the form (About You, Finances, Retirement Plan, Guaranteed Income,
   Investment Strategy) — or load one of six pre-built example households
3. Click **Estimate My Plan**
4. Results appear in the sticky right panel:
   - A large probability number ("78%") colored by success label
   - A badge: **on track** (≥80%) / **at risk** (60–79%) / **critical** (<60%)
   - Top 5 SHAP drivers — what's helping and what's hurting the score
   - A **Peer Comparison** card showing income and net worth percentile vs.
     similar-age households from the 2022 Survey of Consumer Finances

---

## System Architecture

```
Browser (React + Vite)
  │
  │  POST /api/v1/plan/evaluate     POST /api/v1/cohort/compare
  │  (run in parallel on submit)
  │
  │  POST /api/v1/chat/explain      POST /api/v1/chat/plan
  │  (chat panel — requires Azure OpenAI or Anthropic)
  ▼
FastAPI (uvicorn)
  │
  ├─ EvaluateRouter ──► SurrogateModelService (XGBoost, <1ms)
  │                       └─ fallback: SimulationEngine (Monte Carlo, ~300ms)
  │
  ├─ CohortRouter  ──► SCFDataService (weighted quantiles on SCF 2022 parquet)
  │
  └─ ChatRouter    ──► /explain: LCEL chain (prompt → LLM → plain-language explanation)
                       /plan:    LangGraph ReAct agent (autonomous tool-calling loop)
                                   tools: cohort_lookup, projection, surrogate_evaluate
```

The ML model was trained on outputs from the Monte Carlo simulation engine
(`scripts/generate_training_data.py` → `scripts/train_surrogate_model.py`).
At runtime the surrogate replaces the simulation, giving instant results with
R²=0.98 and MAE≈3.4 percentage points vs. the full simulation.

---

## Form Inputs and What the Model Receives

The form collects more fields than the model strictly needs. Several are
combined or adjusted before the API call. Notable calculations:

### Effective Savings Rate

The "Your Savings Rate" slider captures employee contributions only. If the
user enters employer 401(k) match details, an effective rate is computed:

```
effective = savings_rate + min(savings_rate, ceiling%) × match_rate
```

Capped at 80%. This effective rate is sent to the model as `savings_rate`.

### Guaranteed Income Total

Social Security, pension, and other income are collected separately with a
monthly/annual toggle. They are summed and converted to annual before being
sent as `social_security_annual`.

### Effective Social Security (SS Start Age Adjustment)

This is the most important input-level calculation in the form.

**The problem:** The surrogate model treats `social_security_annual` as a
constant income stream throughout retirement. But most people retire before
they start collecting Social Security — especially early retirees. Crediting
the full SS amount from day one of retirement overstates income during the
gap years and inflates the success probability.

**The fix:** When SS start age is later than planned retirement age, the raw
SS amount is scaled down to its time-weighted equivalent over the full
retirement horizon:

```
years_in_retirement = life_expectancy − retirement_age
years_receiving_SS  = max(0, life_expectancy − ss_start_age)

effective_SS = raw_SS × (years_receiving_SS / years_in_retirement)
```

**Example** (retire at 60, SS at 67, live to 90):
```
years_in_retirement = 90 − 60 = 30
years_receiving_SS  = 90 − 67 = 23

effective_SS = $57,500 × (23 / 30) = $44,083/yr
```

The model receives $44,083 rather than $57,500. The form shows both: the raw
total the user will actually receive, and a muted note explaining the
adjustment ("SS delayed 7 yrs past retirement — model uses ~$44,083/yr
effective SS").

**Why not model the step function exactly?** The surrogate model has a single
`social_security_annual` feature — it cannot represent income that starts
mid-retirement. The time-weighted average is the best single-number
approximation. A future improvement would be to pass separate pre- and
post-SS spending periods, or to retrain the model with SS start age as a
feature.

**Default:** 67 — the full Social Security retirement age for people born
after 1960. Users who plan to take SS at 62 (early, reduced benefit) or
delay to 70 (maximum benefit) should update this field.

---

## Peer Comparison

The cohort comparison calls `POST /api/v1/cohort/compare` in parallel with the
evaluation. It filters the SCF 2022 parquet to households within ±5 years of
the user's age, then computes weighted percentile ranks for income and net
worth using `survey_weight` (each SCF household represents thousands of real
US households).

Education is intentionally excluded from the cohort filter. The SCF Summary
Extract merges bachelor's and graduate degrees into one category (EDCL=4),
making education-based filtering misleading. Age-only cohorts are simpler and
accurate for the "how do I compare to peers my age?" question.

---

## Chat / AI Layer

### What's built

Two backend endpoints exist and are fully implemented with LangChain + LangGraph:

| Endpoint | Pattern | Purpose |
|---|---|---|
| `POST /api/v1/chat/explain` | LCEL chain | Takes the evaluation result and explains it in plain language — "why is my score 73% and what's the biggest thing I can change?" |
| `POST /api/v1/chat/plan` | LangGraph ReAct agent | User asks a free-form question; the agent autonomously calls tools (cohort lookup, projection, surrogate evaluation) and reasons toward an answer |

The ReAct agent is the autonomous equivalent of AutoGen — it decides which tools to call,
calls them, reads the results, and iterates until it can answer. See
[CLAUDE.md](../CLAUDE.md) and [docs/langgraph.md](langgraph.md) for the implementation
details.

### What's missing

1. **LLM credentials** — the backend is wired to `AzureChatOpenAI`. Without an Azure
   OpenAI endpoint + API key in `.env`, both endpoints return 500. To test without Azure,
   swap to `ChatAnthropic` in `agent/llm_factory.py` — the LangChain interface is
   identical and only the constructor arguments change.

2. **Frontend chat panel** — no chat UI exists yet. The natural placement is a third
   column (or slide-out drawer) that appears after the user submits their plan, offering
   to explain the result or answer follow-up questions.

### Where chat fits in the user journey

The results card already answers *what* (the probability) and *why at a glance* (top
SHAP drivers). Chat addresses the questions that naturally follow:

- **Explain** — "What does 'Net spending replacement rate' mean for me specifically?"
- **What-if** — "What would my score be if I retire at 63 instead of 60?" *(agent calls
  surrogate_evaluate with modified inputs)*
- **Peer context** — "How does my savings compare to people my age?" *(agent calls
  cohort_lookup)*
- **Advice** — "What's the single most impactful change I could make?" *(agent reads
  SHAP drivers and reasons about levers)*

### What the agent knows (and what it doesn't — current gaps)

`ChatRequest` currently carries only `HouseholdProfile` (age, income, net_worth, etc.)
plus the user's question and an optional free-form `context` dict. This creates three
gaps that must be addressed before the chat endpoints are useful:

**Gap 1 — The score and SHAP drivers aren't passed to the LLM.**
For `/explain`, the system prompt gets the user's household demographics and question,
but *not* the 73% score or the top SHAP drivers. The LLM can only reason about "why 73%"
if the frontend explicitly includes the `EvaluationResponse` in the `context` field:
```python
ChatRequest(
    household=...,
    question="why is my score 73%?",
    context={"score": 0.73, "label": "at risk", "top_drivers": [...]}  # ← must be added by frontend
)
```
Without this, the LLM is answering blind.

**Gap 2 — Retirement planning parameters aren't in `ChatRequest`.**
`ChatRequest.household` is a `HouseholdProfile`, which has demographics but no
`planned_retirement_age`, `savings_rate`, `social_security_annual`, etc. The agent
can't run a meaningful what-if ("retire at 63 instead of 60") without these.
Fix: expand `ChatRequest` to include the full `EvaluationRequest` fields, or pass
them in `context`.

**Gap 3 — The `evaluate_retirement_plan` agent tool uses a placeholder household.**
In `agent/tools/evaluate_tools.py`, the tool constructs a `HouseholdProfile` with
hardcoded values (age=45, income=$80k, net_worth=$200k) instead of using the actual
user's data. What-if tool calls therefore return results for a fictional household.
Fix: pass the real `HouseholdProfile` into the tool closure at construction time.

### Financial advice boundary

**The legal line:** explaining a model's output is not the same as giving personalized
investment advice. Personalized investment advice — recommending specific securities,
funds, or tax strategies for a named individual — requires registration as an Investment
Adviser (SEC or state-registered RIA). WealthPath is a scenario modeler, not an RIA.

**What the agent is allowed to do:**

| Allowed | Example |
|---|---|
| Explain model output | "Your net spending replacement rate is the #1 factor pulling your score down." |
| Run what-if scenarios | "If you increase your savings rate to 15%, your score rises from 68% to 74%." |
| Surface cohort data | "Your savings puts you in the 62nd percentile for your age group." |
| Explain concepts | "Equity fraction affects expected return and volatility in the simulation." |

**What the agent must redirect:**

| Redirected | Reason |
|---|---|
| "Which funds should I buy?" | Specific product recommendation — requires RIA |
| "Should I do a Roth conversion?" | Tax advice — requires CPA or tax attorney |
| "Roll over my 401(k) to an IRA?" | Specific account action recommendation |
| "Am I better off with whole life insurance?" | Insurance product recommendation |

**How it works in the prompts:** Both system prompts (the LCEL chain in `ai_engine.py`
and the ReAct agent in `planning_agent.py`) instruct the LLM to:

1. Decline the product/tax-specific part of the question
2. Refer the user to a CFP or RIA for that part
3. Offer to model the relevant scenario instead — keeping the interaction useful

Example of a well-handled response when a user asks "should I do a Roth conversion?":

> "I can't advise on whether a Roth conversion is right for your situation — that involves
> tax projections that depend on your current and future bracket, which a CPA or CFP would
> need to assess. What I can do is model what happens to your retirement success probability
> if you assume a higher effective savings rate, which is one downstream effect of
> tax-efficient contributions. Want me to run that?"

**Frontend consideration:** The chat panel UI should include a persistent disclaimer:
*"WealthPath provides scenario modeling, not personalized financial advice. For investment
product or tax recommendations, consult a licensed CFP or RIA."*

### Activating without Azure (development shortcut)

In [src/wealthpath/agent/llm_factory.py](../src/wealthpath/agent/llm_factory.py),
replace:
```python
from langchain_openai import AzureChatOpenAI
llm = AzureChatOpenAI(...)
```
with:
```python
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-sonnet-4-6", api_key=os.environ["ANTHROPIC_API_KEY"])
```
Install: `pip install langchain-anthropic`. Everything else — the ReAct agent, LCEL
chain, tools, prompts — works unchanged.

---

## Known Limitations

| Limitation | Impact | Planned fix |
|---|---|---|
| Single SS start age, not a step function | Overstates SS in gap years for early retirees (mitigated by time-weighting) | Retrain model with SS start age feature |
| Single retirement age for household | Can't model spouses retiring at different times | Two-person inputs |
| Savings rate % vs. dollar contributions | Undercounts savings for people with complex contribution structures | Optional annual $ contribution field |
| SCF education merges BA + graduate | Education filter removed; age-only cohort used instead | Use full SCF public dataset |
| Surrogate model MAE ≈ 3.4pp | Results within ±3–4pp of full Monte Carlo | Retrain on larger dataset |

See [boldin-comparison.md](boldin-comparison.md) for a detailed real-world
comparison against a Boldin plan, which quantifies several of these gaps.
