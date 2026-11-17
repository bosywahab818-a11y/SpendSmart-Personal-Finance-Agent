# 4. Agent Workflow

## 4.1 High-level architecture

```text
                 USER
                   |
                   v
        Natural-language request
                   |
                   v
          LLM / AGENT BRAIN
       (GPT-OSS-120B via GroqCloud)
                   |
          Understand the goal
          Plan the next action
          Select the required tool
                   |
                   v
             TOOL LAYER
   +---------------+----------------+
   | Retrieve      | Categorize      |
   | transactions  | transactions    |
   +---------------+----------------+
   | Calculate     | Detect spending |
   | metrics       | anomalies       |
   +---------------+----------------+
   | Evaluate      | Generate savings|
   | budget        | plan            |
   +---------------+----------------+
                   |
                   v
         Generate financial report
                   |
                   v
       Tool results returned to LLM
                   |
                   v
       Interpret, validate, explain
                   |
                   v
          RESPONSE TO THE USER
```

## 4.2 Step-by-step example

User request:

> "Analyze my spending this month and help me save 20% of my 6,000 EGP income."

1. **Understand the request:** The agent identifies a monthly spending analysis and a 20% savings target.
2. **Calculate the target:** 20% of 6,000 EGP is 1,200 EGP.
3. **Check data availability:** The agent checks whether it has authorized transaction data and the relevant date range.
4. **Retrieve transactions:** It calls `retrieve_transactions`.
5. **Categorize:** It calls `categorize_transactions` on the retrieved records.
6. **Calculate metrics:** It calls `calculate_financial_metrics` to calculate actual totals and category spending.
7. **Evaluate budget:** If the user has supplied category limits, it calls `evaluate_budget`.
8. **Check unusual activity:** If historical data is available and useful, it calls `detect_spending_anomalies`.
9. **Plan savings:** It calls `generate_savings_plan` using the verified spending information and the 1,200 EGP target.
10. **Prepare the report:** It calls `generate_financial_report` if a consolidated report is useful.
11. **Respond:** It summarizes findings, explains assumptions, highlights items that need user review, and presents practical recommendations.

## 4.3 Tool orchestration rules

- Retrieve data before analyzing it.
- Categorize transactions before producing category-level spending totals.
- Calculate metrics from the transaction records rather than guessing.
- Use historical data for anomaly detection; if it is unavailable, explain that anomaly detection is limited.
- Evaluate a budget only when budget limits are available.
- Generate a savings plan only when the income, expense, and goal information is sufficient.
- Generate a report when the user requests one or when a consolidated report materially helps.
- If a tool fails, do not fabricate its result. Explain the failure and continue only with the information that is still reliable.

## 4.4 Human approval points

SpendSmart can autonomously analyze authorized data and prepare recommendations. It must obtain explicit user approval before:
- Creating or changing a persistent budget.
- Sending a report to another person.
- Triggering external notifications.
- Connecting a new financial data source or expanding access permissions.

The proposed tools are read-only or recommendation-only. No payment, transfer, or purchase tool is included.