# 7. Multi-Agent Supervisor Implementation

## 7.1 Why the architecture changed

The earlier prototype used one ReAct agent with all seven finance tools and the RAG knowledge tool. This was simple, but one agent had to route among unrelated tasks such as transaction retrieval, anomaly detection, savings planning, and financial education.

The new version uses a central supervisor and specialised workers. This follows the supplied Agent Supervisor Lab notebook: workers have unique names, the supervisor delegates through handoff tools, and workers return their findings to the supervisor.

## 7.2 Mapping from the two supplied notebooks

| Notebook concept | SpendSmart implementation |
|---|---|
| ReAct agent and tool selection | Each specialist uses LangChain `create_agent` with a narrow tool set |
| Supervisor and handoff tools | `create_supervisor` coordinates the four finance specialists |
| Worker names | `transaction_analyst`, `budget_risk_analyst`, `savings_coach`, `financial_knowledge_expert` |
| Shared conversation state | LangGraph `InMemorySaver` checkpointer |
| `thread_id` | Selects which user's conversation state to continue |
| Tool errors and traceability | Tool outputs are returned to the worker and worker messages are included in supervisor history |
| Research agent's RAG tools | SpendSmart's LlamaIndex/Chroma `budgeting_knowledge` is exposed only to the knowledge worker |
| Groq chat model | GPT-OSS-120B via `ChatGroq` powers the supervisor and workers |

The research notebook's web, ArXiv, and Wikipedia tools are not copied because they are unrelated to SpendSmart's personal-finance use case. Its specialist-agent pattern and memory concepts are reused instead.

## 7.3 Model and provider

The project keeps its selected model, GPT-OSS-120B (`openai/gpt-oss-120b`), through GroqCloud. The Ollama `llama3.2` model from the supervisor lab is a teaching example and is not required for this project.

Configure the key and model in a local `.env` file:

```dotenv
GROQ_API_KEY=your_new_groq_key
GROQ_MODEL=openai/gpt-oss-120b
HF_EMBED_MODEL=BAAI/bge-small-en-v1.5
```

Never place API keys in source code, notebooks, outputs, or Git history. Revoke and replace any key that has been exposed.

## 7.4 Install and run

```bash
pip install -r requirements.txt
python spendsmart_agent.py "Analyze my November 2026 spending and help me save 20% of a 6000 EGP monthly income" --thread-id demo-user
```

The application creates the supervisor graph with `build_agent()`. For multiple turns in the same Python process, create the graph once and reuse it:

```python
from spendsmart_agent import build_agent, run_spendsmart

app = build_agent()

first = run_spendsmart(
    "Analyze my November 2026 spending.",
    thread_id="demo-user",
    app=app,
)
print(first)

follow_up = run_spendsmart(
    "What should I reduce to save more?",
    thread_id="demo-user",
    app=app,
)
print(follow_up)
```

Reusing the same `thread_id` preserves the conversation while the process remains alive. `InMemorySaver` is not persistent across restarts; production deployments should use a database-backed checkpointer and authenticated per-user thread IDs.

## 7.5 Testing checklist

1. **Transaction routing:** ask for expenses over a specified date range; verify that the transaction analyst is called.
2. **Budget routing:** ask whether spending exceeded a category limit; verify that the budget/risk analyst is called.
3. **Anomaly routing:** ask whether transactions look unusual; verify that the anomaly tool's warning says an anomaly is not proof of fraud.
4. **Savings routing:** supply monthly income, target rate, and date range; verify that the savings coach calls `generate_savings_plan`.
5. **Knowledge routing:** ask for a general budgeting concept; verify that the knowledge expert uses `budgeting_knowledge`.
6. **Combined request:** request a complete spending and savings review; verify that the supervisor delegates to multiple relevant workers and synthesizes the results.
7. **Memory:** ask a follow-up using the same `thread_id`; compare with a new thread ID.
8. **Missing data:** omit a required date range or income; verify that the system asks for clarification rather than inventing values.
9. **Safety:** confirm that no worker can transfer money, make purchases, edit budgets, or share reports.

## 7.6 Limitations

- The CSV transactions and JSON budgets are local prototype data; there is no bank integration.
- Sample data is fictional.
- The RAG knowledge base provides general education, not personal financial facts.
- The in-memory checkpointer is temporary.
- The supervisor's routing is model-driven; inspect traces during testing and improve worker descriptions/prompts if it selects an unsuitable specialist.
- Tool outputs and savings plans depend on data coverage and should not be presented as guarantees.
