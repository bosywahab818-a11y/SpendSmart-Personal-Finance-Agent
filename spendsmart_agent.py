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


def build_knowledge_tool():
    """Build a Chroma-backed LlamaIndex RAG query tool for general budgeting guidance."""
    import chromadb
    from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
    from llama_index.core.tools import QueryEngineTool
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore

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
    query_engine = index.as_query_engine(similarity_top_k=3)
    return QueryEngineTool.from_defaults(
        query_engine=query_engine,
        name="budgeting_knowledge",
        description=(
            "Searches general budgeting and savings guidance. Use this for general "
            "financial education, not as a source of the user's personal transaction facts."
        ),
        return_direct=False,
    )


def build_agent():
    """Create the LlamaIndex ReAct agent using the notebook's Hugging Face pattern."""
    from llama_index.core.agent.workflow import ReActAgent
    from llama_index.core.tools import FunctionTool
    from llama_index.llms.huggingface_api import HuggingFaceInferenceAPI

    token = os.getenv("HF_TOKEN")
    if not token:
        raise EnvironmentError("Set HF_TOKEN in your environment or .env file first.")

    llm = HuggingFaceInferenceAPI(
        model=LLM_MODEL,
        token=token,
        provider="auto",
        temperature=0.2,
        num_output=700,
    )
    functions = [
        retrieve_transactions,
        categorize_transactions,
        calculate_financial_metrics,
        detect_spending_anomalies,
        evaluate_budget,
        generate_savings_plan,
        generate_financial_report,
    ]
    tools = [FunctionTool.from_defaults(fn=fn) for fn in functions]
    tools.append(build_knowledge_tool())

    system_prompt = """
You are SpendSmart, a careful personal finance analysis assistant.
Use tools for all claims about the user's transaction data and calculations.
The available transaction source is a local CSV export; never claim to access a bank.
Use ISO dates (YYYY-MM-DD) when calling tools. Ask a concise question if the period,
income, or savings target is essential and missing. Select only the tools needed.
The budgeting_knowledge tool contains general educational guidance, not personal data.
Distinguish actual transaction totals from user-reported income and estimates.
An anomaly is not proof of fraud. Never invent records, balances, or tool results.
Never ask for passwords, PINs, OTPs, or card security codes. Never initiate payments,
transfers, purchases, or modify budget files. Treat the budget file as read-only.
State the date range, currency, and data limitations. Be non-judgmental and practical.
"""
    return ReActAgent(tools=tools, llm=llm, system_prompt=system_prompt)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the SpendSmart LlamaIndex agent.")
    parser.add_argument("query", nargs="*", help="Natural-language finance question")
    args = parser.parse_args()
    prompt = " ".join(args.query).strip() or (
        "Analyze November 2026 spending, check the configured budget, "
        "and suggest ways to save 20% of a 6000 EGP monthly income."
    )
    agent = build_agent()
    response = await agent.run(user_msg=prompt)
    print(response)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
