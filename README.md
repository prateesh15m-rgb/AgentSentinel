# AgentSentinel – Universal ADK Supervisor for Evaluating & Improving Agents

**Repo:** `agentops-autopilot`  
**Product name:** **AgentSentinel**  
**Capstone context:** Google AI Agents Intensive 2025 – Multi-agent evaluation & improvement for ADK-based apps.

---

AgentSentinel is a **control plane for agentic apps** built on the **Google Agent Development Kit (ADK)**.

This repo demonstrates, end-to-end, how to:

1. **Discover** an ADK app’s capabilities and IO schema  
2. **Run the AUT (agentic app) once** and capture a structured response  
3. **Evaluate** the AUT using:
   - Simple **rule-based metrics** (task success, latency)
   - **LLM-judge metrics** using Gemini (rubric-driven)  
4. **Log traces** to a JSONL store for observability & metrics  
5. **Summarize metrics across versions** (v1 → v2 → v3, travel_v1 → travel_v2)  
6. **Propose improvements** using a Planner/Critic pattern that:
   - Reads eval history + best practices  
   - Returns a **changeset** (config patch + new golden testcases)  
7. **Re-evaluate** the improved version and **compare** its metrics.

The reference use case is a **Travel Itinerary Planner** AUT (`travel_planner`), but the architecture is designed to be **framework-agnostic** and re-usable for other ADK apps.

---

## 1. High-Level Architecture

At a high level, AgentSentinel sits **on top of** an ADK app and adds:

- **Supervisor CLI** for discovery, run, eval, metrics, compare  
- **Eval Engine** for rule + LLM metrics  
- **Planner Engine** for improvement proposals  
- **Trace store** for evaluation + production traces  
- **Memory of best practices** to guide the planner

```text
          +------------------------+
          |   AgentSentinel CLI    |
          |  scripts/run_supervisor.py
          +-----------+------------+
                      |
                      v
           +----------+----------+
           |      AUTSpec        |   (core/aut_spec.py)
           |  travel_planner_v1  |
           +----------+----------+
                      |
       +--------------+-------------------------+
       |                                        |
       v                                        v
+-------------+                        +---------------------+
|   ADK App   |                        |   Eval Engine       |
| Travel AUT  |                        | agentops/eval_*     |
| v2_adk/...  |                        | + TravelEvalPack    |
+------+------+                        +----------+----------+
       |                                          |
       v                                          v
+-------------+                          +-------------------+
|  Traces     | <----------------------> |  Planner Engine   |
| data/traces.jsonl                      | agentops/improvement
+-------------+                          +-------------------+
                                                 |
                                                 v
                                      +------------------------+
                                      |  New configs + tests   |
                                      |   travel_v2, v3, ...   |
                                      +------------------------+
````

---

## 2. Directory Structure (Important Bits)

From `dump_repo.py`:

```text
.
├─ .env                         # Local env vars (GOOGLE_API_KEY, etc.)
├─ requirements.txt
├─ dump_repo.py
├─ infra/
│   ├─ env.py                   # Env helpers (API keys, etc.)
│   ├─ traces_store.py          # JSONL trace logger + loader
│   └─ memory_store.py          # Generic memory helpers
├─ core/
│   ├─ aut_spec.py              # AUTSpec model & loader
│   ├─ aut_client.py            # Generic AUT client interface
│   └─ ...
├─ agentops/
│   ├─ eval_engine/             # Evaluation engine
│   │   ├─ engine.py            # EvalEngine orchestration
│   │   └─ models.py            # Eval record / metric models
│   ├─ eval_packs/
│   │   ├─ travel_pack.py       # Travel-specific eval pack
│   │   └─ generic_adk_pack.py  # Generic eval pack (if needed)
│   ├─ improvement/
│   │   ├─ planner.py           # PlannerEngine (Planner + Critic)
│   │   ├─ models.py            # ChangeSet, ConfigPatch models
│   │   └─ apply_changeset.py   # Helpers to apply config patches
│   ├─ memory/
│   │   └─ best_practices.py    # Reads/writes best_practices.jsonl
│   ├─ agents/
│   │   ├─ discovery_agent.py   # For ADK discovery
│   │   ├─ eval_agent.py        # Multi-test eval
│   │   ├─ planner_agent.py     # Planner LLM wrapper
│   │   └─ human_agent.py       # Stub for future human loop
│   ├─ run_full_eval.py         # Run all evals for default AUT
│   ├─ run_full_eval_for_version.py
│   ├─ run_metrics_summary.py   # Aggregate metrics from traces.jsonl
│   ├─ run_planner_once.py      # Run PlannerEngine once
│   └─ travel_planner_planner.py# Travel-specific planner wrapper
├─ scripts/
│   ├─ run_supervisor.py        # MAIN CLI for AgentSentinel
│   ├─ run_travel_v1_eval.py    # Convenience eval script
│   ├─ run_travel_v2_eval.py
│   ├─ discover_travel_v1.py
│   ├─ probe_travel_v1.py
│   └─ test_google_apis.py
├─ v2_adk/
│   ├─ travel_planner/
│   │   ├─ aut_client_travel.py # AUTClient wrapper for travel_planner
│   │   ├─ app/
│   │   │   ├─ main.py          # ADK app entrypoint + runtime
│   │   │   ├─ travel_runtime.py
│   │   │   ├─ agents/travel_root_agent.py
│   │   │   └─ tools/
│   │   │       ├─ dest_info_tool.py
│   │   │       ├─ weather_tool.py
│   │   │       └─ budget_tool.py
│   │   ├─ tools/google_maps_client.py
│   │   ├─ specs/
│   │   │   ├─ travel_planner_config_v1.json
│   │   │   ├─ travel_planner_config_v2.json
│   │   │   ├─ travel_planner_v1.aut.yaml   # AUTSpec for travel_v1
│   │   │   └─ agent_profile_travel_v1.json
│   │   └─ tests/
│   │       ├─ golden/travel_golden_v1.csv  # Golden testcases
│   │       └─ eval/
│   │           ├─ run_travel_v1_eval.py
│   │           └─ run_travel_v2_eval.py
│   ├─ discovery/
│   │   └─ adk_discovery.py     # Generic ADK discovery helpers
│   └─ supervisor/
│       ├─ tools/               # Supervisor tools (eval, metrics, compare)
│       └─ ...
└─ data/
    ├─ best_practices.jsonl     # Memory for PlannerEngine
    ├─ golden_set.csv           # Generic golden set
    ├─ traces.jsonl             # All eval traces (auto-created)
    └─ sample_docs/             # Example docs (safe)
```

---

## 3. How AgentSentinel Maps to Course Concepts

**Course concepts** → **Where they show up in this repo**:

1. **Agentic Apps (ADK)**

   * `v2_adk/travel_planner/app/main.py` – `create_app()` returns the root ADK agent.
   * `v2_adk/travel_planner/app/agents/travel_root_agent.py` – system prompt & orchestration.

2. **Tools**

   * `v2_adk/travel_planner/app/tools/`:

     * `dest_info_tool.py` – static destination profile
     * `weather_tool.py` – seasonal profile
     * `budget_tool.py` – budget breakdown

3. **Memory**

   * **Eval/Improvement memory:**

     * `data/best_practices.jsonl` – LLM-curated best practices per metric
     * `agentops/memory/best_practices.py`
   * **Trace/metrics memory:**

     * `data/traces.jsonl` via `infra/traces_store.py`

4. **Evals**

   * `agentops/eval_engine/engine.py` – `EvalEngine`
   * `agentops/eval_packs/travel_pack.py` – `TravelEvalPack`

     * Uses simple **rule metrics**: `task_success`, `latency_ms`
     * Uses **LLM judge** with Gemini model (`gemini-2.5-pro`) and rubric `travel_itinerary_v1`
   * Golden dataset: `v2_adk/travel_planner/tests/golden/travel_golden_v1.csv`

5. **Observability**

   * `infra/traces_store.py` – all runs are logged as JSONL:

     * input, output, version, metrics, latency, tool calls
   * `agentops/run_metrics_summary.py` – aggregates per-version stats
   * Supervisor command `metrics` & `compare` summarize from traces.

6. **Planner / Auto-Improvement**

   * `agentops/improvement/planner.py` – `PlannerEngine`:

     * reads traces + best practices
     * generates a **ChangeSet** (config patch + new testcases)
   * `agentops/run_planner_once.py` – CLI to invoke PlannerEngine.

---

## 4. Travel Itinerary Planner AUT (`travel_planner`)

The **AUT (Agentic Use-case Template)** for the capstone is a **Travel Itinerary Planner**.

### 4.1 AUTSpec

Defined in:

* `v2_adk/travel_planner/specs/travel_planner_v1.aut.yaml`

Key pieces (also visible via Supervisor `discover`):

* **Inputs schema** (JSON):

  * `destination` (required)
  * `start_date`, `end_date`, `duration_days`
  * `origin`, `budget_total`, `travel_style` (`relaxed|balanced|packed`)
  * `interests` (list of strings)
  * `travelers_profile` (adults, children, notes)
  * `constraints` (mobility, must_include, must_avoid)

* **Outputs schema**:

  * `itinerary_days[]`:

    * `day_index`, `title`, `summary`, `activities[]`
  * `budget_summary`:

    * `currency`, `total_estimated`, `per_day_estimate`, `breakdown`
  * Optional: `season_notes`, `assumptions[]`, `warnings[]`

* **Tools**:

  * `dest_info_tool`, `weather_tool`, `budget_tool`

* **Capabilities**:

  * Single task `"create_itinerary"` (batch mode true, non-interactive)

* **Evaluation config**:

  * `default_pack: travel_pack`
  * `metrics: [task_success, judge_score_avg, judge_score_p95, latency_ms_p95]`
  * `llm_judge: model = gemini-2.5-pro, rubric_id = travel_itinerary_v1`
  * `extra.golden_path = v2_adk/travel_planner/tests/golden/travel_golden_v1.csv`

### 4.2 Runtime Implementation

`v2_adk/travel_planner/app/main.py`:

* Loads config via `load_travel_config(...)`

* Pulls Gemini model using `GOOGLE_API_KEY` or `GEMINI_API_KEY`

* Calls tools:

  * `dest_info(...)`
  * `seasonal_weather_profile(...)`
  * `estimate_budget(...)`

* Builds a **safe prompt** (no fstring injection, no backticks in user text)

* Calls `model.generate_content(prompt)`

* Builds `structured_plan`:

  * `itinerary_days` via `build_itinerary_days(...)`
  * `budget_summary` via `build_budget_summary_from_profile(...)`
  * `season_notes` via `build_season_notes_from_profile(...)`
  * `assumptions` and `warnings` parsed from the free-form answer

* Returns a dict:

  ```python
  {
    "version_id": version_id,
    "request": trip_request,
    "structured_plan": structured,
    "answer_markdown": answer_text,
    "latency_ms": latency_ms,
    "tool_outputs": tool_outputs,
  }
  ```

This **matches the AUTSpec output schema**, which is why the EvalEngine and Supervisor work without further wiring.

---

## 5. End-to-End: Running AgentSentinel

### 5.1 Setup

From repo root:

```bash
python -m venv .venv
source .venv/bin/activate   # On macOS / Linux
# .venv\Scripts\activate    # On Windows

pip install -r requirements.txt
```

Set your Gemini key (or GOOGLE_API_KEY):

```bash
export GEMINI_API_KEY="YOUR_KEY_HERE"
# or
export GOOGLE_API_KEY="YOUR_KEY_HERE"
```

(You can also put this in `.env`, which is git-ignored.)

Test that Gemini calls are working:

```bash
python scripts/test_google_apis.py
```

---

### 5.2 Supervisor CLI (Core AgentSentinel Experience)

Run:

```bash
python scripts/run_supervisor.py
```

You’ll see something like:

```text
===========================================================
   AgentOps Autopilot — Universal ADK Supervisor (CLI)
===========================================================
Loaded AUT spec: .../v2_adk/travel_planner/specs/travel_planner_v1.aut.yaml
AUT ID: travel_planner | Version: travel_v1
Type 'help' for all commands.
-----------------------------------------------------------
Supervisor >
```

#### Key commands

1. **discover – inspect AUT capabilities**

```text
Supervisor > discover
```

Outputs the resolved AUTSpec including inputs/outputs schema, tools, and evaluation config.

2. **profile – evaluation profile only**

```text
Supervisor > profile
```

Shows evaluation configuration for this AUT/version: metrics, llm_judge model, golden path.

3. **eval – run full eval pack on golden CSV**

```text
Supervisor > eval
```

* Loads `travel_golden_v1.csv`

* Runs AUT for each testcase

* Calls Gemini judge for each row

* Aggregates metrics:

  ```json
  "aggregated_metrics": {
    "judge_score_avg": 5.0,
    "judge_score_p95": 5.0,
    "latency_ms_p95": 13995.78,
    "task_success_rate": 1.0
  }
  ```

* Logs each run as a trace into `data/traces.jsonl`.

4. **run – manual single run**

```text
Supervisor > run
Enter a JSON request.
Example: {"destination": "Tokyo", "duration_days": 3, "budget_total": 1500}

JSON > {"destination": "Tokyo", "duration_days": 3, "budget_total": 1500}
```

Supervisor then:

* Calls the ADK app’s `create_app` / `run_travel_planner_once`
* Returns:

  * `answer` (markdown)
  * `structured_plan` with `itinerary_days`, `budget_summary`, etc.
  * `latency_ms`
  * raw tool outputs

5. **metrics – summarize from traces**

```text
Supervisor > metrics
```

This reads `data/traces.jsonl` and prints per-version statistics:

```text
=== Version: travel_v1 ===
  Test cases: 45
  Average score: 4.84
  Average latency: 13277.0 ms
  p50 latency: ...
  p95 latency: ...
  Failing (<4): 2
  Pass rate: 95.6%

=== Version: travel_v2 ===
  Test cases: 12
  Average score: 5.00
  Pass rate: 100.0%
```

6. **compare – compare two versions**

```text
Supervisor > compare travel_v1 travel_v2
{
  "version_1": "travel_v1",
  "version_2": "travel_v2",
  "avg_score_v1": 4.84,
  "avg_score_v2": 5.0,
  "delta": 0.15
}
```

This shows that **travel_v2** is an improvement over travel_v1 according to the LLM judge.

7. **exit**

```text
Supervisor > exit
Goodbye.
```

---

### 5.3 Running Eval Scripts Directly (Optional)

Instead of using Supervisor, you can call helper scripts:

```bash
# Evaluate travel_v1 using golden v1 CSV
python scripts/run_travel_v1_eval.py

# Evaluate travel_v2 using its config + golden v2
python scripts/run_travel_v2_eval.py
```

These script wrappers use the same `TravelEvalPack` and `EvalEngine` under the hood and also log to `data/traces.jsonl`.

---

## 6. Planner Engine & Improvement Loop

The **Planner Engine** is AgentSentinel’s “auto-improver”.

### 6.1 Where it lives

* `agentops/improvement/planner.py` – `PlannerEngine`
* `agentops/improvement/models.py` – `ChangeSet`, `ConfigPatch`, etc.
* `agentops/memory/best_practices.py` – long-term memory
* `data/best_practices.jsonl` – store of learning over time
* `agentops/run_planner_once.py` – CLI entrypoint

### 6.2 What PlannerEngine does

Given an AUTSpec (for example `travel_planner_v1.aut.yaml`), it:

1. Reads **Eval history** from `data/traces.jsonl`

   * For all versions of this AUT (v1, v2, v3, travel_v1, travel_v2)
2. Cross-references with **best practices** from `data/best_practices.jsonl`
3. Calls a **Planner LLM agent** (see `agentops/agents/planner_agent.py`) with:

   * Current scores / failure cases
   * Target metrics (e.g., raise average score > 4.8)
   * Homework: propose **concrete changes**
4. Returns a **ChangeSet** that may include:

   * `config_patch`: tweak model, temperature, tool usage
   * `new_testcases`: new rows to add to golden CSV
   * `rationale`: explanation of why these changes help
   * `metadata`: context for the next iteration

> For the capstone, this is framed as:
> **“AgentSentinel helped improve travel_planner from v1 → travel_v2, increasing judge_score_avg and eliminating failing (<4) testcases.”**

### 6.3 How to run Planner once

From repo root:

```bash
python agentops/run_planner_once.py
```

This will:

* Load the AUTSpec (default: `travel_planner_v1.aut.yaml`)
* Construct `PlannerEngine(spec=spec)`
* Call `planner_engine.propose_changeset(version_id=base_version_id)`
* Pretty-print a JSON-like proposal:

```text
=== Planner Changeset Proposal ===
{
  "config_patch": { ... },
  "new_testcases": [ ... ],
  "rationale": "...",
  "metadata": { ... }
}

Next steps:
  1) Use this proposal to create a NEW version config (travel_planner_config_v2.json)
  2) Append new_testcases to golden CSV (travel_golden_v2.csv)
  3) Update AUT spec travel_planner_v2.aut.yaml
  4) Run eval again via Supervisor:
       Supervisor > eval travel_v2
```

---

## 7. Data & Traces

All evals and manual runs log to **JSONL** for easy analysis:

* **File:** `data/traces.jsonl`
* **Writer:** `infra/traces_store.log_trace(...)`

Each line is a dict with:

* `trace_id`, `timestamp`
* `aut_id`, `version_id`
* `input`, `output`
* `metrics` (e.g., judge_score, task_success)
* `latency_ms`
* `tool_calls` (normalized)
* `session_graph` (if any; currently `{}` for ADK app runs)

These are used by:

* `agentops/run_metrics_summary.py`
* Supervisor `metrics` / `compare`
* `PlannerEngine` to compute **current state vs targets**

> **Note:** `.gitignore` excludes `data/traces.jsonl` and `*.jsonl` so runtime artifacts will not pollute the repo.

---

## 8. How This Demonstrates AgentSentinel

For the capstone narrative, you can describe AgentSentinel as:

> **AgentSentinel is a framework-agnostic control plane for agentic apps.**
> It can:
>
> * **Discover** an ADK app and its schema
> * **Evaluate** it using rule + LLM-judge metrics
> * **Observe** it via structured traces
> * **Improve** it using a Planner/Critic loop guided by best practices
> * **Version** agents and compare performance over time.

This repo implements that vision concretely for:

* A **Travel Itinerary Planner** as the first AUT
* A **Gemini-based eval harness** with a rubric
* A **multi-version story**: v1, v2, v3, travel_v1, travel_v2
* A **planner loop** that can propose travel_v2 improvements from travel_v1 metrics

---

## 9. Limitations & Future Work

This is a **capstone-scale slice** of AgentSentinel, not a full production system. Potential extensions:

* Integrate **real observability backends** (e.g., OpenTelemetry exporters)
* Add **human-in-the-loop UI** for labels (`evaluation.human` block in AUTSpec)
* Multi-AUT support in a single deployment
* Rich **session_graph** visualization for ADK orchestration traces
* More EvalPacks (e.g., safety, hallucination, style, brand voice)
* Web UI for **AgentSentinel Supervisor** instead of CLI

---

## 10. Quick Commands Recap

```bash
# 0. Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="YOUR_KEY"

# 1. Supervisor CLI (AgentSentinel)
python scripts/run_supervisor.py
# inside:
#   > discover
#   > profile
#   > eval
#   > run
#   > metrics
#   > compare travel_v1 travel_v2
#   > exit

# 2. Travel eval helpers
python scripts/run_travel_v1_eval.py
python scripts/run_travel_v2_eval.py

# 3. Metrics summary from traces.jsonl
python agentops/run_metrics_summary.py

# 4. Planner / improvement loop
python agentops/run_planner_once.py
```
