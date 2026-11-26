# 6. LlamaIndex RAG Knowledge Component

This document describes the LlamaIndex component retained inside the SpendSmart multi-agent architecture. LlamaIndex is no longer the top-level agent orchestrator: LangGraph's supervisor coordinates the finance specialists, while LlamaIndex powers the general financial-knowledge retrieval tool.

## 6.1 Role in the multi-agent system

The `financial_knowledge_expert` worker receives the `budgeting_knowledge` tool. That tool queries Markdown guidance indexed in Chroma. It is intended for general financial education, not for retrieving the user's personal transaction facts.

## 6.2 RAG pipeline

```text
Markdown files in knowledge/
          |
          v
SimpleDirectoryReader
          |
          v
HuggingFaceEmbedding
          |
          v
ChromaVectorStore
          |
          v
LlamaIndex VectorStoreIndex
          |
          v
Query Engine (Groq LLM)
          |
          v
budgeting_knowledge tool
          |
          v
financial_knowledge_expert
          |
          v
SpendSmart supervisor
```

The first initialization may take longer because the embedding model must be downloaded and the Chroma collection must be created. The persistent Chroma directory is local.

## 6.3 Important separation of facts

- Personal transaction totals, balances, savings rates, and category spending must come from the CSV finance tools.
- The RAG index contains general budgeting guidance only.
- The knowledge worker must not use educational documents as evidence of a user's personal financial position.
- If the knowledge folder is missing or empty, the RAG component cannot initialize; add at least one Markdown document before running the full application.

## 6.4 Dependencies

The RAG component uses:

- `llama-index-core`
- `llama-index-llms-groq`
- `llama-index-embeddings-huggingface`
- `llama-index-vector-stores-chroma`
- `chromadb`

Install the complete project dependencies with:

```bash
pip install -r requirements.txt
```

## 6.5 Configuration

Set these values in a private local `.env` file:

```dotenv
GROQ_API_KEY=your_new_groq_key
GROQ_MODEL=openai/gpt-oss-120b
HF_EMBED_MODEL=BAAI/bge-small-en-v1.5
```

Never place access tokens in source code, notebook outputs, or Git history. Revoke and replace any key that has been exposed.

## 6.6 Prototype limitations

- The knowledge base is local and only contains the Markdown files supplied in `knowledge/`.
- Retrieved guidance is general education, not regulated financial advice.
- Chroma persists locally; this is not a hosted multi-user knowledge service.
- The RAG component does not access a bank or external financial account.
