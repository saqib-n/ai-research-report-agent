# Research Report Agent

## Portfolio entry

A research agent that plans its searches, gathers findings, then evaluates whether it actually has enough to write from and runs a second round if something important is missing. Only then does it write a report with every claim cited. The evaluation step is a real branch in the graph, not a fixed number of searches, and it's capped so it can't run away.

**Stack:** Python, LangGraph, Pydantic, Tavily

---

## One search is not research

The standard build here is search, summarise the top three results, return. Fast, cheap, and thin in a way that stays invisible until someone who knows the subject reads it.

Teams who actually need this, competitor analysis, market summaries, need something closer to what a person does. Search, read, notice a gap, search again for the specific missing thing.

## The loop

```
plan ──▶ search ──▶ evaluate ──┬──▶ gap found ──▶ back to search
                               │
                               └──▶ enough ──▶ write
```

After round one the model reads its own notes against the topic and makes a call: is something important missing, and what query would fill it?

This is the only one of my agents that loops conditionally. The others route once or run a fixed sequence. Here, one round versus two is a judgment the agent makes about its own work. Capped at two, because unbounded self-directed search is a cost problem waiting to happen.

## A decision about the demo data

I could have generated plausible search results for any topic so the demo worked on anything.

I didn't. A research tool that invents sources when it can't find real ones is the exact failure this exists to prevent, and shipping that as the demo path would be strange. Two topics have proper mock research. Everything else gets told there's no data without a Tavily key.

## My part

The loop design, the round cap, structured output at each decision point, and a fallback that's honest about what it doesn't know.
