# 2. LLM and Provider Selection

## 2.1 Selected model

**Model:** GPT-OSS-120B  
**Model identifier on GroqCloud:** `openai/gpt-oss-120b`  
**Model developer:** OpenAI  
**Inference provider:** GroqCloud

It is important to distinguish the model developer from the inference provider: OpenAI develops the model, while GroqCloud is the selected service through which the proposed system accesses it.

## 2.2 Why choose this model?

SpendSmart needs an LLM that can understand natural-language financial questions, plan a sequence of actions, choose suitable tools, interpret structured tool outputs, and explain results clearly.

The model is selected for the proposed design because it is intended for reasoning-oriented tasks and can be used in a tool-calling workflow. The exact availability and behavior of tool calling, structured output, context limits, latency, and pricing should be verified against the provider's current documentation before implementation.

## 2.3 Responsibilities of the LLM

The LLM is responsible for:

- Understanding the user's financial question and goal.
- Identifying which information is missing.
- Planning the required tool sequence.
- Selecting and invoking the appropriate tools.
- Interpreting tool results and resolving inconsistencies.
- Explaining calculations and recommendations in plain language.
- Respecting privacy, authorization, and safety rules.

## 2.4 What the LLM should not do

The LLM should not invent transaction records, balances, or calculations. It should not claim that a transaction is fraudulent merely because it is unusual. It must not request credentials or perform financial transactions.

## 2.5 Alternative models considered

| Model option | Provider | Why it could be considered |
|---|---|---|
| Gemini | Google | Alternative for general reasoning and tool-oriented workflows |
| Claude | Anthropic | Alternative for long-context reasoning and clear explanations |
| GPT-OSS-120B | GroqCloud inference; model developed by OpenAI | Selected option for this proposed design |

The alternatives are included as design options, not as a claim that one model is universally better. A real implementation should benchmark candidate models on tool-selection accuracy, calculation-grounding, response quality, latency, cost, and privacy requirements.

## 2.6 Selection summary

The proposed stack uses GPT-OSS-120B through GroqCloud as the agent's language and reasoning layer. Financial calculations and data operations are delegated to explicit tools so that the LLM does not need to perform every operation from memory.