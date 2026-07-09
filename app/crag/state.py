from typing import List, TypedDict
from langchain_core.documents import Document


class Status:
    OK = "ok"
    PARTIAL = "partial"
    INSUFFICIENT_DATA = "insufficient_data"


class Grade:
    INCORRECT = "incorrect"
    AMBIGUOUS = "ambiguous"
    CORRECT = "correct"



class GraphState(TypedDict):
    query: str
    experiment_id: str
    documents: List[Document]
    status: List[Status]
    correct: List[Document]
    incorrect: List[Document]




