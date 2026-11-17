# 3. Tool Specifications

The tools below are proposed functions that the agent can call. Each specification includes a function name, input parameters with types, output parameters with types, and a description.

**Type conventions**

- `String`: text value.
- `Integer`: whole number.
- `Float`: decimal number used for a score or rate.
- `Decimal`: monetary or precision-sensitive numeric value.
- `Boolean`: true or false.
- `Date`: calendar date in ISO 8601 format (`YYYY-MM-DD`).
- `Array<T>`: list of values of type `T`.
- `Object`: structured collection of named fields.
- `Nullable<T>`: value may be `null`.

All monetary values must carry an associated currency. The examples use EGP, but the design can support other currencies.

---

## Tool 1 — Retrieve Transactions

**Function name:** `retrieve_transactions`

**Description:** Retrieves the user's authorized financial transactions for a selected date range. The data source could be a read-only banking integration or a user-uploaded CSV file. The tool must only return data the user is authorized to access.

### Input parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `user_id` | String | Yes | Internal identifier for the authenticated user |
| `start_date` | Date | Yes | First date to include |
| `end_date` | Date | Yes | Last date to include |
| `transaction_type` | String | No | Filter such as `all`, `income`, or `expense`; defaults to `all` |
| `currency` | String | No | Currency filter, such as `EGP` |

### Output parameters

| Parameter | Type | Description |
|---|---|---|
| `transactions` | `Array<Transaction>` | Retrieved transaction records |
| `total_records` | Integer | Number of returned records |
| `currency` | String | Currency represented by the result |
| `retrieval_status` | Boolean | Whether retrieval succeeded |

**Transaction object fields**

| Field | Type | Description |
|---|---|---|
| `transaction_id` | String | Unique transaction identifier |
| `date` | Date | Transaction date |
| `merchant` | String | Merchant or transaction counterparty |
| `amount` | Decimal | Transaction amount |
| `description` | String | Available transaction description |
| `transaction_type` | String | `income` or `expense` |

---

## Tool 2 — Categorize Transactions

**Function name:** `categorize_transactions`

**Description:** Classifies transactions into spending or income categories. Example expense categories include food, transportation, shopping, education, healthcare, entertainment, bills, and subscriptions. Low-confidence classifications should be marked for review rather than presented as certain.

### Input parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `transactions` | `Array<Transaction>` | Yes | Transactions to classify |
| `categories` | `Array<String>` | Yes | Allowed category labels |
| `classification_mode` | String | No | `rule_based`, `model_based`, or `hybrid` |

### Output parameters

| Parameter | Type | Description |
|---|---|---|
| `categorized_transactions` | `Array<CategorizedTransaction>` | Original transaction data with category and confidence attached |
| `unclassified_count` | Integer | Number of transactions that could not be classified reliably |

**Categorized transaction additional fields**

| Field | Type | Description |
|---|---|---|
| `category` | String | Assigned category or `uncategorized` |
| `confidence_score` | Float | Classification confidence from 0.0 to 1.0 |

---

## Tool 3 — Calculate Financial Metrics

**Function name:** `calculate_financial_metrics`

**Description:** Calculates the user's financial summary for a selected period, including total income, expenses, remaining balance, savings rate, and category totals. Income should be derived from transaction records. If a user-reported income figure is supplied, it is a reference value and should be kept distinct from transaction-derived income.

### Input parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `categorized_transactions` | `Array<CategorizedTransaction>` | Yes | Categorized transaction data |
| `start_date` | Date | Yes | Start of analysis period |
| `end_date` | Date | Yes | End of analysis period |
| `reported_monthly_income` | `Nullable<Decimal>` | No | User-reported income for comparison |
| `currency` | String | Yes | Currency for the calculations |

### Output parameters

| Parameter | Type | Description |
|---|---|---|
| `transaction_income_total` | Decimal | Income total derived from transactions |
| `total_expenses` | Decimal | Expense total derived from transactions |
| `remaining_balance` | Decimal | Transaction income minus expenses for the period |
| `savings_rate` | `Nullable<Float>` | Savings rate where a valid income denominator exists |
| `category_totals` | `Object<String, Decimal>` | Expense total grouped by category |
| `period_summary` | Object | Period dates, currency, record counts, and calculation notes |

---

## Tool 4 — Detect Spending Anomalies

**Function name:** `detect_spending_anomalies`

**Description:** Compares current transactions with historical spending patterns to flag unusual amounts, sudden category spikes, or possible duplicate transactions. An anomaly is a signal for review, not proof of fraud.

### Input parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `current_transactions` | `Array<Transaction>` | Yes | Transactions in the current analysis period |
| `historical_transactions` | `Array<Transaction>` | Yes | Historical transactions used as a comparison baseline |
| `sensitivity_level` | String | No | `low`, `medium`, or `high`; controls how readily unusual activity is flagged |
| `detection_period_days` | Integer | No | Historical comparison window in days |

### Output parameters

| Parameter | Type | Description |
|---|---|---|
| `anomalies` | `Array<Anomaly>` | List of possible unusual events |
| `detection_status` | Boolean | Whether the analysis completed successfully |

**Anomaly object fields**

| Field | Type | Description |
|---|---|---|
| `transaction_id` | String | Related transaction identifier, if applicable |
| `anomaly_type` | String | Example: `unusually_large`, `category_spike`, `possible_duplicate` |
| `anomaly_score` | Float | Relative anomaly score |
| `reason` | String | Explanation of why it was flagged |
| `risk_level` | String | `low`, `medium`, or `high` |
| `requires_user_review` | Boolean | Whether the user should inspect the item |

---

## Tool 5 — Evaluate Budget

**Function name:** `evaluate_budget`

**Description:** Compares actual spending totals with user-provided budget limits. This is a read-only evaluation tool; it does not create or modify budget limits.

### Input parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `category_spending` | `Object<String, Decimal>` | Yes | Actual spending by category |
| `budget_limits` | `Object<String, Decimal>` | Yes | User-defined spending limit for each category |
| `budget_period` | String | Yes | Period represented, such as `monthly` or `weekly` |
| `currency` | String | Yes | Currency used by the budget |

### Output parameters

| Parameter | Type | Description |
|---|---|---|
| `budget_status` | String | Overall status, such as `within_budget`, `warning`, or `over_budget` |
| `remaining_budget` | `Object<String, Decimal>` | Remaining amount by category; negative values indicate an overrun |
| `utilization_rate` | `Object<String, Float>` | Percentage of each category budget used |
| `exceeded_categories` | `Array<String>` | Categories whose limits were exceeded |
| `budget_warnings` | `Array<String>` | Human-readable warnings |

---

## Tool 6 — Generate Savings Plan

**Function name:** `generate_savings_plan`

**Description:** Produces a proposed savings plan based on income, current expenses, existing savings, and the user's goal. It identifies potential reductions and estimates whether the target is realistic. It only recommends changes; it does not move money or change the user's budget.

### Input parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `monthly_income` | Decimal | Yes | Monthly income used for planning |
| `current_expenses` | `Object<String, Decimal>` | Yes | Current spending by category |
| `current_savings` | Decimal | No | Current savings amount; defaults to zero only if confirmed |
| `target_savings` | Decimal | Yes | Desired savings amount for the planning period |
| `financial_goals` | `Array<String>` | No | User's goals, such as emergency fund or tuition |
| `planning_period_months` | Integer | Yes | Number of months covered by the plan |
| `currency` | String | Yes | Currency for all monetary values |

### Output parameters

| Parameter | Type | Description |
|---|---|---|
| `recommended_monthly_savings` | Decimal | Proposed monthly savings contribution |
| `suggested_budget` | `Object<String, Decimal>` | Proposed category budgets |
| `reduction_opportunities` | `Array<ReductionOpportunity>` | Categories where reductions may be possible |
| `projected_savings` | Decimal | Estimated savings over the planning period |
| `goal_feasibility` | String | `likely`, `challenging`, or `insufficient_data` |
| `recommendations` | `Array<String>` | Actionable suggestions and assumptions |

**Reduction opportunity fields**

| Field | Type | Description |
|---|---|---|
| `category` | String | Spending category |
| `current_amount` | Decimal | Current spending |
| `suggested_amount` | Decimal | Proposed spending |
| `potential_reduction` | Decimal | Difference between current and suggested amounts |
| `rationale` | String | Why the proposed reduction may be reasonable |

---

## Tool 7 — Generate Financial Report

**Function name:** `generate_financial_report`

**Description:** Combines the outputs of the analysis tools into a structured report. The report can include financial metrics, category breakdowns, budget status, anomalies requiring review, and savings recommendations.

### Input parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `financial_metrics` | Object | Yes | Output from the financial metrics tool |
| `categorized_transactions` | `Array<CategorizedTransaction>` | Yes | Categorized transactions for the report |
| `anomaly_results` | `Array<Anomaly>` | Yes | Detected anomalies, possibly empty |
| `budget_results` | Object | Yes | Budget evaluation result |
| `savings_plan` | Object | Yes | Proposed savings plan |
| `report_period` | String | Yes | Period label, such as `November 2026` |
| `output_format` | String | No | `markdown`, `json`, or `pdf` |

### Output parameters

| Parameter | Type | Description |
|---|---|---|
| `report_id` | String | Unique report identifier |
| `report_summary` | String | Short natural-language summary |
| `report_content` | Object | Structured report sections |
| `file_url` | `Nullable<String>` | File location if a downloadable file was actually generated |
| `generation_status` | Boolean | Whether report generation succeeded |

---

## Tool selection at a glance

| User request | Likely tools |
|---|---|
| "Show my spending last month" | Retrieve → Categorize → Calculate metrics |
| "Where am I overspending?" | Retrieve → Categorize → Calculate metrics → Evaluate budget |
| "Was anything unusual this month?" | Retrieve current and historical data → Detect anomalies |
| "Help me save 1,200 EGP monthly" | Retrieve → Categorize → Calculate metrics → Generate savings plan |
| "Give me a complete monthly report" | Retrieve → Categorize → Calculate metrics → Detect anomalies → Evaluate budget → Generate savings plan → Generate report |

The agent should not call every tool for every request. It should select only the tools needed to answer the user's actual question.