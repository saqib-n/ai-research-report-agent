"""Web search, real if a Tavily key is set, otherwise a small local
fallback keyed by topic so the multi-round research loop can still be
demoed and tested with zero search API key.

The fallback only covers two demo topics (see data/sample_research/topics.json),
for anything else it says so honestly rather than inventing findings.
"""

import json
import os
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_research"


def _load_topics() -> dict:
    with open(DATA_DIR / "topics.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _mock_search(query: str) -> list[dict]:
    topics = _load_topics()
    query_lower = query.lower()

    best_topic = None
    best_score = 0
    for topic_name, topic_data in topics.items():
        score = sum(1 for kw in topic_data["keywords"] if kw in query_lower)
        if score > best_score:
            best_score = score
            best_topic = topic_data

    if best_topic is None:
        return [{
            "source": "no-match",
            "content": (
                f"No mock research data available for '{query}'. Set TAVILY_API_KEY "
                "for real web search, or try one of the demo topics: AI agent market, "
                "reusable water bottle market."
            ),
        }]

    return best_topic["findings"]


def web_search(query: str) -> list[dict]:
    """Returns a list of {source, content} dicts."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return _mock_search(query)

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        result = client.search(query=query, max_results=4)
        findings = [
            {"source": item.get("url", "unknown"), "content": item.get("content", "")}
            for item in result.get("results", [])
        ]
        return findings if findings else _mock_search(query)
    except Exception as exc:
        # Say so instead of failing silently, otherwise a bad key looks like
        # "no data for this topic".
        print(f"Tavily search failed ({exc}), using local demo data instead.", file=sys.stderr)
        return _mock_search(query)
