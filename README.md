# SpendSmart – Personal Finance Multi-Agent Assistant

**A multi-agent personal finance assistant for expense tracking, budget monitoring, anomaly detection, financial education, and savings recommendations.**

SpendSmart uses a **LangGraph supervisor architecture**. A central supervisor routes each request to specialized finance agents, then combines their verified results into one response.

> **Project scope:** This is a local-data prototype. It reads an authorized CSV export and a read-only JSON budget. It does not connect to a bank, move money, execute payments, make purchases, or modify budgets.

## Multi-agent architecture

```text
                         USER
                           |
                           v
                 SpendSmart Supervisor
                  (intent + routing)
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
                 Supervisor synthesizes
                    verified findings
                           |
                           v
                     USER RESPONSE
```

### Specialist responsibilities

| Agent | Tools / responsibilities |
|---|---|
| Transaction Agent | `retrieve_transactions`, `categorize_transactions` |
| Financial Analysis Agent | `calculate_financial_metrics`, `detect_spending_anomalies` |
| Budget Agent | `evaluate_budget` |
| Savings Agent | `generate_savings_plan` |
| Financial Education Agent | Chroma-backed `search_budgeting_knowledge` |
| Supervisor | Routes work, checks findings, and writes the final response |

The original deterministic finance functions remain in `spendsmart_agent.py`. The multi-agent orchestration is implemented in `spendsmart_multi_agent.py`.

## Course notebook concepts applied

| Course concept | SpendSmart implementation |
|---|---|
| LangGraph `create_agent()` | Creates each specialist worker |
| `create_supervisor()` | Creates the central coordinator and handoff tools |
| `include_agent_name="inline"` | Makes worker messages visible in the shared trace |
| `output_mode="last_message"` | Returns the supervisor final response as the user-facing output |
| `InMemorySaver()` + `thread_id` | Keeps conversation state between turns in the same running process |
| Groq Chat model | Uses GPT-OSS-120B through Groq for LangGraph agents |
| Existing Chroma RAG | Supplies general budgeting education to the education specialist |

## Repository structure

```text
SpendSmart-Personal-Finance-Agent/
├── spendsmart_agent.py           # Existing finance functions and Chroma RAG builder
├── spendsmart_multi_agent.py     # LangGraph workers + supervisor
├── requirements.txt
├── .env.example
├── data/
│   ├── transactions.csv          # Fictional sample transactions
│   └── budgets.json              # Example category limits
├── knowledge/
│   └── financial_guidance.md     # General budgeting knowledge
└── docs/
```

## Setup

Use Python 3.10 or newer.

1. Create and activate a virtual environment.

   **Windows PowerShell**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and add a newly generated Groq API key. Never commit `.env`.

4. Run a request:

   ```powershell
   python spendsmart_multi_agent.py "Analyze my spending from 2026-11-01 to 2026-11-18 and check my budget"
   ```

Example savings request:

```powershell
python spendsmart_multi_agent.py "I earn 6000 EGP monthly and want to save 20%. Analyze my spending from 2026-11-01 to 2026-11-18."
```

## Conversation memory

The graph is compiled with LangGraph's `InMemorySaver`. Reuse the same `thread_id` when calling `run_spendsmart` in a long-running Python process to continue a conversation:

```python
from spendsmart_multi_agent import run_spendsmart

print(run_spendsmart(
    "Analyze my spending from 2026-11-01 to 2026-11-18.",
    thread_id="user-session-1",
))
print(run_spendsmart(
    "Which category used the most money?",
    thread_id="user-session-1",
))
```

A different thread ID starts a separate conversation. In-memory history is lost when the Python process restarts; use a persistent database checkpointer for a deployed application. Passing a thread ID to two separate one-shot CLI processes does not persist memory between those processes.

## Testing the specialists

Build and test the workers independently before testing the supervisor:

```python
from spendsmart_multi_agent import build_agents, get_llm

workers = build_agents(get_llm())
for worker in workers:
    print(worker.name)
```

Then build the supervisor and inspect its graph:

```python
from spendsmart_multi_agent import build_supervisor

app = build_supervisor()
print(app.get_graph().draw_mermaid())
```

## Safety and limitations

- All personal transaction facts come from the local CSV export.
- The budget JSON and source CSV are read-only to the agents.
- Sample transactions and budget limits are fictional.
- Anomaly detection flags items for review; it does not prove fraud.
- Savings plans are estimates, not guarantees.
- No bank connection, payment, transfer, purchase, or budget-editing capability is included.
- Never request passwords, PINs, OTPs, or card security codes.
