# 6. LlamaIndex Implementation

This implementation adapts the supplied `02_llamaindex_agents` notebook to SpendSmart. It uses the same LlamaIndex building blocks and integration style, while replacing the notebook's household/dinner-party example with personal-finance analysis.

## 6.1 Mapping from the course notebook

| Notebook section | SpendSmart adaptation |
|---|---|
| Hugging Face Inference API | `HuggingFaceInferenceAPI` initializes the LLM using `HF_TOKEN` and a configurable model name |
| RAG loading and indexing | `SimpleDirectoryReader` loads Markdown files from `knowledge/` |
| Embeddings | `HuggingFaceEmbedding` creates document embeddings |
| Chroma storage | `ChromaVectorStore` stores the knowledge vectors locally |
| Query engine | LlamaIndex query engine retrieves relevant budgeting guidance |
| QueryEngineTool | `budgeting_knowledge` exposes RAG retrieval to the agent |
| FunctionTool | Seven finance functions are wrapped as LlamaIndex tools |
| ReActAgent | The agent reasons and selects tools using a ReAct loop |

The supplied notebook explains that its Hugging Face inference integration is not configured as a function-calling model by default, so the implementation uses `ReActAgent` rather than assuming native function calling.

## 6.2 Architecture

```text
User question
     |
     v
LlamaIndex ReActAgent
     |
     +---- Finance FunctionTools
     |       +-- retrieve_transactions
     |       +-- categorize_transactions
     |       +-- calculate_financial_metrics
     |       +-- detect_spending_anomalies
     |       +-- evaluate_budget
     |       +-- generate_savings_plan
     |       +-- generate_financial_report
     |
     +---- QueryEngineTool
             +-- budgeting_knowledge
                    |
                    v
              Chroma vector store
                    |
                    v
          financial_guidance.md

Tool results -> ReAct reasoning -> final response
```

## 6.3 Requirements

Use Python 3.10 or newer. Create and activate a virtual environment, then install:

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

Install the project packages:

```bash
pip install -r requirements.txt
```

## 6.4 Hugging Face token configuration

1. Create or use a Hugging Face access token with the permissions needed to access the selected Inference Provider.
2. Copy `.env.example` to a local file named `.env`.
3. Replace the placeholder with your token.
4. Keep `.env` private. It is excluded by `.gitignore`.

Example:

```dotenv
HF_TOKEN=your_new_token_here
HF_LLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct
HF_EMBED_MODEL=BAAI/bge-small-en-v1.5
```

The course notebook contained a token directly in a code cell. Do not reuse or publish that value. If it was a real token, revoke it and create a replacement.

The default LLM name follows the supplied notebook. Hugging Face model/provider availability can change. If the default is not served for your account, set `HF_LLM_MODEL` to a model currently listed as available through Hugging Face Inference Providers.

## 6.5 Run the agent

From the repository root:

```bash
python spendsmart_agent.py "Analyze my November 2026 spending and help me save 20% of a 6000 EGP monthly income"
```

If no question is provided, the script runs a sample analysis prompt.

## 6.6 Finance tools

The seven finance tools are ordinary typed Python functions. The implementation passes them to `FunctionTool.from_defaults`, allowing LlamaIndex to use their names, type hints, and docstrings as tool metadata and argument schemas.

| Function | Implementation |
|---|---|
| `retrieve_transactions` | Reads local CSV records for a date range |
| `categorize_transactions` | Applies transparent merchant/description keyword rules |
| `calculate_financial_metrics` | Computes income, expenses, balance, savings rate, and category totals |
| `detect_spending_anomalies` | Flags possible duplicates and unusually large expenses against available history |
| `evaluate_budget` | Compares category expenses with the example JSON budget |
| `generate_savings_plan` | Estimates a savings target and illustrative optional-spending reductions |
| `generate_financial_report` | Combines metrics, budget, anomaly, and categorization results |

The tools read local sample/export data. The implementation does not contain a bank API integration.

## 6.7 RAG knowledge tool

The implementation loads Markdown documents from `knowledge/`, creates embeddings with `HuggingFaceEmbedding`, stores them in a persistent Chroma collection, and exposes the query engine through `QueryEngineTool`.

The RAG collection contains general budgeting guidance. It is deliberately separate from personal transaction facts: transaction totals must come from the CSV analysis tools, not from retrieved educational documents.

The first run may take longer because the embedding model must be downloaded and the knowledge collection must be created. The local Chroma directory is ignored by Git.

## 6.8 Example data and expected analysis

The sample CSV is fictional and includes November 2026 transactions, plus earlier records for historical comparison. The JSON file contains example category budgets.

For November 1–18, 2026, the sample transaction file contains:
- Transaction-derived income: 6,000 EGP.
- Expenses: 3,915 EGP.
- Remaining transaction balance: 2,085 EGP.
- A 20% target based on 6,000 EGP monthly income: 1,200 EGP.

These figures describe only the supplied sample records and date coverage. They are not real account data or a complete month-end statement.

## 6.9 Safety and limitations

- The CSV is a local file; no real bank connection is implemented.
- The sample records and budgets are fictional.
- The budget JSON is read-only from the agent's perspective.
- No transfer, payment, purchase, or account-changing tool exists.
- The anomaly detector provides review signals, not fraud determinations.
- The savings plan is illustrative and depends on the quality and coverage of the supplied data.
- Never place an access token in source code, notebook output, Git history, or a public repository.
