"""Research workspace for the research report agent.

Opens a page in the browser where you type a topic and watch the research
loop run: plan the queries, search, judge whether there's enough, search
again if not, then write the report with a source after each claim. Same
graph as research.py.

Run:
    python app.py
"""

import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from agent.llm import DEFAULT_MODEL
from agent.researcher import MAX_ROUNDS, build_graph
from agent.search import _load_topics

load_dotenv()

logger = logging.getLogger("research-agent")
app = FastAPI(title="Research Report Agent")
WEB_DIR = Path(__file__).resolve().parent / "web"
_graph = None


class Topic(BaseModel):
    topic: str = Field(min_length=3, max_length=300)


def stream_research(topic: str):
    """Run the research graph, yielding (step, update) as each node finishes."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    for chunk in _graph.stream({"topic": topic}, stream_mode="updates"):
        yield from chunk.items()


@app.get("/", include_in_schema=False)
def workspace():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/info")
def info():
    live = bool(os.getenv("TAVILY_API_KEY"))
    return {
        "model": os.getenv("LLM_MODEL") or DEFAULT_MODEL,
        "search": "Tavily web search" if live else "Demo search data",
        "demo_topics": [] if live else list(_load_topics()),
        "max_rounds": MAX_ROUNDS,
    }


@app.post("/api/research")
def research(body: Topic):
    """Newline-delimited JSON, one line per finished step, then a done line."""
    def lines():
        started = time.perf_counter()
        try:
            for step, update in stream_research(body.topic.strip()):
                yield json.dumps({"step": step, **update}) + "\n"
            yield json.dumps({"done": True, "seconds": round(time.perf_counter() - started, 1)}) + "\n"
        except Exception as exc:
            logger.exception("Research failed")
            detail = str(exc).splitlines()[0][:200] if str(exc) else ""
            yield json.dumps({"error": f"The research run failed ({type(exc).__name__}: {detail})."}) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import threading
    import webbrowser

    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    uvicorn.run(app, host="127.0.0.1", port=port)
