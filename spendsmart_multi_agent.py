"""SpendSmart multi-agent supervisor implementation.

The existing finance functions remain in spendsmart_agent.py. This module
organizes them into specialist LangGraph agents coordinated by a supervisor.
All financial tools are read-only or recommendation-only.
"""
from __future__ import annotations

import argparse
import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph_supervisor import create_supervisor

from spendsmart_agent import (
    TRANSACTIONS_PATH,
    BUDGETS_PATH,
    retrieve_transactions,
    categorize_transactions,
    calculate_financial_metrics,
    detect_spending_anomalies,
    evaluate_budget,
    generate_savings_plan,
    generate_financial_report,
    build_knowledge_tool,
)

load_dotenv()

MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_STEPS = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "60"))

SUPERVISOR_PROMPT = """
You are SpendSmart's supervisor. You are the ONLY agent that communicates
directly with the user. Delegate finance work to the specialist agents and
then synthesize their verified results into one clear answer.

Available specialists:
- transaction_expert: retrieve and categorize authorized local CSV transactions.
- analysis_expert: calculate financial metrics and flag possible spending anomalies.
- budget_expert: compare spending with the configured, read-only budget.
- savings_expert: create an illustrative savings plan from income, dates and target rate.
- financial_education_expert: retrieve general budgeting guidance from the Chroma knowledge base.

Routing and workflow:
1. Identify the user's requested date range, currency, income assumption and goal.
2. If an essential date range, monthly income, or savings target is missing, ask
   one concise clarification question instead of inventing values.
3. For transaction questions, delegate to transaction_expert.
4. For totals, balances, category metrics or unusual activity, delegate to
   analysis_expert. Use transaction_expert first when categorized records are
   specifically needed.
5. For budget status, delegate to budget_expert.
6. For savings goals, delegate to savings_expert after identifying the income,
   target savings rate and date range.
7. For general budgeting education, delegate to financial_education_expert.
8. For a comprehensive report, request the relevant analysis, budget and
   transaction findings, then combine them. Do not claim a report section was
   checked unless the relevant specialist returned results.
9. Give one task at a time. Workers report back to you; do not ask workers to
   communicate directly with each other.
10. Never invent tool results. Explain tool failures and data limitations.

Financial safety:
- The only personal transaction source is the authorized local CSV export.
- The budget JSON is read-only. Never edit it or claim to have changed a budget.
- Never claim to connect to a bank, move money, make purchases or execute payments.
- An anomaly is a review signal, not proof of fraud.
- Distinguish transaction-derived income from user-reported income.
- Do not combine different currencies. State the date range and currency.
- Treat savings projections as estimates, not guarantees.
- Never request passwords, PINs, OTPs or card security codes.
- Be calm, practical and non-judgmental.
"""

@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    """Initialize the Groq chat model used by the supervisor and workers."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is missing. Add your rotated Groq key to the local .env file."
        )
    return ChatGroq(
        model=MODEL_NAME,
        api_key=api_key,
        temperature=0.2,
        max_tokens=4096,
    )


@lru_cache(maxsize=1)
def get_knowledge_tool():
    """Build the existing Chroma RAG tool once, using a LlamaIndex Groq adapter."""
    from llama_index.llms.groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is required for the knowledge assistant.")
    rag_llm = Groq(model=MODEL_NAME, api_key=api_key, temperature=0.2)
    return build_knowledge_tool(rag_llm)


@tool
def search_budgeting_knowledge(query: str) -> str:
    """Retrieve general budgeting and savings education from the local Chroma knowledge base.

    Use this for general financial education, not for facts about the user's transactions.
    """
    result = get_knowledge_tool().call(query)
    return str(getattr(result, "content", result))


def build_agents(model=None):
    """Build and return the five independent specialist worker agents."""
    model = model or get_llm()

    transaction_agent = create_agent(
        model=model,
        tools=[retrieve_transactions, categorize_transactions],
        name="transaction_expert",
        system_prompt=(
            "You are SpendSmart's transaction specialist. Use the supplied tools to "
            "retrieve and categorize records from the authorized local CSV only. "
            "Use ISO dates (YYYY-MM-DD). Never calculate totals by guessing. "
            "If dates are missing, ask for them. You cannot edit transactions."
        ),
    )

    analysis_agent = create_agent(
        model=model,
        tools=[calculate_financial_metrics, detect_spending_anomalies],
        name="analysis_expert",
        system_prompt=(
            "You are SpendSmart's financial analysis specialist. Use tools for all "
            "metrics and anomaly checks. State date coverage and currency. Anomaly "
            "flags are not proof of fraud. Never invent missing history or totals."
        ),
    )

    budget_agent = create_agent(
        model=model,
        tools=[evaluate_budget],
        name="budget_expert",
        system_prompt=(
            "You are SpendSmart's budget specialist. Compare the selected period "
            "with the configured monthly category limits using evaluate_budget. "
            "The budget file is read-only and its limits may be examples. Never "
            "claim to change or save a budget."
        ),
    )

    savings_agent = create_agent(
        model=model,
        tools=[generate_savings_plan],
        name="savings_expert",
        system_prompt=(
            "You are SpendSmart's savings specialist. Use generate_savings_plan "
            "for estimates. Require positive monthly income, a target rate from "
            "0 to 1, and an ISO date range. Protect essential expenses and explain "
            "that suggested reductions are illustrative, not guaranteed."
        ),
    )

    education_agent = create_agent(
        model=model,
        tools=[search_budgeting_knowledge],
        name="financial_education_expert",
        system_prompt=(
            "You are SpendSmart's financial education specialist. Use the Chroma "
            "knowledge tool for general budgeting concepts. Do not use educational "
            "documents as evidence of the user's personal financial situation."
        ),
    )

    return [
        transaction_agent,
        analysis_agent,
        budget_agent,
        savings_agent,
        education_agent,
    ]


def build_supervisor(checkpointer=None):
    """Compile the supervisor graph with specialist handoffs and conversation memory."""
    model = get_llm()
    agents = build_agents(model)
    workflow = create_supervisor(
        agents,
        model=model,
        prompt=SUPERVISOR_PROMPT,
        supervisor_name="spendsmart_supervisor",
        include_agent_name="inline",
        output_mode="full_history",
    )
    return workflow.compile(checkpointer=checkpointer or InMemorySaver())


# One compiled graph keeps the same in-memory checkpointer alive during this process.
spendsmart_app = None


def run_spendsmart(query: str, thread_id: str = "default", app=None) -> str:
    """Run a user request; reuse thread_id to continue the same in-process conversation."""
    global spendsmart_app
    if app is None:
        if spendsmart_app is None:
            spendsmart_app = build_supervisor()
        app = spendsmart_app

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": MAX_STEPS,
    }
    result = app.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
    )
    final_message = result["messages"][-1]
    content = getattr(final_message, "content", str(final_message))
    if isinstance(content, list):
        content = "\n".join(
            str(item.get("text", item)) if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ask the SpendSmart multi-agent personal finance assistant."
    )
    parser.add_argument("query", nargs="*", help="Natural-language finance question")
    parser.add_argument(
        "--thread-id",
        default="default",
        help="Conversation identifier (memory lasts only while this process is running).",
    )
    args = parser.parse_args()
    query = " ".join(args.query).strip() or (
        "Analyze my spending from 2026-11-01 to 2026-11-18, check my configured "
        "budget, and suggest ways to save 20% of a 6000 EGP monthly income."
    )
    print(run_spendsmart(query, thread_id=args.thread_id))


if __name__ == "__main__":
    main()
