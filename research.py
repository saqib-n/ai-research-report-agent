"""Run the research agent on a topic and save the report.

Run:
    python research.py "the AI agent market"
    python research.py "the reusable water bottle market"

Those two are the demo topics with mock research data (see
data/sample_research/topics.json), works with no search API key.
Any other topic needs TAVILY_API_KEY set in .env for real results.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

from agent.researcher import research_topic

load_dotenv()

OUTPUT_DIR = Path(__file__).parent / "output"


def main():
    if len(sys.argv) < 2:
        print('Usage: python research.py "topic to research"')
        sys.exit(1)

    topic = " ".join(sys.argv[1:])
    print(f"Researching: {topic}\n")

    result = research_topic(topic)

    print(f"Ran {result['round']} search round(s), {len(result['searched_queries'])} queries, "
          f"{len(result['notes'])} findings gathered.\n")
    print(result["report"])

    OUTPUT_DIR.mkdir(exist_ok=True)
    safe_name = "".join(c if c.isalnum() else "_" for c in topic)[:50]
    output_file = OUTPUT_DIR / f"report_{safe_name}.md"
    output_file.write_text(result["report"], encoding="utf-8")
    print(f"\nSaved to {output_file}")


if __name__ == "__main__":
    main()
