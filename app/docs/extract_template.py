import os

from weasyprint import HTML
from app.crag.state import GraphState
from app.docs.response import MIMETYPE

from datetime import datetime
from html import escape

import json
from app.retriever.extract_data import get_model_by_id, get_run_by_id
from template.doc_template import (
MODEL_STATUS_COLORS, 
PAGE_TEMPLATE, 
RUN_CARD,
RUN_CARD_MD, 
VERDICTS,
VERDICT_NOTES,
VERDICT_LEGEND,
STATUS_COLORS, 
PIPELINE_VERSION, 
LIFECYCLE_COLORS, 
VERDICT_MD_NOTES,
VERDICT_DESCRIPTIONS,
VERDICT_BADGE,
MD_TEMPLATE)

def _s(v) -> str:
    return str(v) if v is not None else ""

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

def _md_rows(items: dict) -> str:
    """Full markdown table (header + separator + rows), not just body rows —
    without the header/separator, most renderers show plain pipe-text instead
    of a table."""
    header = "| Field | Value |\n|---|---|"
    if not items:
        return f"{header}\n| — | *none recorded* |"
    return header + "\n" + "\n".join(f"| {k} | {_s(v)} |" for k, v in items.items())

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


def _extract_source_url(ds: dict) -> str:
    """MLflow /inputs/dataset_inputs shape → dataset source URL string."""
    source = ds.get("source", "")
    if not source:
        return ""
    try:
        source = json.loads(source)
    except (json.JSONDecodeError, TypeError):
        return str(source)
    
    return source.get("url", "")

def _convert_timestamp_to_datetime(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp/1000).strftime("%Y-%m-%d %H:%M:%S") if timestamp else "—"

def _extract_model_version(tags: dict) -> str:
    raw = tags.get("mlflow.modelVersions", "")
    if not raw:
        return ""
    try:
        versions = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not versions:
        return ""
    v = versions[0]                          
    name = v.get("name", "")
    version = v.get("version", "")
    if name and version:
        return f"{name} version {version}"
    return name or (f"version {version}" if version else "")        


def _model_blocks(run: dict) -> str:
    """One block per model_output on this run, each with its own fetched
    details (name, status, registration) and its own fallback on fetch failure."""
    outputs = run.get("outputs", {}).get("model_outputs", []) or []
    if not outputs:
        return '<div class="none">none recorded</div>'

    blocks = []
    for mo in outputs:
        model_id = mo.get("model_id", "")
        rows = {"Model id": model_id, "Step": mo.get("step", "")}

        model_details = get_model_by_id(model_id) if model_id else {}

        info = ((model_details or {}).get("model", {}).get("info", {}))
        status_chip = ""
        if info:
            rows["Name"] = info.get("name", "")
            status = str(info.get("status", "")).removeprefix("LOGGED_MODEL_")
            if status:
                s_fg, s_bg = MODEL_STATUS_COLORS.get(status, ("#5A6472", "#F7F8FA"))
                status_chip = (f'<span class="chip" style="color:{s_fg};'
                              f'background:{s_bg}">{escape(status)}</span>')
            rows["Artifact URI"] = info.get("artifact_uri", "")
            rows["Created at"] = _convert_timestamp_to_datetime(int(info.get("creation_timestamp_ms")))
            rows["Last updated at"] = _convert_timestamp_to_datetime(int(info.get("last_updated_timestamp_ms")))
            regs = info.get("tags") or []
            if regs:
                rows["Registered as"] = _extract_model_version(_kv(regs))

        rows = {k: v for k, v in rows.items() if v}
        rows_out = []
        for k, v in rows.items():
            cls = ' class="mono"' if k == "Model id" else ""
            rows_out.append(f'<tr><td>{escape(str(k))}</td><td{cls}>{escape(str(v))}</td></tr>')
        row_html = "\n".join(rows_out)
        if status_chip:
            row_html += f'<tr><td>Status</td><td>{status_chip}</td></tr>'
        blocks.append(f'<table class="model-block">{row_html}</table>')

    return "\n".join(blocks)



def _md_model_blocks(run: dict, run_details: dict | None = None) -> str:
    """One markdown table per model_output on this run."""
    outputs = run.get("outputs", {}).get("model_outputs", []) or []
    if not outputs:
        return "*none recorded*"
 
    blocks = []
    for mo in outputs:
        model_id = mo.get("model_id", "")
        rows = {"Model id": f"`{model_id}`", "Step": mo.get("step", "")}
 
        info = ((run_details or {}).get("models", {}).get(model_id, {}) or {}).get("info", {})
        if info:
            rows["Name"] = info.get("name", "")
            status = _s(info.get("status")).removeprefix("LOGGED_MODEL_")
            if status:
                rows["Status"] = status
            rows["Created at"] = _convert_timestamp_to_datetime(info.get("creation_timestamp"))
            rows["Last updated"] = _convert_timestamp_to_datetime(info.get("last_updated_timestamp"))
            model_type = info.get("model_type", "")
            if model_type:
                rows["Model type"] = model_type
            tag_list = info.get("tags") or []
            if tag_list:
                version_str = _extract_model_version(_kv(tag_list))
                if version_str:
                    rows["Version"] = version_str
            regs = info.get("registrations") or []
            if regs:
                rows["Registered as"] = f'{regs[0].get("name", "")} v{regs[0].get("version", "")}'
 
        rows = {k: v for k, v in rows.items() if v}
        table = "| Field | Value |\n|---|---|\n" + "\n".join(
            f"| {k} | {_s(v)} |" for k, v in rows.items())
        blocks.append(table)
 
    return "\n\n".join(blocks)


def _extract_run_info(run: dict, mimeType: str) -> str:
    """One run (raw MLflow /runs/get shape) → rendered RUN_CARD html."""
    info = run.get("info", {}) or {}
    data = run.get("data", {}) or {}

    status = info.get("status", "UNKNOWN")

    lifecycle_stage = info.get("lifecycle_stage", "UNKNOWN")
    
    s_fg, s_bg = STATUS_COLORS.get(status, ("#334155", "#E8EDF3"))

    l_fg, l_bg = LIFECYCLE_COLORS.get(lifecycle_stage, ("#334155", "#E8EDF3"))

    metrics = _kv(data.get("metrics"))
    params  = _kv(data.get("params"))

    ds_input = _first(run.get("inputs", {}).get("dataset_inputs"))

    ds = ds_input.get("dataset", {})

    source = ds.get("source", "")
    
    url = _extract_source_url(ds)

    run_id = str(info.get("run_id") or info.get("run_uuid") or "0")

    tags = _kv(data.get("tags"))

    current_tags = {k: v for k, v in tags.items() if not k.startswith("mlflow")}

     
    dataset = {
        "Name":        ds.get("name", ""),
        "Digest":      ds.get("digest", ""),
        "URI":         url,
        "Schema":      _summarize_schema(ds.get("schema")),
        "Context":     _kv(ds_input.get("tags")).get("mlflow.data.context", ""),
    }
    dataset = {k: v for k, v in dataset.items() if v}     # show only present fields

    if mimeType == MIMETYPE.MARKDOWN:
        return RUN_CARD_MD.format(
            run_name=escape(str(info.get("run_name") or run_id)),
            status=escape(str(info.get("status") or "UNKNOWN")),
            lifecycle_stage=(str(info.get("lifecycle_stage") or "UNKNOWN")),
            run_id=escape(run_id),
            user_id=escape(str(info.get("user_id") or "—")),
            duration=_duration(info),
            metrics_rows=_md_rows(metrics),
            params_rows=_md_rows(params),
            model_rows=_md_model_blocks(run),
            dataset_rows=_md_rows(dataset),
            tags_rows=_md_rows(current_tags),
        )
    else:
        return RUN_CARD.format(
        run_name=escape(str(info.get("run_name") or run_id)),
        status=escape(str(info.get("status") or "UNKNOWN")),
        s_fg=s_fg, s_bg=s_bg,
        lifecycle_stage=(str(info.get("lifecycle_stage") or "UNKNOWN")),
        l_fg=l_fg, l_bg=l_bg,
        run_id=escape(run_id),
        user_id=escape(str(info.get("user_id") or "—")),
        duration=_duration(info),
        metrics_rows=_rows(metrics),
        params_rows=_rows(params),
        model_rows=_model_blocks(run),
        dataset_rows=_rows(dataset, mono_keys=("digest",)),
        tags_rows=_rows(current_tags),
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
  


def render_document_html(state: dict, mimeType: str) -> str:
    """
    state: final graph state (query, generation, grading_result, experiment_id)
    """
    answer = state["generation"]
    judge = state["grading_result"]

    aggregate = state.get("aggregates", {})

    answer = answer if answer else "No answer generated"

    evidence_ids = state.get("evidence_ids", [])

    verdict = judge.verdict if judge else "unsupported"
    missing_evidence = judge.missing_evidence if judge else []
    if mimeType == MIMETYPE.MARKDOWN:
        badge = VERDICT_BADGE[verdict]
        note = VERDICT_MD_NOTES.get(verdict, "").format(
            missing=escape(", ".join(missing_evidence)))
        legend = "\n".join(
                f"- **{name}** —— {desc}" for name, desc in VERDICT_DESCRIPTIONS)
    else:
        v_label, v_fg, v_bg = VERDICTS.get(verdict, VERDICTS["unsupported"])
        note_text = VERDICT_NOTES.get(verdict, "").format(
        missing=escape(", ".join(missing_evidence)))
        note = f'<p class="note">{note_text}</p>' if note_text else ""
        legend = "\n".join(
                f"<li><b>{name}</b>: {desc}</li>" for name, desc in VERDICT_LEGEND)

    cards = []
    if judge.related_run_ids:                                  
      for eid in judge.related_run_ids:              
                run_data = get_run_by_id(eid) or {}
                run = run_data.get("run", {})
                if run:
                  cards.append(_extract_run_info(run, mimeType))
    elif evidence_ids:                          
      for eid in evidence_ids:
        if eid in aggregate.get("runs", {}):
            run_data = get_run_by_id(eid) or {}
            run = run_data.get("run", {})
            if run:
                cards.append(_extract_run_info(run, mimeType))
    
    if mimeType == MIMETYPE.MARKDOWN:
        return MD_TEMPLATE.format(
            experiment_id=escape(str(state["experiment_id"])),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            version=PIPELINE_VERSION,
            badge=badge,
            query=escape(state["query"]),
            response=escape(answer),
            note=note,
            cards="\n\n".join(cards) if cards
                  else '*No specific runs cited in this response.*',
            legend=legend,
        )
    
    return PAGE_TEMPLATE.format(
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

    documentation = render_document_html(state, mimetype)

    base_dir = os.path.join(output_dir, f"experiment_{state['experiment_id']}")
    os.makedirs(base_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    output_path = os.path.join(base_dir, f"documentation_{timestamp}.{mimetype}")

    if mimetype == MIMETYPE.PDF:
        HTML(string=documentation).write_pdf(output_path)
    else:
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(documentation)

    print(f"Documentation generated at {output_path} in {mimetype} format.")