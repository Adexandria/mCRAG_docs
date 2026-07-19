from collections import defaultdict
import datetime
from os import path
import os
from app.crag.nodes import parse_chunk
from app.crag.state import GraphState
from app.docs.response import MIMETYPE, TemplateResponse
from app.config import TEMPLATE_PATH
from weasyprint import HTML
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from langchain_core.documents import Document


def extract_template_response(state: GraphState) -> TemplateResponse:
    """Builds the TemplateResponse for the documentation renderer from the final graph state."""
    verdict = state["grading_result"].verdict if state["grading_result"] else "unknown"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    run_id = (state["grading_result"].related_run_ids[0]
              if state["grading_result"].related_run_ids else "")

    meta = next(
    (d.metadata for d in state["documents"] if d.metadata["run_id"] == run_id),
        None,
    ) if run_id else None

    if meta is None:
        print(f"[extract_template_response] run {run_id!r} not found in documents.")
        return TemplateResponse(
            status="", run_id="", run_name="", created_by="",
            duration=0, experiment_id=state["experiment_id"],
            judge_verdict=verdict, query=state["query"],
            date_time=timestamp, response=state["generation"],
        )

    start, end = meta.get("start_time"), meta.get("end_time")
    duration = (end - start) / 1000 if start and end else 0

    return TemplateResponse(
        status=meta.get("status", ""),
        run_id=run_id,
        run_name=meta.get("run_name", ""),
        created_by=meta.get("user_id", ""),
        duration=duration,
        experiment_id=state["experiment_id"],
        judge_verdict=verdict,
        query=state["query"],
        date_time=timestamp,
        response=state["generation"],
    )


def extract_template() -> str:
    """
    Extracts and returns the content of the HTML template file specified by TEMPLATE_PATH.
    Returns:
        str: The content of the HTML template file.
    """
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as file:
        template_content = file.read()
    
    return template_content


def append_data_to_template(template: str, data:  dict) -> str:
    """
    Appends the provided data to the HTML template by replacing placeholders with actual values.
    Args:
        template (str): The HTML template content.
        data (TemplateResponse): The template response object containing the data to be inserted into the template.
    Returns:
        str: The updated HTML template with data inserted.
    """
    for key, value in data.items():
        placeholder = f"{{{{{key}}}}}"
        template = template.replace(placeholder, str(value))
    
    return template


def generate_documentation(state: GraphState, output_dir: str, mimetype: str):
    """
    Generates documentation by extracting the template and appending the provided data.
    Args:
        state (GraphState): The graph state containing the judge response and other information.
        output_dir (str): The directory where the generated documentation will be saved.
        mimetype (str): The MIME type of the documentation to be generated.
    """
    template = extract_template()
    print(f"Template extracted from {TEMPLATE_PATH}.")

    data = extract_template_response(state)
    documentation = append_data_to_template(template, data.model_dump())

    base_dir = os.path.join(output_dir, f"experiment_{data.experiment_id}")
    os.makedirs(base_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
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