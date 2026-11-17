# 1. Brainstorming and Use Case

## 1.1 Starting point: what problem could an agent solve?

Before selecting the final idea, consider common situations where people need repeated analysis, multiple steps, and decisions based on changing information.

| Idea | Problem | Possible agent behavior |
|---|---|---|
| Expense Tracking Agent | People lose track of small daily expenses | Collect, organize, and summarize transactions |
| Smart Budgeting Agent | People set budgets but do not monitor them | Compare spending with category limits and warn about overspending |
| Financial Anomaly Detection Agent | Unusual charges can be difficult to notice | Compare current activity with historical patterns and flag outliers |
| Personal Finance Agent | These problems are connected | Coordinate tracking, analysis, budget monitoring, anomaly detection, and savings planning |

## 1.2 Selected idea: SpendSmart

**SpendSmart – Personal Finance Agent** is an AI-powered assistant that helps a user monitor personal finances and make informed budgeting decisions.

The idea combines the most useful parts of the brainstorming options into one agentic workflow. Instead of answering only one question, the system can decide which analysis steps are needed, call the relevant tools, inspect their results, and then provide a useful recommendation.

## 1.3 Problem statement

Many people have difficulty understanding their spending habits. They may know their income but not exactly how much they spend in each category, whether they are exceeding a budget, or where they could save money. Reviewing transactions manually is time-consuming.

SpendSmart aims to reduce this effort by analyzing authorized financial data and converting it into clear summaries and practical recommendations.

## 1.4 Intended users

- Students managing a monthly allowance.
- Employees managing a fixed monthly salary.
- Individuals trying to reduce unnecessary expenses.
- Users saving toward a personal goal.

## 1.5 Main objectives

1. Retrieve financial transactions for a selected period.
2. Categorize transactions into understandable spending groups.
3. Calculate income, expenses, remaining balance, and savings rate.
4. Detect unusual spending patterns and possible duplicate transactions.
5. Compare actual spending with user-defined budget limits.
6. Recommend realistic ways to reach a savings goal.
7. Generate a readable financial summary.

## 1.6 Example user scenario

A user says:

> "My monthly income is 6,000 EGP. I want to save 20% of it. Analyze my spending and tell me how I can reach that goal."

The target savings amount is:

- Monthly income: 6,000 EGP
- Target savings rate: 20%
- Target savings amount: 1,200 EGP

SpendSmart should not immediately invent a budget. It should first check whether it has access to the user's authorized transaction data. If data is available, it can retrieve the relevant period, categorize transactions, calculate the current financial position, compare category spending with budget limits if supplied, and identify possible savings opportunities.

It then explains whether the target appears achievable from the available data and what changes may help. If transaction history is missing or incomplete, it should clearly state that limitation and ask for the missing information.

## 1.7 Why is this an agentic system?

A conventional chatbot may provide general budgeting tips. An agentic system goes further:

- It interprets the user's goal.
- It determines which steps and tools are required.
- It calls tools in a logical sequence.
- It uses tool outputs to decide what to do next.
- It can repeat or refine analysis when results are incomplete.
- It combines the results into a final recommendation.

The LLM acts as the reasoning and orchestration layer. The tools perform specific operations such as retrieving transactions and calculating metrics.

## 1.8 Expected benefits

- Saves time compared with manual transaction review.
- Makes spending patterns easier to understand.
- Helps users notice budget overruns earlier.
- Supports goal-based saving.
- Presents analysis in natural language.

## 1.9 Scope and limitations

SpendSmart is a budgeting and financial-awareness assistant, not a bank, accountant, or licensed financial adviser. It does not transfer money, execute payments, purchase products, or guarantee savings. Its conclusions depend on the completeness and accuracy of the supplied data.