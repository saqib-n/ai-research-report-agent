from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import researcher
from agent.search import web_search


def test_demo_topic_returns_findings(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    findings = web_search("size of the AI agent market")
    assert len(findings) == 4
    assert all(f["source"] and f["content"] for f in findings)


def test_unknown_topic_says_so_instead_of_inventing(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    findings = web_search("quantum lawnmowers")
    assert findings[0]["source"] == "no-match"


def test_search_node_skips_duplicate_findings(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    state = {
        "topic": "AI agents",
        "pending_queries": ["ai agent adoption", "ai agents pricing"],
        "searched_queries": [],
        "notes": [],
        "round": 0,
    }
    result = researcher.search_node(state)
    assert len(result["notes"]) == 4  # both queries hit the same 4 demo findings
    assert result["round"] == 1
    assert result["pending_queries"] == []


def test_round_cap_stops_without_calling_the_model():
    state = {"topic": "x", "notes": [], "round": researcher.MAX_ROUNDS, "searched_queries": []}
    assert researcher.evaluate_node(state, llm=None) == {"pending_queries": []}


def test_evaluate_drops_queries_already_searched():
    from tests.fakes import FakeStructuredLLM

    assessment = researcher.ResearchAssessment(enough_info=False, additional_queries=["old query", "new query"])
    state = {"topic": "x", "notes": [], "round": 1, "searched_queries": ["old query"]}
    result = researcher.evaluate_node(state, FakeStructuredLLM(assessment))
    assert result == {"pending_queries": ["new query"]}


def test_routing():
    assert researcher.route_after_evaluate({"pending_queries": ["q"]}) == "search"
    assert researcher.route_after_evaluate({"pending_queries": []}) == "write_report"


def test_report_is_plain_text():
    llm = GenericFakeChatModel(messages=iter([AIMessage(content="# Report")]))
    state = {"topic": "x", "notes": [{"source": "s", "content": "c"}]}
    assert researcher.write_report_node(state, llm) == {"report": "# Report"}
