PIPELINE_VERSION = "v1.0"

# ── verdict palette (judge) ──────────────────────────────────────────
VERDICTS = {
    "supported":        ("Supported",        "#0E6E45", "#E7F5EE"),
    "missing_evidence": ("Incomplete",       "#8A5A00", "#FCF2DC"),
    "inconsistent":     ("Inconsistency","#9E2B25", "#FBEAE8"),
    "unsupported":      ("Failed",  "#9E2B25", "#FBEAE8"),
    "data_insufficient": ("Insufficient data",     "#8A5A00", "#FCF2DC"),
    "unresponsive":     ("Unresponsive",     "#9E2B25", "#FBEAE8"),
}

VERDICT_NOTES = {
    "supported":        "Passes all criteria: the answer is complete, consistent, and traceable to the MLflow experiment.",
    "missing_evidence": "Not available in the MLflow experiment data: {missing}.",
    "inconsistent":     "This response failed consistency review or could not be corrected within the retry limit.",
    "unsupported":      "This response failed MLflow experiment review or could not be corrected within the retry limit.",
    "data_insufficient": "The available MLflow experiment data provided by CRAG pipeline is not sufficient to answer the query: {missing}.",
    "unresponsive":     "No responsive answer could be generated for this query.",
}

VERDICT_LEGEND = [
    ("Supported",        "every value verified against the MLflow experiment"),
    ("Incomplete", "the asked-for information is absent, omitted or never recorded"),
    ("Inconsistency",     "response contradicts the MLflow experiment"),
    ("Failed",      "response contains values absent from the MLflow experiment"),
    ("Insufficient data", "the available MLflow experiment data provided by CRAG pipeline is not sufficient to answer the query"),
    ("Unresponsive",     "response does not address the query"),
]

STATUS_COLORS = {
    "FINISHED": ("#0A8310", "#E4EDFF"),  
    "FAILED":   ("#F80000", "#F6E8FB"),   
    "RUNNING":  ("#0F26F1", "#E0F5FA"),   
    "KILLED":   ("#334155", "#E8EDF3"),   
}

LIFECYCLE_COLORS = {
    "active":   ("#0A8310", "#E4EDFF"),
    "deleted":  ("#941010", "#E8EDF3"),
}


MODEL_STATUS_COLORS = {
    "READY":         ("#0E6E45", "#E7F5EE"), 
    "PENDING":       ("#8A5A00", "#FCF2DC"), 
    "UPLOAD_FAILED": ("#9E2B25", "#FBEAE8"),  
}
 
 
PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Experiment {experiment_id} — documentation</title>
<style>
  :root {{
    --ink: #1A1D21; --muted: #5A6472; --hair: #E2E5E9;
    --label: #2F3E8F; --card: #F7F8FA;
  }}
  * {{ box-sizing: border-box; margin: 0; }}
  body {{
    font-family: "Segoe UI", -apple-system, Arial, sans-serif;
    color: var(--ink); background: #fff;
    max-width: 780px; margin: 0 auto; padding: 44px 40px;
    line-height: 1.55; font-size: 14px;
  }}
  header {{ border-bottom: 2px solid var(--ink); padding-bottom: 16px; }}
  h1 {{ font-size: 21px; font-weight: 600; letter-spacing: -0.01em; }}
  .meta {{ color: var(--muted); font-size: 12.5px; margin-top: 5px; }}
  .stamp {{
    float: right; font-size: 12px; font-weight: 600;
    padding: 5px 14px; border-radius: 3px; letter-spacing: 0.04em;
    color: {v_fg}; background: {v_bg}; border: 1.5px solid {v_fg};
    text-transform: uppercase;
  }}
  section {{ margin-top: 28px; }}
  .label {{
    font-size: 11px; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--label);
    border-bottom: 1px solid var(--hair); padding-bottom: 5px; margin-bottom: 12px;
  }}
  .query {{
    font-size: 15px; padding: 10px 16px;
    border-left: 3px solid var(--label); background: var(--card);
  }}
  .response {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: 15.5px; line-height: 1.7;
  }}
  .note {{
    margin-top: 12px; font-size: 13px; padding: 9px 14px;
    color: {v_fg}; background: {v_bg}; border-left: 3px solid {v_fg};
  }}
  .run {{
    border: 1px solid var(--hair); border-radius: 8px;
    padding: 14px 16px; background: #fff; break-inside: avoid;
    margin-top: 12px;
  }}
  .run h3 {{ font-size: 14.5px; font-weight: 600; display: inline; }}
  .status {{
    float: right; font-size: 10.5px; font-weight: 600; letter-spacing: 0.05em;
    padding: 2px 10px; border-radius: 10px;
  }}
  .idrow {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12.5px; }}
  .idrow td {{ padding: 3px 0; }}
  .idrow td:first-child {{ color: var(--muted); width: 30%; }}
  .idrow td:last-child {{ text-align: right; }}
  .panels {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }}
  .panel {{ border: 1px solid var(--hair); border-radius: 6px; padding: 8px 12px; break-inside: avoid; }}
  .panel .ptitle {{
    font-size: 10.5px; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--label);
  }}
  .panel .anchor {{ color: var(--muted); font-weight: 400; text-transform: none; letter-spacing: 0; }}
  .panel table {{ width: 100%; border-collapse: collapse; margin-top: 5px; font-size: 12px; }}
  .panel td {{ padding: 2.5px 0; border-top: 1px solid var(--hair); }}
  .panel td:first-child {{ color: var(--muted); }}
  .panel td:last-child {{ text-align: right; }}
  .mono {{ font-family: Consolas, Menlo, monospace; font-size: 11px; word-break: break-all; }}
  .none {{ color: var(--muted); font-style: italic; }}
  .chip {{
    display: inline-block; font-size: 10px; font-weight: 600;
    letter-spacing: 0.05em; padding: 2px 9px; border-radius: 10px;
  }}
  .model-block {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12px; }}
  .model-block:first-child {{ margin-top: 0; }}
  .model-block td {{ padding: 6px 0; border-top: 1px solid var(--hair); vertical-align: middle; }}
  .model-block td:first-child {{ color: var(--muted); width: 42%; white-space: nowrap; }}
  .model-block td:last-child {{ text-align: right; }}
  .srclink {{ color: var(--label); text-decoration: none; word-break: break-all; }}
  .srclink:hover {{ text-decoration: underline; }}
  .legend {{
    margin-top: 26px; padding: 10px 14px; background: var(--card);
    border-radius: 6px; font-size: 11.5px; color: var(--muted);
  }}
  .legend b {{ color: var(--ink); }}
  .legend ul {{ margin: 6px 0 0 18px; padding: 0; line-height: 1.8; }}
  .legend li {{ margin: 0; }}
  footer {{
    margin-top: 18px; padding-top: 12px; border-top: 1px solid var(--hair);
    color: var(--muted); font-size: 11.5px;
  }}
  @page {{ size: A4; margin: 18mm 16mm; }}
  @media print {{
    body {{ padding: 0; max-width: none; }}
    .stamp, .note, .status, .chip, .query {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
  @media (max-width: 560px) {{ .panels {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header>
  <span class="stamp">{v_label}</span>
  <h1>Experiment documentation</h1>
  <p class="meta">Experiment {experiment_id} &nbsp;·&nbsp; generated {timestamp} &nbsp;·&nbsp; MLflow Corrective RAG (CRAG) pipeline {version}</p>
</header>
 
<section>
  <p class="label">Query</p>
  <p class="query">{query}</p>
</section>
 
<section>
  <p class="label">Response</p>
  <div class="response">{response}</div>
  {note}
</section>
 
<section>
  <p class="label">Run information</p>
  {cards}
</section>
 
<div class="legend"><b>Verdict reference</b><ul>{legend}</ul></div>
 
<footer>All run identifiers are traceable to the MLflow tracking server. <br>
A <b>SUPPORTED</b> verdict additionally certifies that every value in the response
was verified against the experiment MLflow experiment.</footer>
</body>
</html>"""
 
RUN_CARD = """<div class="run">
  <span class="status" style="color:{s_fg};background:{s_bg}">{status}</span>
  <h3>{run_name}</h3>
  <table class="idrow">
    <tr><td>Run id</td><td class="mono">{run_id}</td></tr>
    <tr><td>Created by</td><td>{user_id}</td></tr>
    <tr><td>Duration</td><td>{duration}</td></tr>
    <tr><td>Lifecycle</td><td><span class="chip" style="color:{l_fg};background:{l_bg}">{lifecycle_stage}</span></td></tr>
  </table>
  <div class="panels">
    <div class="panel">
      <div class="ptitle">Metrics <span class="anchor"></span></div>
      <table>{metrics_rows}</table>
    </div>
    <div class="panel">
      <div class="ptitle">Parameters <span class="anchor"></span></div>
      <table>{params_rows}</table>
    </div>
    <div class="panel">
      <div class="ptitle">Dataset <span class="anchor"></span></div>
      <table>{dataset_rows}</table>
    </div>
    <div class="panel">
      <div class="ptitle">Model</div>
      <table>{model_rows}</table>
    </div>
  </div>
</div>"""

 
VERDICT_BADGE = {
    "supported":         "✅ SUPPORTED",
    "missing_evidence":  "⚠️ INCOMPLETE",
    "data_insufficient": "⚠️ INSUFFICIENT DATA",
    "inconsistent":      "❌ INCONSISTENCY",
    "unsupported":       "❌ FAILED",
    "unresponsive":      "❌ UNRESPONSIVE",
}
 
VERDICT_MD_NOTES = {
    "supported":         "> ✅ Passes all criteria: the answer is complete, consistent, and traceable to the MLflow experiment.\n",
    "missing_evidence":  "> ⚠️ Not available in the MLflow experiment data: {missing}.\n",
    "data_insufficient": "> ⚠️ The available MLLflow experiment data provided by CRAG pipeline is not sufficient to answer this query: {missing}.\n",
    "inconsistent":      "> ⚠️ This response failed consistency review or could not be corrected within the retry limit.\n",
    "unsupported":       "> ⚠️ This response failed MLflow experiment review or could not be corrected within the retry limit.\n",
    "unresponsive":      "> ⚠️ No responsive answer could be generated for this query.\n",
}
 
VERDICT_DESCRIPTIONS = [
    ("Supported",         "every value verified against the MLflow experiment"),
    ("Incomplete",  "the asked-for information is absent, omitted, or never recorded"),
    ("Insufficient data", "the available MLflow experiment data provided by CRAG pipeline is not sufficient to answer the query"),
    ("Inconsistency",      "response contradicts the MLflow experiment"),
    ("Failed",       "response contains values absent from the MLflow experiment"),
    ("Unresponsive",      "response does not address the query"),
]
 
MD_TEMPLATE = """# Experiment documentation — experiment {experiment_id}
 
**Verdict:** {badge}
*Generated {timestamp} · MLflow Corrective RAG (CRAG) pipeline {version}*
 
## Query
 
> {query}
 
## Response
 
{response}
{note}
## Run information
 
{cards}
 
## Verdict reference
 
{legend}
 
---
All run identifiers are traceable to the MLflow tracking server.
A **SUPPORTED** verdict additionally certifies that every value in the response was verified
against the experiment MLflow experiment.
"""
 
RUN_CARD_MD = """### {run_name} — `{status}` · lifecycle: `{lifecycle_stage}`
 
| Field | Value |
|---|---|
| Run id | `{run_id}` |
| Created by | {user_id} |
| Duration | {duration} |
 
**Metrics**
 
{metrics_rows}
 
**Parameters**
 
{params_rows}
 
**Dataset**
 
{dataset_rows}
 
**Model**
 
{model_rows}
"""