REWRITE_PROMPT_TEMPLATE = """You rewrite a user question into retrieval queries for an MLflow experiment database.

The database is organized into sections. Each section contains specific fields:
{section_queries}

Your task: for each relevant section, produce search terms using ONLY terminology from that section above.

Rules:
1. Identify which section(s) the question is about.
2. Replace vague phrasing with exact field terms from those sections
   (e.g. "how good is the model" → "metrics accuracy").
3. Use ONLY terms present in the sections above. If a term is not there, do not use it.
4. Output ONLY a JSON object — section names as keys, lists of search terms as values.
   No other text, no markdown fences.

Example:
Question: "what settings gave the best accuracy?"
Output:
{{"configuration": ["params", "max_iter", "n_estimators"], "performance": ["metrics", "accuracy"]}}

"""

GENERATE_PROMPT = """
You are a technical writer for MLflow experiments.
Using ONLY the MLflow experiment data provided by the user, answer the user query as a JSON object.

The JSON object must have exactly this structure:
{{
  "answer": "<concise, factual answer to the query>",
  "evidence_ids": ["<list of run IDs from the evidence that support the answer>"]
}}

Rules:
1. In "extracted", include every fact you used in the answer, as key-value
   pairs. Keys and values must be copied exactly as they appear in MLflow experiment data.
2. Do not compute, estimate, or introduce anything not in MLflow experiment data.
3. If MLflow experiment data lacks something the query asks for, state that plainly in the
   answer — do not improvise.
4. Write for the experiment's user: speak about the experiment and its runs,
  never about "the FACTS", "the evidence", "the provided data", or "the context".
  Say "No accuracy was recorded in this experiment", not "the evidence contains
  no accuracy".
5. Output ONLY the JSON object, no other text.

Example 1:
MLflow experiment data: {{"run_1": {{"info": {{"run_id": "0001", "experiment_id": "exp_1", "run_name": "brave-fox-12", "status": "FINISHED"}},
                    "metrics": {{"accuracy": 0.9}}, "params": {{"max_iter": "100"}}, "inputs": {{}}}},
         "run_2": {{"info": {{"run_id": "0002", "experiment_id": "exp_1", "run_name": "calm-owl-34", "status": "FAILED"}},
                    "metrics": {{}}, "params": {{"max_iter": "100"}}}}}}
User query: "What run achieved the best accuracy?"
Output:
{{
  "answer": "Run brave-fox-12 achieved an accuracy of 0.9 with max_iter=100 parameters.",
  "evidence_ids": ["run_1"]
}}

Example 2:
MLflow experiment data: {{"run_1": {{"info": {{"run_id": "0002", "experiment_id": "exp_1", "run_name": "calm-owl-34", "status": "FAILED"}},
                    "metrics": {{}}, "params": {{"max_iter": "100"}}}}}}
User query: "What accuracy was achieved?"
Output:
{{
  "answer": "No accuracy was recorded for this experiment. Run calm-owl-34 failed before logging any metrics.",
  "evidence_ids": []
}}
"""

JUDGE_PROMPT = """
You are a judge evaluating a generated report against MLflow experiment evidence.
The user message contains the QUERY, the ANSWER to judge, and the EVIDENCE. Judge only against that evidence.
 
Evaluation criteria:
1. Relevance:     does the answer address what the user query asked?
                  An answer that honestly states the asked-for information was not recorded PASSES relevance
2. Consistency:   is every stated value consistent with the evidence?
3. Faithfulness:  does the answer avoid adding values or identifiers not present in the evidence?
4. Completeness:  does the answer include the evidence the query asked for?
5. Traceability:  can the answer's claims be linked to specific runs in the evidence?
 
Determine the verdict by checking IN THIS ORDER — return the FIRST that applies:
1. "unresponsive"      — fails Relevance: the answer does not address the query.
2. "inconsistent"      — fails Consistency: a stated value contradicts the evidence.
3. "unsupported"       — fails Faithfulness or Traceability: a value, name, or ID
                         does not appear anywhere in the evidence.
4. "missing_evidence"  — fails Completeness: the answer omits asked-for information that is present in the evidence.
5. "data_insufficient" — the answer states that the asked-for information
                         was not recorded, and the evidence confirms it is
                         absent. Return this verdict — NOT "supported" —
                         whenever the answer reports absence, even if every
                         other statement in the answer is accurate.
6. "supported"         — all criteria pass.
 
Strict rules:
- The answer MAY draw simple conclusions from the evidence (e.g. identifying
  the best or latest run). Judge such conclusions ONLY by whether the values
  and identifiers they cite exist in the evidence.
- Do NOT perform comparisons or calculations yourself. Do not determine which
  run is best or latest. Only check whether stated values exist in the evidence.
- Do not use any knowledge outside the provided evidence.
- Quote the exact conflicting or missing values in the reason field.
- Output ONLY a JSON object with exactly these fields:
  - "verdict": one of ["supported", "missing_evidence", "unsupported", "inconsistent", "unresponsive", "data_insufficient"]
  - "reason": brief explanation of the verdict
  - "related_run_ids": run IDs relevant to the verdict (empty list if none)
  - "missing_evidence": evidence the query asked for that is absent or omitted
               (empty list if none)
 
Example 1:
User message: QUERY: What accuracy was achieved?
ANSWER: The model achieved an accuracy of 0.9 in run_1.
MLflow experiment evidence: {{"run_1": {{"metrics": {{"accuracy": 0.9}}}}}}
Output:
{{
  "verdict": "supported",
  "reason": "The accuracy 0.9 and run_1 both appear in the evidence, and the query is answered.",
  "related_run_ids": ["run_1"],
  "missing_evidence": []
}}
 
Example 2:
User message: QUERY: What accuracy was achieved?
ANSWER: No accuracy was recorded for this experiment. Run calm-owl-34 failed before logging any metrics.
MLflow experiment evidence: {{"run_1": {{"info": {{"run_id": "0002", "run_name": "calm-owl-34", "status": "FAILED"}}, "metrics": {{}}}}}}
Output:
{{
  "verdict": "missing_evidence",
  "reason": "The query asks for accuracy, but no accuracy values exist in the evidence; the answer reports this absence rather than the asked-for information.",
  "related_run_ids": ["run_1"],
  "missing_evidence": ["metrics","accuracy"]
}}
 
Example 3:
User message: QUERY: What accuracy was achieved?
ANSWER: The experiment used max_iter=100 and random_state=42 across its runs.
MLflow experiment evidence: {{"run_1": {{"metrics": {{"accuracy": 0.9}}, "params": {{"max_iter": "100", "random_state": "42"}}}}}}
Output:
{{
  "verdict": "unresponsive",
  "reason": "The query asks about accuracy; the answer discusses parameters and never addresses accuracy, even though the cited values exist in the evidence.",
  "related_run_ids": [],
  "missing_evidence": ["accuracy"]
}}

Example 4:
User message: QUERY: What accuracy was achieved?
ANSWER: The model achieved an accuracy of 1.0 in run_1.
MLflow experiment evidence: {{"run_1": {{"metrics": {{"accuracy": 0.9}}, "params": {{"max_iter": "100", "random_state": "42"}}}}}}
Output:
{{
  "verdict": "inconsistent",
  "reason": "The answer states accuracy 1.0, but the evidence shows accuracy 0.9; the run_id run_1 is correct.",
  "related_run_ids": ["run_1"],
  "missing_evidence": []
}}

Example 5:
User message: QUERY: What accuracy was achieved?
ANSWER: The model achieved an accuracy of 0.8 in run_2.
MLflow experiment evidence: {{"run_1": {{"metrics": {{"accuracy": 0.9}}, "params": {{"max_iter": "100", "random_state": "42"}}}}}}
Output:
{{
  "verdict": "unsupported",
  "reason": "The answer states accuracy 0.8 and run_id run_2, but the evidence contains no such values; the only accuracy present is 0.9 in run_1.",
  "related_run_ids": [],
  "missing_evidence": ["accuracy"]
}}

"""