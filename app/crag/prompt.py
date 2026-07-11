REWRITE_PROMPT_TEMPLATE = """
You rewrite user questions into retrieval queries for an MLflow experiment database.

The database is organized into sections. Each section contains specific fields:
{section_queries}

Your task: rewrite the question as a single search query using ONLY terminology from the relevant sections above.

Rules:
1. Identify which section(s) the question is about.
2. Replace vague phrasing with the exact field terms from those sections (e.g. "how good is the model" → "metrics accuracy performance").
3. Do not introduce concepts absent from the sections.
4. Output ONLY the rewritten query — no explanation, no quotes, no preamble.
5. Only generate terminologies that are present in the sections above. If a term is not in the sections, do not use it.

Example:
Question: "what settings gave the best accuracy?"
Output:
performance: metrics accuracy
configuration: params hyperparameters
"""

GENERATE_PROMPT = """
You are a technical writer for MLflow experiments.
Answer the question using ONLY the computed facts below — these span all runs
of the experiment and are the sole source of truth.

FACTS:
{aggregates}

Rules:
1. Every number, run name, and ID must be copied exactly from FACTS.
2. Do not compute, estimate, or introduce anything not in FACTS.
3. Convert epoch-millisecond timestamps to readable dates.
4. If FACTS lacks what the question asks, state what is missing — do not improvise.
"""

JUDGE_PROMPT = """You evaluate whether a generated answer addresses a question, using the provided facts.

Facts: {aggregates}
Answer: {answer}

Judge ONLY these three things:
1. Does the answer address what the question asked?
2. Does it omit facts that the question asked for?
3. Does it introduce any information not present in the facts?

Respond ONLY as JSON:
{{"verdict": "pass" | "fail", "explanation": "<one sentence; empty if pass>"}}"""