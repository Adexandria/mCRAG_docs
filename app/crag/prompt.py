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
                  An answer that honestly states the asked-for information was not recorded PASSES relevance.
2. Consistency:   is every stated value consistent with the evidence?
3. Faithfulness:  does the answer avoid adding values or identifiers not present in the evidence?
4. Completeness:  does the answer include the evidence the query asked for?
5. Traceability:  can the answer's claims be linked to specific runs in the evidence?
 
Determine the verdict by checking IN THIS ORDER — return the FIRST that applies:
1. "unresponsive"      — fails Relevance: the answer does not address the query.
2. "data_insufficient" — the answer correctly states that the evidence lacks what the query explicitly asked for (e.g., missing metrics or properties). Focus strictly on whether the specific information requested by the query is absent from the evidence. If the query did not ask for run IDs or run names, do not penalize or trigger verdicts based on their absence; judge solely on whether the requested target data is missing.
3. "inconsistent"      — fails Consistency: a stated value contradicts the evidence.
4. "unsupported"       — fails Faithfulness or Traceability: a value, name, or ID does not appear anywhere in the evidence.
5. "missing_evidence"  — fails Completeness: the answer omits asked-for information that is present in the evidence and includes any missing values.
6. "supported"         — all checks above pass: the answer addresses the query, every value/metric it states appears in the evidence, the requested data actually exists in the evidence, and it does not have any missing evidence.
 
Strict rules:
- OVERRIDE RULE: If the query asks for performance metrics (like accuracy, loss, score) that were not logged or recorded, and the answer reports that no metrics/results were recorded, the verdict MUST ALWAYS be "data_insufficient". 
- If the query does NOT ask for run IDs or run names, evaluate `data_insufficient` purely based on the absence of the requested target information (e.g., metrics), regardless of whether run names or IDs are mentioned in the answer.
- The answer MAY draw simple conclusions from the evidence (e.g. identifying the best or latest run). Judge such conclusions ONLY by whether the values and identifiers they cite exist in the evidence.
- Do NOT perform comparisons or calculations yourself. Do not determine which run is best or latest. Only check whether stated values exist in the evidence.
- Do not use any knowledge outside the provided evidence.
- Quote the exact conflicting or missing values in the reason field.
- Output ONLY a JSON object with exactly these fields:
  - "verdict": one of ["supported", "missing_evidence", "unsupported", "inconsistent", "unresponsive", "data_insufficient"]
  - "reason": brief explanation of the verdict
  - "related_run_ids": run IDs relevant to the verdict (empty list if none)
  - "missing_evidence": evidence the query asked for that is absent or omitted (empty list if none)
 
Example 1:
User message: QUERY: What accuracy was achieved?
ANSWER: The model achieved an accuracy of 0.9 in run_1.
MLflow experiment evidence: {"run_1": {"metrics": {"accuracy": 0.9}}}
Output:
{
  "verdict": "supported",
  "reason": "The accuracy 0.9 and run_1 both appear in the evidence, and the query is answered with existing data.",
  "related_run_ids": ["run_1"],
  "missing_evidence": []
}
 
Example 2:
User message: QUERY: What accuracy was achieved?
ANSWER: No results were recorded in this experiment. Two runs finished successfully (vaunted-eel-701 and flawless-fox-692), but neither logged any metrics to compare performance.
MLflow experiment evidence: {"vaunted-eel-701": {"metrics": {}}, "flawless-fox-692": {"metrics": {}}}
Output:
{
  "verdict": "data_insufficient",
  "reason": "The query asks for accuracy, but the evidence contains no metric values; the answer correctly notes that no metrics were logged.",
  "related_run_ids": ["vaunted-eel-701", "flawless-fox-692"],
  "missing_evidence": ["accuracy"]
}
 
Example 3:
User message: QUERY: What accuracy was achieved?
ANSWER: The experiment used max_iter=100 and random_state=42 across its runs.
MLflow experiment evidence: {"run_1": {"metrics": {"accuracy": 0.9}, "params": {"max_iter": "100", "random_state": "42"}}}
Output:
{
  "verdict": "unresponsive",
  "reason": "The query asks about accuracy; the answer discusses parameters and never addresses accuracy, even though the cited values exist in the evidence.",
  "related_run_ids": [],
  "missing_evidence": ["accuracy"]
}
"""