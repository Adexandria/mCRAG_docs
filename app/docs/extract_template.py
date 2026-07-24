import os

from weasyprint import HTML
from app.crag.state import GraphState
from app.docs.response import MIMETYPE
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from langchain_core.documents import Document

from datetime import datetime
from html import escape

import json
from app.retriever.extract_data import get_run_by_id
from template.doc_template import PAGE, RUN_CARD, VERDICTS, VERDICT_NOTES, VERDICT_LEGEND, STATUS_COLORS, PIPELINE_VERSION


def _duration(info: dict) -> str:
    start, end = info.get("start_time"), info.get("end_time")
    if not (start and end):
        return "—"
    try:
        secs = (int(end) - int(start)) / 1000
    except (TypeError, ValueError):
        return "—"
    return f"{secs:.2f} s" if secs < 60 else f"{secs/60:.1f} min"


def _rows(items: dict, mono_keys=()) -> str:
    if not items:
        return '<tr><td colspan="2" class="none">none recorded</td></tr>'
    out = []
    for k, v in items.items():
        v_str = str(v)
        cls = ' class="mono"' if any(m in k.lower() for m in mono_keys) else ""
        if v_str.startswith(("http://", "https://")):
            cell = (f'<a href="{escape(v_str, quote=True)}" class="srclink" '
                    f'target="_blank" rel="noopener">{escape(v_str)}</a>')
        else:
            cell = escape(v_str)
        out.append(f"<tr><td>{escape(str(k))}</td><td{cls}>{cell}</td></tr>")
    return "\n".join(out)


def _suffix_pick(group: dict, wanted: dict) -> dict:
    """Pick fields from a flat group dict by key suffix.
    wanted: {display_label: suffix}"""
    out = {}
    for label, suffix in wanted.items():
        for k, v in group.items():
            if str(k).lower().endswith(suffix):
                out[label] = v
                break
    return out

def _kv(entries: list) -> dict:
    """MLflow's [{'key': k, 'value': v}, ...] → {k: v}"""
    return {e["key"]: e["value"] for e in (entries or [])}


def _first(lst: list) -> dict:
    return (lst or [{}])[0] or {}


def extract_source_url(ds: dict) -> str:
    """MLflow /inputs/dataset_inputs shape → dataset source URL string."""
    source = ds.get("source", "")
    if not source:
        return ""
    try:
        source = json.loads(source)
    except (json.JSONDecodeError, TypeError):
        return str(source)
    
    return source.get("url", "")

def extract_run_info(run: dict) -> str:
    """One run (raw MLflow /runs/get shape) → rendered RUN_CARD html."""
    info = run.get("info", {}) or {}
    data = run.get("data", {}) or {}
    s_fg, s_bg = STATUS_COLORS.get(info.get("status", ""), ("#334155", "#E8EDF3"))

    # data groups: key/value lists → flat dicts
    metrics = _kv(data.get("metrics"))
    params  = _kv(data.get("params"))

    # outputs.model_outputs: [{'model_id': ..., 'step': ...}]
    model_out = _first(run.get("outputs", {}).get("model_outputs"))
    model = {"Model id": model_out.get("model_id", ""),
             "Step": model_out.get("step", "")} if model_out else {}

    # inputs.dataset_inputs: [{'dataset': {...}, 'tags': [...]}]
    ds_input = _first(run.get("inputs", {}).get("dataset_inputs"))
    ds = ds_input.get("dataset", {})
    source = ds.get("source", "")
    
    url = extract_source_url(ds)
     
    dataset = {
        "Name":        ds.get("name", ""),
        "Digest":      ds.get("digest", ""),
        "URI":         url,
        "Schema":      _summarize_schema(ds.get("schema")),
        "Context":     _kv(ds_input.get("tags")).get("mlflow.data.context", ""),
    }
    dataset = {k: v for k, v in dataset.items() if v}     # show only present fields

    run_id = str(info.get("run_id") or info.get("run_uuid") or "—")
    return RUN_CARD.format(
        run_name=escape(str(info.get("run_name") or run_id)),
        status=escape(str(info.get("status") or "UNKNOWN")),
        s_fg=s_fg, s_bg=s_bg,
        run_id=escape(run_id),
        user_id=escape(str(info.get("user_id") or "—")),
        duration=_duration(info),
        metrics_rows=_rows(metrics),
        params_rows=_rows(params),
        model_rows=_rows(model, mono_keys=("model id",)),
        dataset_rows=_rows(dataset, mono_keys=("digest",)),
    )


def _summarize_schema(schema_str) -> str:
    """MLflow stores schema as a JSON string → '5 columns' summary for the card."""
    if not schema_str:
        return ""
    try:
        cols = json.loads(schema_str).get("mlflow_colspec", [])
        return f"{len(cols)} columns"
    except (json.JSONDecodeError, TypeError):
        return ""
  


def render_document_html(state: dict) -> str:
    """
    state: final graph state (query, generation, grading_result, experiment_id)
    """
    answer = state["generation"]
    judge = state["grading_result"]

    aggregate = state.get("aggregates", {})


    answer = answer if answer else "No answer generated"
    evidence_ids = state.get("evidence_ids", [])

    v_label, v_fg, v_bg = VERDICTS.get(judge.verdict, VERDICTS["unsupported"])
    note_text = VERDICT_NOTES.get(judge.verdict, "").format(
        missing=escape(", ".join(judge.missing_evidence)))
    note = f'<p class="note">{note_text}</p>' if note_text else ""

    cards = []
    if judge.related_run_ids:                                  
      for eid in judge.related_run_ids:              
                run_data = get_run_by_id(eid) or {}
                run = run_data.get("run", {})
                if run:
                  cards.append(extract_run_info(run))
    elif evidence_ids:                          
      for eid in evidence_ids:
        if eid in aggregate.get("runs", {}):
            run_data = get_run_by_id(eid) or {}
            run = run_data.get("run", {})
            if run:
                cards.append(extract_run_info(run))
      
        
    legend = "\n".join(
        f"<li><b>{name}</b>: {desc}</li>" for name, desc in VERDICT_LEGEND)

    return PAGE.format(
        experiment_id=escape(str(state["experiment_id"])),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        version=PIPELINE_VERSION,
        v_label=v_label, v_fg=v_fg, v_bg=v_bg,
        query=escape(state["query"]),
        response=escape(answer),
        note=note,
        cards="\n".join(cards) if cards
              else '<p class="none">No specific runs cited in this response.</p>',
        legend=legend,
    )


def generate_documentation(state: GraphState, output_dir: str, mimetype: str):
    """
    Generates documentation by extracting the template and appending the provided data.
    Args:
        state (GraphState): The graph state containing the judge response and other information.
        output_dir (str): The directory where the generated documentation will be saved.
        mimetype (str): The MIME type of the documentation to be generated.
    """
    # template = extract_template()
    # print(f"Template extracted from {TEMPLATE_PATH}.")

    # data = extract_template_response(state)
    # documentation = append_data_to_template(template, data.model_dump())

    documentation = render_document_html(state)

    base_dir = os.path.join(output_dir, f"experiment_{state['experiment_id']}")
    os.makedirs(base_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    output_path = os.path.join(base_dir, f"documentation_{timestamp}.{mimetype}")

    if mimetype == MIMETYPE.PDF:
        HTML(string=documentation).write_pdf(output_path)
        
    elif mimetype == MIMETYPE.MARKDOWN:
        soup = BeautifulSoup(documentation, "html.parser")
        for tag in soup(["style", "script", "head", "footer"]):
            tag.decompose()  
        markdown = md(str(soup), heading_style="ATX")
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(markdown)
            
    else:
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(documentation)

    print(f"Documentation generated at {output_path} in {mimetype} format.")

if __name__ == "__main__":

    """Test input: final graph state for the best-metric query (experiment 2)."""

    inputs = {
    "query": "Extract the run with the best metric?",
    "experiment_id": "2",
    "retry_count": 0,
    "generation": "Run fearless-hen-13 achieved the best metric with an accuracy of 1.0",
    "grading_result": {
        "verdict": "supported",
        "reason": (
            "The answer correctly identifies run 'fearless-hen-13' as achieving "
            "the best metric with an accuracy of 1.0. The evidence shows this run "
            "has an accuracy of 1.0, which is higher than the other run's accuracy "
            "of 0.9, making it the best. The run name and accuracy value both "
            "appear in the evidence"
        ),
        "related_run_ids": ["992435a3093c4c508ea95bbaad49a2c2"],
        "evidence_ids": ["992435a3093c4c508ea95bbaad49a2c2", "run_name", "accuracy"],
        "missing_evidence": [],
    },
    "aggregates": {
        "40c777ecfda846e3b42b3daf01a0247c": {
            "info": {
                "artifact_uri": "mlflow-artifacts:/2/40c777ecfda846e3b42b3daf01a0247c/artifacts",
                "experiment_id": "2",
                "lifecycle_stage": "active",
                "run_id": "40c777ecfda846e3b42b3daf01a0247c",
                "run_uuid": "40c777ecfda846e3b42b3daf01a0247c",
                "run_name": "unruly-penguin-358",
                "user_id": "adeol",
                "status": "FINISHED",
                "start_time": 1784061874763,
                "end_time": 1784061887114,
            },
            "metrics": {
                "accuracy": 0.9,
                "precision": 0.9013888888888889,
                "recall": 0.9,
                "f1_score": 0.8992327365728899,
            },
            "params": {"max_iter": "100"},
            "tags": {},
            "inputs": {},
            "outputs": {},
        },
        "992435a3093c4c508ea95bbaad49a2c2": {
            "info": {
                "artifact_uri": "mlflow-artifacts:/2/992435a3093c4c508ea95bbaad49a2c2/artifacts",
                "experiment_id": "2",
                "lifecycle_stage": "active",
                "run_id": "992435a3093c4c508ea95bbaad49a2c2",
                "run_uuid": "992435a3093c4c508ea95bbaad49a2c2",
                "run_name": "fearless-hen-13",
                "user_id": "adeol",
                "status": "FINISHED",
                "start_time": 1784061887177,
                "end_time": 1784061896949,
            },
            "metrics": {
                "accuracy": 1.0,
                "precision": 1.0,
                "recall": 1.0,
                "f1_score": 1.0,
            },
            "params": {
                "n_estimators": "100",
                "max_depth": "5",
                "random_state": "42",
            },
            "tags": {},
            "inputs": {},
            "outputs": {},
        },
    },
    "grading_report": {
        "total_retrieved": 4,
        "correct": 4,
        "discarded": [],
        "proceed": True,
        "runs_found": [
            "40c777ecfda846e3b42b3daf01a0247c",
            "992435a3093c4c508ea95bbaad49a2c2",
        ],
        "groups_per_run": {
            "40c777ecfda846e3b42b3daf01a0247c": ["info", "metrics", "params"],
            "992435a3093c4c508ea95bbaad49a2c2": ["info", "metrics", "params"],
        },
        "section_status": {
            "summary": {
                "status": "ok",
                "supporting_runs": [
                    "40c777ecfda846e3b42b3daf01a0247c",
                    "992435a3093c4c508ea95bbaad49a2c2",
                ],
            },
            "performance": {
                "status": "ok",
                "supporting_runs": [
                    "40c777ecfda846e3b42b3daf01a0247c",
                    "992435a3093c4c508ea95bbaad49a2c2",
                ],
            },
            "configuration": {
                "status": "ok",
                "supporting_runs": [
                    "40c777ecfda846e3b42b3daf01a0247c",
                    "992435a3093c4c508ea95bbaad49a2c2",
                ],
            },
            "lineage": {"status": "partial", "missing": ["inputs", "outputs"]},
            "metadata": {"status": "partial", "missing": ["tags"]},
        },
    },
    "documents": [
        Document(
            id="df3a067f-e281-48fa-87df-7f5914087a2e",
            metadata={
                "run_id": "40c777ecfda846e3b42b3daf01a0247c",
                "run_name": "unruly-penguin-358",
                "experiment_id": "2",
                "status": "FINISHED",
                "user_id": "adeol",
                "start_time": 1784061874763,
                "end_time": 1784061887114,
                "chunk_index": 1,
            },
            page_content=(
                "[('info.lifecycle_stage', 'active'), "
                "('info.run_id', '40c777ecfda846e3b42b3daf01a0247c'), "
                "('data.metrics.accuracy', 0.9), "
                "('data.metrics.precision', 0.9013888888888889), "
                "('data.metrics.recall', 0.9), "
                "('data.metrics.f1_score', 0.8992327365728899), "
                "('data.params.max_iter', '100')]"
            ),
        ),
        Document(
            id="f9c43f9a-25a9-42bc-a6ab-cb461068006a",
            metadata={
                "run_id": "992435a3093c4c508ea95bbaad49a2c2",
                "run_name": "fearless-hen-13",
                "experiment_id": "2",
                "status": "FINISHED",
                "user_id": "adeol",
                "start_time": 1784061887177,
                "end_time": 1784061896949,
                "chunk_index": 1,
            },
            page_content=(
                "[('info.lifecycle_stage', 'active'), "
                "('info.run_id', '992435a3093c4c508ea95bbaad49a2c2'), "
                "('data.metrics.accuracy', 1.0), "
                "('data.metrics.precision', 1.0), "
                "('data.metrics.recall', 1.0), "
                "('data.metrics.f1_score', 1.0), "
                "('data.params.n_estimators', '100'), "
                "('data.params.max_depth', '5'), "
                "('data.params.random_state', '42')]"
            ),
        ),
        Document(
            id="176c88cf-bce3-451d-8280-c7e3c5046b6a",
            metadata={
                "run_id": "40c777ecfda846e3b42b3daf01a0247c",
                "run_name": "unruly-penguin-358",
                "experiment_id": "2",
                "status": "FINISHED",
                "user_id": "adeol",
                "start_time": 1784061874763,
                "end_time": 1784061887114,
                "chunk_index": 0,
            },
            page_content=(
                "[('info.run_uuid', '40c777ecfda846e3b42b3daf01a0247c'), "
                "('info.experiment_id', '2'), "
                "('info.run_name', 'unruly-penguin-358'), "
                "('info.user_id', 'adeol'), "
                "('info.status', 'FINISHED'), "
                "('info.start_time', 1784061874763), "
                "('info.end_time', 1784061887114), "
                "('info.artifact_uri', 'mlflow-artifacts:/2/40c777ecfda846e3b42b3daf01a0247c/artifacts')]"
            ),
        ),
        Document(
            id="976f32dc-70d8-4c68-abeb-a24e67cac515",
            metadata={
                "run_id": "992435a3093c4c508ea95bbaad49a2c2",
                "run_name": "fearless-hen-13",
                "experiment_id": "2",
                "status": "FINISHED",
                "user_id": "adeol",
                "start_time": 1784061887177,
                "end_time": 1784061896949,
                "chunk_index": 0,
            },
            page_content=(
                "[('info.run_uuid', '992435a3093c4c508ea95bbaad49a2c2'), "
                "('info.experiment_id', '2'), "
                "('info.run_name', 'fearless-hen-13'), "
                "('info.user_id', 'adeol'), "
                "('info.status', 'FINISHED'), "
                "('info.start_time', 1784061887177), "
                "('info.end_time', 1784061896949), "
                "('info.artifact_uri', 'mlflow-artifacts:/2/992435a3093c4c508ea95bbaad49a2c2/artifacts')]"
            ),
        ),
    ],
}
    print("Generating documentation...")
    generate_documentation(inputs, "output", MIMETYPE.MARKDOWN)