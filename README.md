# SpendSmart – Personal Finance Agent

**An agentic AI concept for personal expense tracking, budget monitoring, anomaly detection, and savings recommendations.**

SpendSmart is a proposed personal finance assistant that helps users understand where their money goes and make better day-to-day budgeting decisions. It combines an LLM with specialized tools that retrieve and analyze financial transaction data, evaluate budgets, detect unusual spending patterns, and generate understandable reports.

> **Project scope:** This repository documents the agent design and assignment deliverables. It is a conceptual design, not a live banking application. No real financial accounts are connected and no transactions are executed.

## Assignment deliverables

1. **Use case:** SpendSmart personal finance assistant.
2. **LLM and provider:** GPT-OSS-120B, developed by OpenAI and accessed through GroqCloud (`openai/gpt-oss-120b`).
3. **Tools:** Seven proposed tools, each with a function name, typed inputs, typed outputs, and a description.
4. **System prompt:** A complete instruction set defining the agent's role, workflow, tool-use rules, privacy boundaries, and response format.

## Repository structure

```text
SpendSmart-Personal-Finance-Agent/
├── README.md
├── docs/
│   ├── 01_brainstorming_and_use_case.md
│   ├── 02_llm_and_provider.md
│   ├── 03_tool_specifications.md
│   ├── 04_agent_workflow.md
│   └── 05_system_prompt.md
└── LICENSE
```

## Quick overview

A user may ask:

> "I earn 6,000 EGP per month. Help me understand my spending and save 20% of my income."

SpendSmart can retrieve the user's authorized transactions, categorize them, calculate spending metrics, compare expenses with budget limits, identify unusual activity, and suggest a realistic savings plan. It then explains its findings in a clear report.

## Important design principles

- **Read-only by default:** the agent analyzes authorized data; it does not move money or make purchases.
- **User approval:** it must ask before changing a budget, sharing a report, or triggering an external notification.
- **Privacy:** it must never request passwords, PINs, or one-time verification codes.
- **Honest analysis:** an unusual transaction is a possible anomaly, not proof of fraud.
- **Traceable results:** calculations should come from tools and supplied data, not invented figures.
- **Practical recommendations:** savings suggestions should be realistic and based on observed spending.

## Detailed documentation

- [Brainstorming and use case](docs/01_brainstorming_and_use_case.md)
- [LLM and provider selection](docs/02_llm_and_provider.md)
- [Tool specifications](docs/03_tool_specifications.md)
- [Agent workflow](docs/04_agent_workflow.md)
- [Complete system prompt](docs/05_system_prompt.md)

## Example scenario

Assume a user has a monthly income of **6,000 EGP** and wants to save **20% (1,200 EGP)**. SpendSmart reviews the available transaction history, estimates the user's current savings rate, identifies categories with possible reductions, and proposes a budget. The 1,200 EGP target is treated as a goal to evaluate—not as a guaranteed outcome.

## Status

**Design/documentation prototype.** Implementation, integrations, authentication, and testing would be separate future phases.
