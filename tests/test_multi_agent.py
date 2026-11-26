import sys
import types
import unittest
from unittest.mock import MagicMock, patch

import spendsmart_agent as spend


def fake_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


class MultiAgentArchitectureTests(unittest.TestCase):
    def _fake_dependencies(self):
        calls = {"workers": [], "supervisor": {}, "compiled_with": None}

        class FakeChatGroq:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeGroq:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeMemory:
            pass

        class FakeWorkflow:
            def compile(self, checkpointer=None):
                calls["compiled_with"] = checkpointer
                return "compiled-spendsmart-app"

        def fake_create_agent(model, tools, name, system_prompt):
            worker = {
                "model": model,
                "tools": tools,
                "name": name,
                "system_prompt": system_prompt,
            }
            calls["workers"].append(worker)
            return worker

        def fake_create_supervisor(workers, **kwargs):
            calls["supervisor"] = {"workers": workers, **kwargs}
            return FakeWorkflow()

        modules = {
            "langchain": fake_module("langchain", __path__=[]),
            "langchain.agents": fake_module(
                "langchain.agents", create_agent=fake_create_agent
            ),
            "langchain_groq": fake_module(
                "langchain_groq", ChatGroq=FakeChatGroq
            ),
            "langgraph": fake_module("langgraph", __path__=[]),
            "langgraph.checkpoint": fake_module(
                "langgraph.checkpoint", __path__=[]
            ),
            "langgraph.checkpoint.memory": fake_module(
                "langgraph.checkpoint.memory", InMemorySaver=FakeMemory
            ),
            "langgraph_supervisor": fake_module(
                "langgraph_supervisor", create_supervisor=fake_create_supervisor
            ),
            "llama_index": fake_module("llama_index", __path__=[]),
            "llama_index.llms": fake_module(
                "llama_index.llms", __path__=[]
            ),
            "llama_index.llms.groq": fake_module(
                "llama_index.llms.groq", Groq=FakeGroq
            ),
        }
        return modules, calls

    def test_build_agent_wires_four_specialists_and_checkpointer(self):
        modules, calls = self._fake_dependencies()
        with patch.dict(sys.modules, modules), \
             patch.dict("os.environ", {"GROQ_API_KEY": "unit-test-key"}), \
             patch.object(spend, "build_knowledge_tool", return_value="rag-tool"):
            app = spend.build_agent()

        self.assertEqual(app, "compiled-spendsmart-app")
        self.assertEqual(
            [worker["name"] for worker in calls["workers"]],
            [
                "transaction_analyst",
                "budget_risk_analyst",
                "savings_coach",
                "financial_knowledge_expert",
            ],
        )
        workers = {worker["name"]: worker for worker in calls["workers"]}
        self.assertEqual(
            workers["transaction_analyst"]["tools"],
            [
                spend.retrieve_transactions,
                spend.categorize_transactions,
                spend.calculate_financial_metrics,
                spend.generate_financial_report,
            ],
        )
        self.assertEqual(
            workers["budget_risk_analyst"]["tools"],
            [spend.evaluate_budget, spend.detect_spending_anomalies],
        )
        self.assertEqual(
            workers["savings_coach"]["tools"],
            [spend.generate_savings_plan],
        )
        self.assertEqual(
            workers["financial_knowledge_expert"]["tools"], ["rag-tool"]
        )
        self.assertEqual(len(calls["supervisor"]["workers"]), 4)
        self.assertEqual(
            calls["supervisor"]["supervisor_name"], "spendsmart_supervisor"
        )
        self.assertIsNotNone(calls["compiled_with"])

    def test_run_spendsmart_passes_thread_id_and_returns_final_message(self):
        app = MagicMock()
        app.invoke.return_value = {
            "messages": [types.SimpleNamespace(content="SpendSmart test answer")]
        }
        answer = spend.run_spendsmart(
            "Summarize my spending",
            thread_id="test-session-123",
            app=app,
        )
        self.assertEqual(answer, "SpendSmart test answer")
        app.invoke.assert_called_once()
        payload, config = app.invoke.call_args.args
        self.assertEqual(
            payload["messages"],
            [{"role": "user", "content": "Summarize my spending"}],
        )
        self.assertEqual(
            config["configurable"]["thread_id"], "test-session-123"
        )
        self.assertEqual(config["recursion_limit"], 60)

    def test_build_agent_requires_groq_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(EnvironmentError, "GROQ_API_KEY"):
                spend.build_agent()


if __name__ == "__main__":
    unittest.main()
