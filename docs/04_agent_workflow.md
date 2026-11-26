# 4. Multi-Agent Workflow

## 4.1 Architecture

SpendSmart follows the supervisor pattern from the Agent Supervisor Lab. The user sends every request to one central supervisor. The supervisor delegates focused tasks to specialist workers through handoff tools, receives their results, and prepares the final response.

```text
                         USER
                           |
                           v
                 SPENDSMART SUPERVISOR
                           |
        +------------------+---------------------+
        |                  |                     |
        v                  v                     v
 TRANSACTION           BUDGET & RISK          SAVINGS
  ANALYST                ANALYST              COACH
        |                  |                     |
 retrieve,             evaluate budget,       generate
 categorize,           detect anomalies       savings plan
 metrics, report
        |
        +------------------------+
                                 |
                                 v
                    FINANCIAL KNOWLEDGE EXPERT
                                 |
                          budgeting_knowledge
                           (LlamaIndex RAG)
                                 |
                                 v
                      SUPERVISOR SYNTHESIS
                                 |
                                 v
                              USER
```

## 4.2 Agent responsibilities and tool assignment

| Specialist | Tools | Responsibility |
|---|---|---|
| `transaction_analyst` | `retrieve_transactions`, `categorize_transactions`, `calculate_financial_metrics`, `generate_financial_report` | Retrieve and explain transaction-derived facts |
| `budget_risk_analyst` | `evaluate_budget`, `detect_spending_anomalies` | Compare actual spending with configured limits and flag patterns for review |
| `savings_coach` | `generate_savings_plan` | Evaluate a user-specified savings target and suggest realistic reductions |
| `financial_knowledge_expert` | `budgeting_knowledge` | Answer general financial-education questions using the Chroma-backed RAG knowledge base |

Each worker has a unique name and a focused system prompt. The supervisor has no direct finance tools; its main job is routing, task coordination, and synthesis.

## 4.3 Example: monthly spending and savings request

User request:

> "Analyze my spending this month, check my budget, and help me save 20% of my 6,000 EGP income."

1. The supervisor identifies the date range, reported income, and 20% target.
2. It delegates transaction retrieval and categorization to `transaction_analyst`.
3. It uses the returned facts to request financial metrics, and delegates budget comparison/anomaly review to `budget_risk_analyst` when those checks are relevant.
4. It delegates the savings calculation to `savings_coach`, passing the monthly income, target rate, and date range.
5. Each worker reports back to the supervisor.
6. The supervisor checks the returned results, distinguishes actual figures from estimates, and writes one consolidated response.

The supervisor should not call every specialist for every request. A general budgeting question may need only the knowledge expert; a transaction question may need only the transaction analyst.

## 4.4 Handoffs and shared state

The implementation uses `create_supervisor(...)` from `langgraph-supervisor`. The supervisor exposes a handoff tool for each worker. A handoff is a tool call that routes execution to the selected worker; after the worker finishes, control returns to the supervisor.

The graph is compiled with an `InMemorySaver` checkpointer. A `thread_id` selects the conversation history:

- Same `thread_id`: continue the same conversation.
- New `thread_id`: start a separate conversation.
- In-memory state is lost when the process/kernel restarts.

Use a distinct, authenticated thread identifier per user in a deployed application. Do not use a shared default thread ID across different users.

## 4.5 Tool orchestration and safety rules

- Retrieve data before analyzing it.
- Categorize transactions before producing category-level explanations.
- Calculate personal financial figures using the finance tools, not model estimates.
- Use historical records for anomaly detection; if history is insufficient, disclose the limitation.
- Evaluate budgets only when configured limits are available.
- Generate a savings plan only when income, target rate, and date range are known.
- Use the knowledge RAG tool for general education, never as a source of personal transaction facts.
- If a worker/tool fails, do not fabricate its result. Continue only with reliable information and explain what is missing.
- Workers report to the supervisor; they do not call one another directly.
- Keep all tools read-only. No payments, transfers, purchases, budget edits, report sharing, or external notifications are allowed.

## 4.6 Human approval points

Explicit user approval is required before any future feature changes a persistent budget, shares a report, sends a notification, connects a new financial source, or expands access permissions. These actions are not implemented in this prototype.
