import json

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import app as web
from agent import researcher


class FakeLLM:
    """Structured answers for plan and evaluate, plain text for the report."""

    def __init__(self):
        self.structured = [
            researcher.QueryPlan(queries=["ai agent market size", "ai agent adoption"]),
            researcher.ResearchAssessment(enough_info=True),
        ]

    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        if self.structured:
            return self.structured.pop(0)
        return AIMessage(content="# AI agents\n\nDemand grew (industry-report-2026.com).")


def test_workspace_streams_the_research_loop(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setattr(web, "_graph", researcher.build_graph(llm=FakeLLM()))
    client = TestClient(web.app)

    assert "Research loop" in client.get("/").text
    assert client.get("/api/info").json()["demo_topics"] == ["ai agent market", "reusable water bottle market"]

    lines = [json.loads(line) for line in client.post("/api/research", json={"topic": "the AI agent market"}).text.splitlines() if line]
    assert [m.get("step") for m in lines[:4]] == ["plan", "search", "evaluate", "write_report"]
    assert lines[0]["pending_queries"] == ["ai agent market size", "ai agent adoption"]
    assert len(lines[1]["notes"]) == 4
    assert lines[3]["report"].startswith("# AI agents")
    assert lines[4]["done"] is True
    assert client.post("/api/research", json={"topic": "x"}).status_code == 422
