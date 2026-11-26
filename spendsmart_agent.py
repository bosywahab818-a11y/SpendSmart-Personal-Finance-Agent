"""SpendSmart: a documentation-friendly LlamaIndex personal finance agent.

This prototype analyzes a local CSV export only. It does not connect to a bank,
move money, execute payments, or change persistent budgets.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
TRANSACTIONS_PATH = Path(os.getenv("TRANSACTIONS_PATH", ROOT / "data/transactions.csv"))
BUDGETS_PATH = Path(os.getenv("BUDGETS_PATH", ROOT / "data/budgets.json"))
KNOWLEDGE_PATH = ROOT / "knowledge"
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", ROOT / ".chroma"))
LLM_MODEL = os.getenv("HF_LLM_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct")
EMBED_MODEL = os.getenv("HF_EMBED_MODEL", "BAAI/bge-small-en-v1.5")

CATEGORY_RULES = {
    "food": ("cafe", "restaurant", "supermarket", "grocery", "food"),
    "transportation": ("metro", "ride", "uber", "taxi", "bus", "transport"),
    "education": ("university", "bookstore", "course", "tuition", "education"),
    "shopping": ("clothing", "store", "shop", "mall"),
    "subscriptions": ("streaming", "subscription", "membership"),
    "healthcare": ("pharmacy", "clinic", "hospital", "medical"),
}


def _load_transactions() -> pd.DataFrame:
    """Load the local sample/export file and validate its required columns."""
    if not TRANSACTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Transactions file not found: {TRANSACTIONS_PATH}. "
            "Provide an authorized CSV export using the sample column format."
        )
    df = pd.read_csv(TRANSACTIONS_PATH)
    required = {
        "transaction_id", "date", "merchant", "amount",
        "description", "transaction_type", "currency",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["date", "amount"]).copy()
    df["transaction_type"] = df["transaction_type"].astype(str).str.lower()
    return df


def _period(start_date: str, end_date: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    start, end = pd.Timestamp(start_date), pd.Timestamp(end_date)
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    return start, end


def _filter_period(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    start, end = _period(start_date, end_date)
    return df[(df["date"] >= start) & (df["date"] <= end)].copy()


def _category(merchant: str, description: str) -> str:
    text = f"{merchant} {description}".lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(word in text for word in keywords):
            return category
    return "other"


def retrieve_transactions(
    start_date: str,
    end_date: str,
    transaction_type: str = "all",
) -> str:
    """Retrieve authorized local CSV transactions between ISO dates (YYYY-MM-DD).

    transaction_type must be all, income, or expense. Returns transaction records
    as JSON; this tool reads data and never modifies the source file.
    """
    df = _filter_period(_load_transactions(), start_date, end_date)
    if transaction_type not in {"all", "income", "expense"}:
        return json.dumps({"error": "transaction_type must be all, income, or expense"})
    if transaction_type != "all":
        df = df[df["transaction_type"] == transaction_type]
    records = df.copy()
    records["date"] = records["date"].dt.strftime("%Y-%m-%d")
    return json.dumps(
        {"count": len(records), "transactions": records.to_dict(orient="records")},
        ensure_ascii=False,
        default=str,
    )


def categorize_transactions(start_date: str, end_date: str) -> str:
    """Categorize each transaction in the selected date range using transparent merchant rules."""
    df = _filter_period(_load_transactions(), start_date, end_date)
    df["category"] = df.apply(
        lambda row: _category(str(row["merchant"]), str(row["description"])), axis=1
    )
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return json.dumps(
        {"count": len(df), "categorized_transactions": df.to_dict(orient="records")},
        ensure_ascii=False,
        default=str,
    )


def calculate_financial_metrics(
    start_date: str,
    end_date: str,
    reported_monthly_income: float | None = None,
) -> str:
    """Calculate income, expenses, balance, savings rate, and category totals for ISO dates."""
    df = _filter_period(_load_transactions(), start_date, end_date)
    income = float(df.loc[df.transaction_type == "income", "amount"].sum())
    expenses_df = df[df.transaction_type == "expense"].copy()
    expenses = float(expenses_df["amount"].sum())
    balance = income - expenses
    savings_rate = (balance / income) if income > 0 else None
    expenses_df["category"] = expenses_df.apply(
        lambda row: _category(str(row["merchant"]), str(row["description"])), axis=1
    )
    category_totals = expenses_df.groupby("category")["amount"].sum().to_dict()
    result: dict[str, Any] = {
        "period": {"start_date": start_date, "end_date": end_date},
        "currency": sorted(df.currency.dropna().astype(str).unique().tolist()),
        "transaction_income_total": round(income, 2),
        "total_expenses": round(expenses, 2),
        "remaining_balance": round(balance, 2),
        "savings_rate": round(savings_rate, 4) if savings_rate is not None else None,
        "category_totals": {k: round(float(v), 2) for k, v in category_totals.items()},
        "transaction_count": int(len(df)),
    }
    if reported_monthly_income is not None:
        result["user_reported_monthly_income"] = float(reported_monthly_income)
        result["income_note"] = "Reported income is shown separately from transaction-derived income."
    return json.dumps(result, ensure_ascii=False)


def detect_spending_anomalies(start_date: str, end_date: str) -> str:
    """Flag possible duplicate or unusually large expenses; flags are not fraud determinations."""
    df = _load_transactions()
    current = _filter_period(df, start_date, end_date)
    expenses = current[current.transaction_type == "expense"].copy()
    anomalies: list[dict[str, Any]] = []

    duplicates = expenses.duplicated(
        subset=["date", "merchant", "amount"], keep=False
    )
    for _, row in expenses[duplicates].iterrows():
        anomalies.append({
            "transaction_id": row.transaction_id,
            "type": "possible_duplicate",
            "reason": "Same date, merchant, and amount appear more than once.",
            "requires_user_review": True,
        })

    history_start = pd.Timestamp(start_date) - pd.Timedelta(days=90)
    history = df[
        (df.date >= history_start)
        & (df.date < pd.Timestamp(start_date))
        & (df.transaction_type == "expense")
    ].copy()
    if not history.empty:
        history["category"] = history.apply(
            lambda row: _category(str(row.merchant), str(row.description)), axis=1
        )
        baseline = history.groupby("category").amount.mean().to_dict()
        for _, row in expenses.iterrows():
            cat = _category(str(row.merchant), str(row.description))
            avg = float(baseline.get(cat, 0))
            if avg > 0 and float(row.amount) >= 2.5 * avg:
                anomalies.append({
                    "transaction_id": row.transaction_id,
                    "type": "unusually_large_for_category",
                    "category": cat,
                    "amount": float(row.amount),
                    "historical_category_average": round(avg, 2),
                    "reason": "Amount is at least 2.5 times the historical category average.",
                    "requires_user_review": True,
                })
    return json.dumps({
        "anomalies": anomalies,
        "note": "An anomaly is a review signal, not proof of fraud.",
        "historical_window_days": 90,
    }, ensure_ascii=False)


def evaluate_budget(start_date: str, end_date: str) -> str:
    """Compare expenses in the selected dates with configured monthly category limits."""
    if not BUDGETS_PATH.exists():
        return json.dumps({"status": "budget_not_configured"})
    budget = json.loads(BUDGETS_PATH.read_text(encoding="utf-8"))
    df = _filter_period(_load_transactions(), start_date, end_date)
    expenses = df[df.transaction_type == "expense"].copy()
    expenses["category"] = expenses.apply(
        lambda row: _category(str(row.merchant), str(row.description)), axis=1
    )
    actual = expenses.groupby("category").amount.sum().to_dict()
    limits = budget.get("monthly_limits", {})
    results = {}
    exceeded = []
    for category, limit in limits.items():
        spent = float(actual.get(category, 0))
        limit = float(limit)
        results[category] = {
            "spent": round(spent, 2),
            "limit": round(limit, 2),
            "remaining": round(limit - spent, 2),
            "utilization_rate": round(spent / limit, 4) if limit > 0 else None,
        }
        if spent > limit:
            exceeded.append(category)
    return json.dumps({
        "currency": budget.get("currency", "unspecified"),
        "category_results": results,
        "exceeded_categories": exceeded,
        "status": "over_budget" if exceeded else "within_configured_limits",
        "note": "Configured limits are examples and should be confirmed by the user.",
    }, ensure_ascii=False)


def generate_savings_plan(
    monthly_income: float,
    target_savings_rate: float,
    start_date: str,
    end_date: str,
) -> str:
    """Suggest a savings plan using observed expenses and a target rate between 0 and 1."""
    if monthly_income <= 0 or not 0 <= target_savings_rate <= 1:
        return json.dumps({"error": "income must be positive and savings rate must be between 0 and 1"})
    metrics = json.loads(calculate_financial_metrics(start_date, end_date))
    target = monthly_income * target_savings_rate
    category_totals = metrics["category_totals"]
    discretionary = {"shopping", "food", "subscriptions", "other"}
    opportunities = []
    for category, amount in category_totals.items():
        if category in discretionary and amount > 0:
            reduction = round(float(amount) * 0.10, 2)
            opportunities.append({
                "category": category,
                "current_spending": amount,
                "illustrative_reduction": reduction,
                "rationale": "Review optional purchases and recurring costs; confirm essentials before reducing.",
            })
    possible_reduction = sum(x["illustrative_reduction"] for x in opportunities)
    current_balance = float(metrics["remaining_balance"])
    return json.dumps({
        "monthly_income_assumption": monthly_income,
        "target_savings_rate": target_savings_rate,
        "target_monthly_savings": round(target, 2),
        "observed_period_balance": round(current_balance, 2),
        "illustrative_reduction_opportunities": opportunities,
        "illustrative_reduction_total": round(possible_reduction, 2),
        "goal_feasibility": "review_required" if current_balance < target else "appears_reachable_from_observed_period",
        "caveat": "This is an estimate from the supplied transaction file, not a guarantee. Confirm period coverage and essential expenses.",
    }, ensure_ascii=False)


def generate_financial_report(start_date: str, end_date: str) -> str:
    """Create a concise consolidated JSON report for a selected period."""
    return json.dumps({
        "period": {"start_date": start_date, "end_date": end_date},
        "metrics": json.loads(calculate_financial_metrics(start_date, end_date)),
        "budget": json.loads(evaluate_budget(start_date, end_date)),
        "anomalies": json.loads(detect_spending_anomalies(start_date, end_date)),
        "categorized_transactions": json.loads(categorize_transactions(start_date, end_date)),
    }, ensure_ascii=False)


def build_knowledge_tool(llm):
    """Build a Chroma-backed LlamaIndex RAG tool exposed to LangChain."""
    import chromadb
    from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore
    from langchain_core.tools import Tool

    if not KNOWLEDGE_PATH.exists() or not list(KNOWLEDGE_PATH.glob("*.md")):
        raise FileNotFoundError("Add at least one .md file to the knowledge/ directory.")

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection("spendsmart_knowledge")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)

    if collection.count() == 0:
        docs = SimpleDirectoryReader(input_dir=str(KNOWLEDGE_PATH)).load_data()
        index = VectorStoreIndex.from_documents(
            docs, vector_store=vector_store, embed_model=embed_model
        )
    else:
        index = VectorStoreIndex.from_vector_store(
            vector_store, embed_model=embed_model
        )

    query_engine = index.as_query_engine(llm=llm, similarity_top_k=3)

    def search_budgeting_knowledge(query: str) -> str:
        """Retrieve general budgeting and savings education from the local knowledge base."""
        return str(query_engine.query(query))

    return Tool(
        name="budgeting_knowledge",
        func=search_budgeting_knowledge,
        description=(
            "Search general budgeting, savings, and personal-finance education. "
            "Use for general guidance, never as a source of the user's transaction facts."
        ),
    )


def build_agent():
    """Build the SpendSmart supervisor and its specialised finance workers."""
    from langchain.agents import create_agent
    from langchain_groq import ChatGroq
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph_supervisor import create_supervisor
    from llama_index.llms.groq import Groq

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise EnvironmentError("Set GROQ_API_KEY in your .env file first.")

    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    model = ChatGroq(
        model=model_name,
        api_key=groq_api_key,
        temperature=0,
    )

    # LlamaIndex remains responsible for the RAG query engine; LangChain
    # exposes that query engine as a tool to the knowledge specialist.
    rag_llm = Groq(
        model=model_name,
        api_key=groq_api_key,
        temperature=0.1,
    )
    knowledge_tool = build_knowledge_tool(rag_llm)

    transaction_agent = create_agent(
        model,
        tools=[
            retrieve_transactions,
            categorize_transactions,
            calculate_financial_metrics,
            generate_financial_report,
        ],
        name="transaction_analyst",
        system_prompt=(
            "You are SpendSmart's transaction analyst. Handle requests about "
            "transaction history, categorization, income, expenses, balances, "
            "savings rates, and consolidated financial reports. Use the supplied "
            "finance tools for every personal-data claim and calculation. "
            "Use ISO dates (YYYY-MM-DD). Ask for a missing essential date range; "
            "never invent transactions, currencies, or totals. The data source "
            "is a local CSV export, not a connected bank."
        ),
    )

    budget_risk_agent = create_agent(
        model,
        tools=[evaluate_budget, detect_spending_anomalies],
        name="budget_risk_analyst",
        system_prompt=(
            "You are SpendSmart's budget and risk analyst. Compare spending with "
            "configured category limits using evaluate_budget. Use "
            "detect_spending_anomalies only when the requested period and suitable "
            "historical data are available. An anomaly is a review signal, not "
            "proof of fraud. Never label a transaction fraudulent or unauthorized. "
            "Use ISO dates and report missing history or unconfigured budgets."
        ),
    )

    savings_agent = create_agent(
        model,
        tools=[generate_savings_plan],
        name="savings_coach",
        system_prompt=(
            "You are SpendSmart's savings coach. Create realistic, non-judgmental "
            "savings recommendations using generate_savings_plan. Confirm that "
            "monthly income, target savings rate, and date range are available. "
            "Protect essential spending and clearly label projections as estimates, "
            "not guarantees. Never invent financial figures."
        ),
    )

    knowledge_agent = create_agent(
        model,
        tools=[knowledge_tool],
        name="financial_knowledge_expert",
        system_prompt=(
            "You are SpendSmart's financial education specialist. Use "
            "budgeting_knowledge for general budgeting and savings concepts. "
            "Do not use educational documents to answer questions about the user's "
            "transactions, balance, or personal budget. Clearly distinguish "
            "general guidance from personalized analysis."
        ),
    )

    supervisor_prompt = """
You are SpendSmart's central supervisor. The user communicates only with you.
Coordinate these specialists:
- transaction_analyst: transaction retrieval, categorization, financial metrics,
  and consolidated reports.
- budget_risk_analyst: configured budget comparisons and possible spending anomalies.
- savings_coach: realistic savings plans and target evaluation.
- financial_knowledge_expert: general financial education from the RAG knowledge base.

Routing and workflow rules:
1. Identify the user's goal, date range, currency, and required level of detail.
2. Delegate only the tasks needed; do not call every worker for every request.
3. For a comprehensive spending review, obtain transaction-derived findings first,
   then request budget/risk analysis when relevant, then a savings plan if the user
   supplied an income and savings goal.
4. For general budgeting concepts, use financial_knowledge_expert.
5. Give workers clear, self-contained tasks with the date range and relevant
   assumptions. Use their returned findings; do not invent missing data.
6. If an essential detail is missing, ask the user one concise clarification question.
7. Workers report back to you. You are responsible for synthesizing their findings
   into one coherent answer and identifying disagreements or missing information.
8. Keep the system read-only. Never authorize payments, transfers, purchases,
   budget edits, external sharing, or notifications.
9. State the period, currency, data coverage, and limitations. An anomaly is not
   proof of fraud. Separate observed facts from estimates and recommendations.
10. When the specialists have completed the required work, answer the user directly.
"""

    workflow = create_supervisor(
        [transaction_agent, budget_risk_agent, savings_agent, knowledge_agent],
        model=model,
        prompt=supervisor_prompt,
        supervisor_name="spendsmart_supervisor",
        include_agent_name="inline",
        output_mode="full_history",
    )

    # The checkpointer stores conversation state by thread_id. Use a distinct,
    # non-guessable thread_id per authenticated user in a deployed application.
    memory = InMemorySaver()
    return workflow.compile(checkpointer=memory)


def run_spendsmart(query: str, thread_id: str = "default", app=None) -> str:
    """Run one turn through the supervisor, retaining memory for this thread."""
    if app is None:
        app = build_agent()

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 60,
    }
    result = app.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
    )
    final_message = result["messages"][-1]
    return str(final_message.content)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ask the SpendSmart multi-agent personal finance assistant."
    )
    parser.add_argument("query", nargs="*", help="Natural-language finance question")
    parser.add_argument(
        "--thread-id",
        default="default",
        help="Conversation identifier used by the in-memory checkpointer",
    )
    args = parser.parse_args()

    prompt = " ".join(args.query).strip() or (
        "Analyze November 2026 spending, check the configured budget, "
        "and suggest ways to save 20% of a 6000 EGP monthly income."
    )
    app = build_agent()
    answer = run_spendsmart(prompt, thread_id=args.thread_id, app=app)
    print(answer)


if __name__ == "__main__":
    main()
