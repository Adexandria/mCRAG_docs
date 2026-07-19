from pydantic import BaseModel, Field, model_validator, AliasPath


class TemplateResponse(BaseModel):
    status: str = Field(..., description="The status of the run", serialization_alias = "status")
    run_id: str = Field(..., description="The run ID", serialization_alias = "run_id")
    run_name: str = Field(..., description="The run name", serialization_alias = "run_name")
    created_by: str = Field(..., description="The user ID", serialization_alias = "created_by")
    duration: float = Field(..., description="The duration of the run", serialization_alias = "duration")
    experiment_id: int = Field(..., description="The experiment ID", serialization_alias = "experiment_id")
    judge_verdict: str = Field(..., description="The verdict of the evaluation", serialization_alias = "judge_verdict")
    query: str = Field(..., description="The user query", serialization_alias = "query")
    date_time: str = Field(..., description="The date and time of the run", serialization_alias = "date_time")
    response : str = Field(..., description="The raw response from the LLM", serialization_alias = "response")


class MIMETYPE:
    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "md"