"""LangGraph research loop: plan queries, search, decide if there's enough
to write from, search again if not, then write the report.

This is the one project in this folder that actually loops. The other
LangGraph pipelines here either route to one specialist or run a fixed
sequence of steps, this one keeps searching, up to a round limit, until
the model judges it has enough to write a real report instead of a
one-search-and-done summary.
"""

from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from agent.llm import get_llm
from agent.search import web_search

MAX_ROUNDS = 2


class QueryPlan(BaseModel):
    queries: list[str] = Field(description="2-3 specific search queries to research this topic")


class ResearchAssessment(BaseModel):
    enough_info: bool = Field(description="True if there's enough gathered to write a solid report")
    additional_queries: list[str] = Field(
        default_factory=list,
        description="If not enough info, 1-2 new queries that would fill the gap. Empty if enough_info is True.",
    )


class ResearchState(TypedDict):
    topic: str
    pending_queries: list[str]
    searched_queries: list[str]
    notes: list[dict]
    round: int
    report: str


def plan_node(state: ResearchState, llm) -> dict:
    system = SystemMessage(content="Plan the first round of research for this topic.")
    human = HumanMessage(content=f"Topic: {state['topic']}")
    structured_llm = llm.with_structured_output(QueryPlan)
    result = structured_llm.invoke([system, human])
    return {"pending_queries": result.queries, "round": 0, "notes": [], "searched_queries": []}


def search_node(state: ResearchState) -> dict:
    # Different queries often return the same source (the demo data always
    # does), so skip anything already in the notes instead of feeding the
    # writer the same finding several times.
    new_notes = list(state["notes"])
    seen = {(n["source"], n["content"]) for n in new_notes}
    for query in state["pending_queries"]:
        for finding in web_search(query):
            key = (finding["source"], finding["content"])
            if key in seen:
                continue
            seen.add(key)
            new_notes.append({"query": query, **finding})

    return {
        "notes": new_notes,
        "searched_queries": state["searched_queries"] + state["pending_queries"],
        "round": state["round"] + 1,
        "pending_queries": [],
    }


def evaluate_node(state: ResearchState, llm) -> dict:
    if state["round"] >= MAX_ROUNDS:
        return {"pending_queries": []}

    notes_text = "\n".join(f"- ({n['source']}) {n['content']}" for n in state["notes"])
    system = SystemMessage(content=(
        "You're deciding whether there's enough research gathered to write a solid report "
        "on the topic, or whether another round of searching is needed to fill a real gap. "
        "Don't ask for more searches just to be thorough, only if something important is missing."
    ))
    human = HumanMessage(content=f"Topic: {state['topic']}\n\nGathered so far:\n{notes_text}")
    structured_llm = llm.with_structured_output(ResearchAssessment)
    result = structured_llm.invoke([system, human])

    if result.enough_info:
        return {"pending_queries": []}

    new_queries = [q for q in result.additional_queries if q not in state["searched_queries"]]
    return {"pending_queries": new_queries}


def write_report_node(state: ResearchState, llm) -> dict:
    notes_text = "\n".join(f"- ({n['source']}) {n['content']}" for n in state["notes"])
    system = SystemMessage(content=(
        "Write a structured research report in markdown from these notes. Include a short "
        "summary at the top, then a few sections with findings. Cite the source in "
        "parentheses after each claim. Be honest if the notes are thin on some point, "
        "don't pad with generic statements not supported by the notes."
    ))
    human = HumanMessage(content=f"Topic: {state['topic']}\n\nResearch notes:\n{notes_text}")
    response = llm.invoke([system, human])
    return {"report": response.text}


def route_after_evaluate(state: ResearchState) -> str:
    return "search" if state["pending_queries"] else "write_report"


def build_graph(model: str | None = None, llm=None):
    llm = llm or get_llm(model)

    graph = StateGraph(ResearchState)
    graph.add_node("plan", lambda state: plan_node(state, llm))
    graph.add_node("search", search_node)
    graph.add_node("evaluate", lambda state: evaluate_node(state, llm))
    graph.add_node("write_report", lambda state: write_report_node(state, llm))

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "evaluate")
    graph.add_conditional_edges("evaluate", route_after_evaluate, {"search": "search", "write_report": "write_report"})
    graph.add_edge("write_report", END)

    return graph.compile()


def research_topic(topic: str, model: str | None = None) -> dict:
    graph = build_graph(model)
    return graph.invoke({"topic": topic})
