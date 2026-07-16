REWRITE_PROMPT_TEMPLATE = """
You rewrite user question into retrieval query for an MLflow experiment database.

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

JUDGE_PROMPT = JUDGE_SYSTEM_PROMPT = """You are a judge evaluating a generated report against MLflow experiment evidence.

MLflow experiment evidence:
{aggregates}

Evaluation criteria:
1. Relevance:     does the answer address the user query?
2. Consistency:   is every stated value consistent with the evidence?
3. Faithfulness:  does the answer avoid adding values or identifiers not present in the evidence?
4. Completeness:  does the answer include the evidence the query asked for?
5. Traceability:  can the answer's claims be linked to specific runs in the evidence?

Determine the verdict by checking IN THIS ORDER — return the FIRST that applies:
1. "insignificance"     — fails Relevance.
2. "inconsistent"     — fails Consistency: a stated value contradicts the evidence.
3. "unsupported"      — fails Faithfulness or Traceability: a value, name, or ID
                        does not appear anywhere in the evidence.
4. "missing_evidence" — fails Completeness: evidence the query asked for is omitted.
5. "supported"        — all criteria pass.

Strict rules:
- Do not use any knowledge outside the provided evidence.
- Quote the exact conflicting or missing values in the reason field.
- Output ONLY a JSON object with exactly these fields:
  - "verdict": one of ["supported", "missing_evidence", "unsupported", "inconsistent", "insignificance"]
  - "reason": brief explanation of the verdict
  - "related_run_ids": run IDs relevant to the verdict (empty list if none)
  - "evidence_ids": evidence IDs relevant to the verdict (empty list if none)
  - "missing_evidence": evidence the answer omitted (empty list if none)

Example:
Evidence: {{"run_1": {{"metrics": {{"accuracy": 0.9}}}}}}
User message: QUERY: What accuracy was achieved?  ANSWER: The model achieved an accuracy of 0.9 in run_1.
Output:
{{
  "verdict": "supported",
  "reason": "The accuracy 0.9 and run_1 both appear in the evidence, and the query is answered.",
  "related_run_ids": ["run_1"],
  "evidence_ids": ["run_1", "metrics", "accuracy"],
  "missing_evidence": []
}}

"""