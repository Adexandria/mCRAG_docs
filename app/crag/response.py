from pydantic import BaseModel, Field, model_validator,AliasPath

VALID_VERDICTS = {"supported", "missing_evidence", "unsupported",
                  "inconsistent", "insignificance"}

class JudgeResponse(BaseModel):
    verdict: str = Field(..., description="The verdict of the evaluation", validation_alias = AliasPath("verdict"))
    reason: str  = Field(..., description="A brief explanation of the verdict", validation_alias = AliasPath("reason"))
    evidence_ids: list[str] | None = Field(default_factory=list, description="Evidence IDs relevant to the verdict", validation_alias = AliasPath("evidence_ids"))
    related_run_ids: list[str] | None = Field(default=None, description="Related run IDs", validation_alias = AliasPath("related_run_ids"))
    missing_evidence: list[str] | None = Field(default=None, description="Missing evidence IDs", validation_alias = AliasPath("missing_evidence"))

    @model_validator(mode="before")
    @classmethod
    def validate_verdict(cls, data):
        if isinstance(data, dict):
            raw = str(data.get("verdict", "")).strip().lower()
            if raw not in VALID_VERDICTS:
                data["verdict"] = "unsupported"         
            else:
                data["verdict"] = raw                   
        return data

