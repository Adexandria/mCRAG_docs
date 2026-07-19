from pydantic import BaseModel, Field, RootModel, model_validator,AliasPath
from typing import Any
from app.config import SECTION

VALID_VERDICTS = {"supported", "missing_evidence", "unsupported",
                  "inconsistent", "unresponsive", "data_insufficient"}

SECTION = set(["summary", "performance", "configuration", "lineage", "metadata"])

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


class GenerateResponse(BaseModel):
    answer: str = Field(..., description="The generated answer", validation_alias = AliasPath("answer"))

class RewriteQueryResponse(RootModel[dict[str, list[str]]]):

    @model_validator(mode="before")
    @classmethod
    def gate_sections(cls, data):
        if not isinstance(data, dict):
            return {}                          
        gated = {}
        for section, terms in data.items():
            s = str(section).strip().lower()
            if s not in SECTION:
                continue                         
            if isinstance(terms, str):           
                terms = terms.split()
            if isinstance(terms, list):
                cleaned = [str(t).strip().lower() for t in terms if str(t).strip()]
                if cleaned:
                    gated[s] = cleaned
        return gated

    def as_queries(self) -> dict[str, str]:
        """The shape retrieval consumes: {section: 'term term term'}."""
        return {s: " ".join(terms) for s, terms in self.root.items()}

    def is_empty(self) -> bool:
        return not self.root