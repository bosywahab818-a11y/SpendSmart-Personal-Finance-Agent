# SpendSmart – Multi-Agent Personal Finance Assistant

**A supervisor-based AI assistant for expense analysis, budget monitoring, anomaly review, financial education, and savings recommendations.**

SpendSmart uses GPT-OSS-120B through GroqCloud. A central supervisor delegates requests to focused finance specialists, each equipped with only the tools needed for its responsibility.

> **Prototype boundary:** SpendSmart analyzes a local CSV export and local JSON budget file. It does not connect to a bank, move money, execute payments, make purchases, or modify persistent budgets.

## Multi-agent architecture

```text
                         USER
                           |
                           v
                 SPENDSMART SUPERVISOR
                 (GPT-OSS-120B / Groq)
                           |
          +----------------+-------------------+
          |                |                   |
          v                v                   v
   TRANSACTION        BUDGET & RISK        SAVINGS COACH
    ANALYST             ANALYST
          |                |                   |
   - retrieve         - evaluate          - generate
     transactions       budget              savings plan
   - categorize      - detect anomalies
   - financial
     metrics
   - financial
     report
          |
          +-------------------+
                              |
                              v
                   FINANCIAL KNOWLEDGE EXPERT
                              |
                       - budgeting_knowledge
                         (LlamaIndex RAG
                          + Chroma)
                              |
                              v
                  SUPERVISOR SYNTHESIS
                              |
                              v
                       USER RESPONSE
```

The supervisor decides which specialist to call, gives it a focused task, receives its result, and combines the findings. Workers report back to the supervisor; they do not call one another directly.

## Specialists and tools

| Agent | Responsibilities | Tools |
|---|---|---|
| `transaction_analyst` | Transaction history, categorization, totals, financial reports | `retrieve_transactions`, `categorize_transactions`, `calculate_financial_metrics`, `generate_financial_report` |
| `budget_risk_analyst` | Budget comparison and unusual-spending review | `evaluate_budget`, `detect_spending_anomalies` |
| `savings_coach` | Savings target evaluation and practical savings suggestions | `generate_savings_plan` |
| `financial_knowledge_expert` | General financial education and budgeting guidance | `budgeting_knowledge` (LlamaIndex RAG / Chroma) |

The seven existing finance functions are reused; the architecture change is in orchestration, not a rewrite of the underlying calculations.

## Technology stack

- **LLM:** OpenAI GPT-OSS-120B via GroqCloud (`openai/gpt-oss-120b`).
- **Multi-agent orchestration:** LangChain `create_agent` + `langgraph-supervisor`.
- **Conversation state:** LangGraph `InMemorySaver` checkpointer keyed by `thread_id`.
- **Finance data:** pandas, local CSV transactions, and read-only JSON budgets.
- **Financial knowledge:** LlamaIndex query engine, Hugging Face embeddings, and Chroma vector store.

## Repository structure

```text
SpendSmart-Personal-Finance-Agent/
├── spendsmart_agent.py          # Finance tools, RAG, supervisor and workers
├── requirements.txt
├── .env.example
├── data/
│   ├── transactions.csv         # Fictional sample data
│   └── budgets.json             # Example category limits
├── knowledge/
│   └── financial_guidance.md
└── docs/
    ├── 01_brainstorming_and_use_case.md
    ├── 02_llm_and_provider.md
    ├── 03_tool_specifications.md
    ├── 04_agent_workflow.md
    ├── 05_system_prompt.md
    ├── 06_llamaindex_implementation.md
    └── 07_multi_agent_implementation.md
```

## Setup

Use Python 3.10 or newer.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local `.env` file from `.env.example` and add a **new** Groq API key:

```dotenv
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
HF_EMBED_MODEL=BAAI/bge-small-en-v1.5
```

Never commit `.env`, API keys, or notebook secrets. The RAG embedding model is downloaded when the knowledge index is first initialized.

## Run

```bash
python spendsmart_agent.py "Analyze my November 2026 spending, check my budget, and help me save 20% of a 6000 EGP monthly income" --thread-id user-session-1
```

For a multi-turn session, reuse the same `--thread-id`. Use a different thread ID for each user/conversation. The command-line entry point creates the supervisor once for the run; applications that need multiple turns in one process should build the app once and call `run_spendsmart(query, thread_id, app)` repeatedly.

## Example routing

- "Show my expenses last month" → transaction analyst.
- "Did I exceed my food budget?" → budget and risk analyst.
- "Was anything unusual in November?" → budget and risk analyst.
- "Help me save 20% of my 6,000 EGP income" → savings coach, with transaction analysis when needed.
- "Explain the 50/30/20 budgeting rule" → financial knowledge expert.
- "Give me a complete monthly review" → supervisor coordinates the relevant specialists and synthesizes their findings.

## Design and safety principles

- **Read-only by default:** local transaction and budget files are not modified.
- **Privacy:** never request passwords, PINs, OTPs, recovery codes, or full payment-card security details.
- **Honest analysis:** calculations and personal-data claims must come from finance tools; never invent records or balances.
- **Anomaly caution:** an anomaly is a signal for user review, not proof of fraud.
- **Human approval:** future budget changes, report sharing, notifications, or new data-source permissions require explicit approval.
- **Currency and period awareness:** do not combine currencies or present partial-period data as a complete month.
- **Practical recommendations:** protect essential expenses and label savings projections as estimates, not guarantees.

## Limitations

- Sample transactions and budget limits are fictional.
- The current data source is a local CSV, not a live bank connection.
- `InMemorySaver` stores conversation history in RAM and loses it when the process/kernel restarts. A persistent database checkpointer is needed for production.
- The sample is a prototype, not professional investment, tax, legal, or banking advice.
