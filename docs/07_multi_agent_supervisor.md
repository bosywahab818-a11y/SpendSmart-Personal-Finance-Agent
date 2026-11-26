# 7. Multi-Agent Supervisor Implementation

## 7.1 Why move from one agent to multiple agents?

The original implementation gives one ReAct agent all finance tools and the budgeting knowledge tool. As the project grows, the agent must decide among unrelated responsibilities in one tool list.

The multi-agent version separates responsibilities into workers with focused prompts and smaller tool sets. A supervisor owns routing and final response synthesis. Workers do not call one another directly; they return findings to the supervisor.

## 7.2 Architecture

```text
                         USER
                           |
                           v
                 SpendSmart Supervisor
                           |
       +-------------------+-------------------+
       |          |        |        |           |
       v          v        v        v           v
  Transaction  Financial  Budget  Savings   Financial
    Agent      Analysis   Agent   Agent     Education
                 Agent                      Agent
       |          |        |        |           |
       +----------+--------+--------+-----------+
                           |
                           v
                 Supervisor response
```

## 7.3 Worker-to-tool mapping

| Worker | Tools | Responsibility |
|---|---|---|
| `transaction_expert` | `retrieve_transactions`, `categorize_transactions` | Retrieve and categorize local CSV records |
| `analysis_expert` | `calculate_financial_metrics`, `detect_spending_anomalies` | Calculate metrics and flag unusual activity |
| `budget_expert` | `evaluate_budget` | Compare expenses with read-only configured limits |
| `savings_expert` | `generate_savings_plan` | Estimate savings target and possible reductions |
| `financial_education_expert` | `search_budgeting_knowledge` | Retrieve general guidance from Chroma |

The deterministic finance functions remain in `spendsmart_agent.py`; `spendsmart_multi_agent.py` imports and reuses them. This avoids duplicating the financial calculation logic.

## 7.4 Supervisor and handoffs

Each worker is created with LangChain's `create_agent()` and a unique name. The supervisor is created with `create_supervisor()`. The library creates a handoff tool for each worker. The supervisor LLM selects a handoff tool when it needs that specialist.

The supervisor prompt describes each specialist's domain, dependencies and safety boundaries. It instructs the supervisor to delegate one task at a time, wait for the worker's result, and synthesize only verified findings.

`include_agent_name="inline"` makes worker authors visible in the shared trace. `output_mode="last_message"` returns the supervisor final response as the user-facing output, keeping the response concise.

## 7.5 Memory

The compiled graph uses `InMemorySaver()`. Each invocation supplies a `thread_id` in the configurable section:

```python
config = {"configurable": {"thread_id": "user-session-1"}}
result = app.invoke({"messages": [{"role": "user", "content": query}]}, config)
```

Reuse the same ID in the same running Python process to continue a conversation. Use a different ID for an independent conversation. This memory is volatile and is cleared when the process exits. A deployed service should use a persistent database checkpointer and enforce user-level access isolation.

## 7.6 Run

Install the dependencies and configure a new Groq API key in a local `.env` file:

```powershell
python -m pip install -r requirements.txt
python spendsmart_multi_agent.py "Analyze my spending from 2026-11-01 to 2026-11-18 and check my budget"
```

To use memory across turns in one Python process:

```python
from spendsmart_multi_agent import run_spendsmart

run_spendsmart("Analyze my spending from 2026-11-01 to 2026-11-18.", thread_id="demo")
run_spendsmart("Which category was highest?", thread_id="demo")
```

The CLI starts a new process for each command, so its in-memory state does not persist between separate CLI executions.

## 7.7 Suggested test sequence

1. Build the workers and confirm the five unique worker names.
2. Test the transaction worker with a date-bounded retrieval request.
3. Test the analysis worker with a metrics request and a period covered by the CSV.
4. Test the budget worker with a period and the configured budget.
5. Test the savings worker with a positive income and a target rate between 0 and 1.
6. Test the education worker with a general budgeting question.
7. Run the supervisor with a request that requires two or more specialists.
8. Reuse a thread ID for a follow-up and verify that the conversation context is available.
9. Inspect the graph trace and confirm that workers report back to the supervisor.

## 7.8 Safety and limitations

- The transaction CSV is the only personal transaction source in this prototype.
- The budget JSON is read-only.
- The Chroma knowledge base is general education, not personal financial evidence.
- Anomaly flags are not fraud determinations.
- Savings recommendations are illustrative, not guaranteed.
- No bank API, transfer, payment, purchase or budget-editing tool is provided.
- Do not put API keys in source files, notebooks or Git history. If a key was committed, revoke it and issue a replacement.
