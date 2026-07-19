from typing import List, TypedDict, Any
from langchain_core.documents import Document

from app.crag.response import JudgeResponse

# Grade the chunks based on the metadata
class MetadataGrade:
    VALID = "valid" # Include correct metadata
    OUT_OF_SCOPE = "out_of_scope" # Invalid experiment id
    UNANCHORED = "unanchored" # Invalid metadata (missing run_id, etc.)
    

# Grade the structure of the retrieved documents based MLFlow Json structure
class StructureGrade:
    OK                = "ok"               
    PARTIAL           = "partial"           
    INSUFFICIENT_DATA = "insufficient_data"  


"""
Represents the state of the graph at a given point in time
Attributes:
    question: The user query
    experiment_id: The MLflow experiment ID
    documents: List of retrieved documents
    anomaly_documents: List of documents with anomalies
    generation: The generated query based on the user input
    aggregates: Aggregated facts from the retrieved documents
"""



class GraphState(TypedDict):
    query: str
    experiment_id: str

    documents: List[Document]
    grading_report: dict 

    section_queries: dict[str, str]             
    documents_by_section: dict[str, List[Document]]
    section_queries_used: dict[str, str]

    generation : str
    aggregates: dict

    grading_result: JudgeResponse                        
    retry_count: int



