"""SpendSmart multi-agent supervisor implementation.

The existing finance functions remain in spendsmart_agent.py. This module
organizes them into specialist LangGraph agents coordinated by a supervisor.
All financial tools are read-only or recommendation-only.
"""
from __future__ import annotations

import argparse
import os
import re
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
directly with the user. Delegate work to specialist agents and report only
verified findings.

AVAILABLE SPECIALISTS:
- transaction_expert: retrieve and categorize authorized CSV transactions.
- analysis_expert: calculate financial metrics and detect spending anomalies.
- budget_expert: evaluate spending against the configured read-only budget.
- savings_expert: create numerical savings plans when specifically requested.
- financial_education_expert: retrieve general financial guidance.

WORKFLOW:

1. DATA FIRST
- Use the local transaction CSV as the primary source for transaction-derived
  income, expenses, balances and spending patterns.
- Never assume missing records mean zero income or expenses.
- Never ask the user for information already available in the tools.

2. DATE HANDLING
- A requested year means the full calendar year.
- A requested month means its first through last calendar day.
- Always distinguish the requested period from the actual transaction period.
- Never present partial records as complete annual or monthly totals.

3. TRANSACTION ANALYSIS
- Delegate totals, balances, savings rates, category totals and anomalies
  to analysis_expert.
- Delegate transaction lists and categorization to transaction_expert.
- Report anomaly results exactly as returned by the analysis tool.
- If the anomaly list is empty, say that no anomalies were flagged by the tool.
- Do NOT claim that duplicates, fraud or unusual transactions were checked
  unless the tool explicitly reports those checks.

4. BUDGET ANALYSIS
- For every comprehensive financial report or budget-status request,
  delegate to budget_expert and use evaluate_budget results.
- Report the actual configured limits, prorated limits, spending, utilization
  and status returned by the tool when available.
- Never replace configured budget results with generic financial rules,
  common percentages or invented targets.
- Never invent category limits or claim a category is over budget unless
  the budget tool reports it.
- Clearly state that configured limits are examples if the tool identifies
  them as example limits.
- Mention the observed transaction period and any coverage limitations.
- If the budget tool fails or returns no result, say budget status is unknown.

5. SAVINGS AND RECOMMENDATIONS
- Give practical recommendations based on verified spending and budget results.
- Do not invent savings targets, income amounts or monthly budgets.
- Use savings_expert only for a requested numerical savings plan or projection.
- Clearly label assumptions and estimates.
- Do not estimate an emergency fund amount unless essential expenses and
  the relevant period are supported by available data.
- Do not describe subscriptions as recurring unless recurrence is verified.
- Do not describe transaction-derived income as salary or allowance unless
  the transaction records explicitly support that description.

6. FINANCIAL EDUCATION
- Delegate general financial education questions to financial_education_expert.
- Keep general guidance separate from findings based on personal transactions.

7. COMPREHENSIVE REPORTS
- For a comprehensive report, request both analysis_expert and budget_expert.
- Include income, expenses, remaining balance, savings rate, category totals,
  anomaly findings and budget status when the tools return those results.
- Include concise recommendations grounded in the verified findings.
- Do not claim a section was checked unless its specialist returned results.

8. ACCURACY AND COVERAGE
- Never invent tool outputs, figures, dates, categories or financial facts.
- Use available_data_period and period_data_period from the metrics tool.
- State the currency and actual date coverage alongside financial totals.
- A date range does not prove that every transaction is present.
- Explicitly warn when the requested period extends beyond available records.
- Never extrapolate partial records into full-period totals.
- Do not combine different currencies.
- An anomaly is a review signal, not proof of fraud.
- Explain tool failures and data limitations.
- If a figure or claim is not supported by a tool result, omit it or clearly
  identify it as general guidance rather than a personal financial finding.

FINANCIAL SAFETY:
- The only personal transaction source is the authorized local CSV export.
- The budget JSON is read-only. Never edit it or claim to change a budget.
- Never claim to connect to a bank, move money, make purchases or execute payments.
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
    model = model or get_llm()

    transaction_agent = create_agent(
        model=model,
        tools=[retrieve_transactions, categorize_transactions],
        name="transaction_expert",
        system_prompt=(
            "You are SpendSmart's transaction specialist. "
            "Use the supplied tools to retrieve and categorize records "
            "from the authorized local CSV only. "
            "Use ISO dates (YYYY-MM-DD). "
            "Never calculate totals by guessing. "
            "If dates are missing, ask for them. "
            "You cannot edit transactions."
        ),
    )

    analysis_agent = create_agent(
        model=model,
        tools=[calculate_financial_metrics, detect_spending_anomalies],
        name="analysis_expert",
        system_prompt=(
            "You are SpendSmart's financial analysis specialist. "
            "Always use calculate_financial_metrics for financial totals. "
            "Always report the requested period separately from the actual "
            "available_data_period and period_data_period returned by the tool. "
            "Never describe requested dates as actual data coverage. "
            "If requested_period_within_available_date_range is false, "
            "clearly warn that the dataset does not cover the entire requested "
            "date range. Even if the requested dates fall within the CSV's "
            "earliest and latest dates, do not assume every transaction is "
            "present. Financial totals describe only the available records. "
            "Report the currency and transaction count. "
            "Do not extrapolate partial data into annual totals. "
            "Use detect_spending_anomalies for anomaly checks. "
            "Anomaly flags are not proof of fraud. "
            "Never invent missing history or totals."
        ),
    )

    budget_agent = create_agent(
        model=model,
        tools=[evaluate_budget],
        name="budget_expert",
        system_prompt=(
            "You are SpendSmart's budget specialist. "
            "You MUST call evaluate_budget for every budget-status request. "
            "Use the exact start_date and end_date provided by the supervisor. "
            "Do not answer from memory or infer budget status without calling "
            "the tool. "
            "After calling the tool, return its complete result faithfully, "
            "including currency, requested_period, observed_transaction_period, "
            "requested_period_boundary_coverage, observed_period_month_equivalent, "
            "every category's spent amount, monthly_limit, prorated_limit_for_"
            "observed_period, remaining amount, utilization_rate and status, "
            "plus exceeded_categories, overall status and note. "
            "Do not omit categories or replace tool results with generic advice. "
            "If the tool returns budget_not_configured, report that exact status. "
            "If the tool fails, explain the failure instead of claiming that no "
            "budget configuration exists. "
            "Never invent budget limits or results."
        ),
    )

    savings_agent = create_agent(
        model=model,
        tools=[generate_savings_plan],
        name="savings_expert",
        system_prompt=(
            "You are SpendSmart's savings specialist. "
            "Use generate_savings_plan when the user requests a specific "
            "numerical savings target or plan. "
            "Do not invent income, expenses, or savings figures. "
            "Clearly label assumptions and projections as estimates."
        ),
    )

    education_agent = create_agent(
        model=model,
        tools=[search_budgeting_knowledge],
        name="financial_education_expert",
        system_prompt=(
            "You are SpendSmart's financial education specialist. "
            "Use search_budgeting_knowledge to retrieve relevant guidance. "
            "Explain financial concepts clearly and practically. "
            "Do not present general educational guidance as personalized "
            "financial data."
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
    global budget_expert_agent
    model = get_llm()
    agents = build_agents(model)
    budget_expert_agent = agents[2]
    workflow = create_supervisor(
        agents,
        model=model,
        prompt=SUPERVISOR_PROMPT,
        supervisor_name="spendsmart_supervisor",
        include_agent_name="inline",
        output_mode="last_message",
    )
    return workflow.compile(checkpointer=checkpointer or InMemorySaver())


# One compiled graph keeps the same in-memory checkpointer alive during this process.
spendsmart_app = None
budget_expert_agent = None



def run_spendsmart(query: str, thread_id: str = "default", app=None) -> str:
    """Run a user request and provide verified budget data when relevant."""
    global spendsmart_app, budget_expert_agent

    if spendsmart_app is None or budget_expert_agent is None:
        spendsmart_app = build_supervisor()

    if app is None:
        app = spendsmart_app

    enhanced_query = query

    budget_keywords = (
        r"\bbudget\b|\bbudgets\b|financial report|"
        r"comprehensive report|financial position|"
        r"spending report|monthly report"
    )

    if re.search(budget_keywords, query, re.IGNORECASE):
        from datetime import date

        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", query)
        year_match = re.search(r"\b(20\d{2})\b", query)

        if len(dates) >= 2:
            start_date, end_date = dates[0], dates[1]
        elif len(dates) == 1:
            start_date = end_date = dates[0]
        elif year_match:
            year = int(year_match.group(1))
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
        else:
            year = date.today().year
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        if start > end:
            start_date, end_date = end.isoformat(), start.isoformat()

        try:
            budget_agent = budget_expert_agent

            budget_result = budget_agent.invoke({
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Check the configured budget from {start_date} "
                        f"through {end_date}. You MUST call evaluate_budget "
                        "and return its complete result. Do not invent values."
                    )
                }]
            })

            budget_message = budget_result["messages"][-1]
            budget_content = getattr(
                budget_message, "content", str(budget_message)
            )

            if isinstance(budget_content, list):
                budget_content = "\n".join(
                    str(item.get("text", item))
                    if isinstance(item, dict) else str(item)
                    for item in budget_content
                )

            enhanced_query += (
                "\n\nVERIFIED BUDGET EXPERT RESULT:\n"
                f"Period checked: {start_date} to {end_date}\n"
                f"{budget_content}\n\n"
                "Use this verified budget result in your answer. "
                "Do not replace its values with estimates or invented limits. "
                "Clearly mention that configured limits are examples if "
                "the tool result says so."
            )

        except Exception as exc:
            enhanced_query += (
                "\n\nIMPORTANT: The automatic budget check failed. "
                "Do not invent or estimate budget results. "
                f"Budget check error: {exc}"
            )

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": MAX_STEPS,
    }

    result = app.invoke(
        {"messages": [{"role": "user", "content": enhanced_query}]},
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
