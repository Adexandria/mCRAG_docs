from collections import defaultdict
import json
import os
import re
from app.crag.state import MetadataGrade, StructureGrade, GraphState
from app.crag.vector_stores import vector_store
from app.config import EXTRACT_ROUTING, SECTION_ROUTING, PREFIX_ROUTING
from app.crag.llm import generate_query, grade_response, rewrite_query

k = os.environ.get("RETRIEVAL_K", 13)
MAX_RETRIES = 2

def retrieval(state):
    """
    Retrieve relevant information based on the given query.
    Args:
        state (dict): The current graph state.
    Returns:
       state (dict): Updated graph state with retrieved documents.
    """
    print("---RETRIEVE---")

    query = state["query"]

    experiment_id = state["experiment_id"]

    documents = vector_store.similarity_search(query, k=k, filter={"experiment_id": experiment_id})
    
    return { "documents": documents , "query": query, "experiment_id": experiment_id}



def grade_structure(state) :
    """
    Grades the retrieved documents based on their relevance to the query and the experiment ID.
    
    Args:
        state (dict): The current graph state.
    Returns:
        state (dict): Updated graph state with grading results and a grading report.
    """

    print("---GRADE STRUCTURE---")

    experiment_id = state["experiment_id"]

    sections = list(SECTION_ROUTING)

    correct, discarded = [], []
    groups_covered: dict[str, set] = defaultdict(set)  

    for doc in state["documents"]:
        meta = doc.metadata
        run_id = meta.get("run_id")

        if meta.get("experiment_id") != experiment_id:
            discarded.append({"grade": MetadataGrade.OUT_OF_SCOPE, "run_id": run_id,
                              "reason": f"experiment_id {meta.get('experiment_id')} != {experiment_id}"})
            continue

        if not run_id:
            discarded.append({"grade": MetadataGrade.UNANCHORED, "run_id": None,
                              "reason": "no run_id/run_uuid anchor in metadata"})
            continue

        correct.append(doc)
        groups_covered[run_id] |= detect_groups(doc.page_content)

    section_status = {}
    for section in sections:
        needed = set(SECTION_ROUTING.get(section, []))
      
       
        supporting_runs = [
            rid for rid, groups in groups_covered.items() if needed <= groups
        ]

        if supporting_runs:
            section_status[section] = {"status": StructureGrade.OK, "supporting_runs": supporting_runs}
        elif any(needed & groups for groups in groups_covered.values()):
            section_status[section] = {
                "status": StructureGrade.PARTIAL,
                "missing": sorted(needed - set.union(*groups_covered.values())),
            }
    
        else:
            section_status[section] = {"status": StructureGrade.INSUFFICIENT_DATA, "missing": sorted(needed)}

    report = {
        "total_retrieved": len(state["documents"]),
        "correct": len(correct),
        "discarded": discarded,
        "runs_found": sorted(groups_covered),
        "groups_per_run": {rid: sorted(g) for rid, g in groups_covered.items()},
        "section_status": section_status,
        "proceed": len(correct) > 0
                   and any(s["status"] == StructureGrade.OK for s in section_status.values()),
    }

    return {"documents": correct, "grading_report": report}


def transform_query(state):
    """
    Transforms a vague user query into a structured query and retrieves relevant documents based on the transformed query.
    
    Args:
        state (dict): The current graph state.
    Returns:
        state (dict): Updated graph state with the transformed query and experiment ID.
    """

    print("---Transform Query---")

    experiment_id = state["experiment_id"]

    query = state["query"]

    routed = rewrite_query(query)          

    return {"experiment_id": experiment_id, "section_queries": routed, "retry_count": state["retry_count"] + 1}


def retrieve_transformed(state):
    """
    Retrieves documents based on the transformed query .
    
    Args:
        state (dict): The current graph state.
    Returns:
        state (dict): Updated graph state with retrieved documents, documents by section, and the structured query used.
    """
    print("---Retrieve Transformed---")
    experiment_id = state["experiment_id"]

    query = state["section_queries"]

    documents_by_section = {}

    seen = {}                                      

    for section in query:
        docs = vector_store.similarity_search(
              query[section],                          
            k=k,
            filter={"experiment_id": experiment_id},
        )
        documents_by_section[section] = docs
        for doc in docs:
            key = (doc.metadata["run_id"], doc.metadata["chunk_index"])
            seen.setdefault(key, doc)

    return {
        "documents": list(seen.values()),           
        "documents_by_section": documents_by_section, 
        "section_queries_used": query,               
    }

def decide_to_generate(state):
    """
    Decides whether to proceed with generating a query based on the grading report.
    
    Args:
        state (dict): The current graph state.
    Returns:
        str: "aggregate_results" if the grading report indicates to proceed, otherwise "transform_query".
    """
    print("---Decide to Generate---")

    grading_report = state["grading_report"]

    retries = state["retry_count"]

    proceed = grading_report.get("proceed", False)

    if proceed:
        print("---DECISION: PROCEED TO GENERATE---")
        return "aggregate_results"
    
    if retries >= MAX_RETRIES:
        print (f"---DECISION: {retries} TRANSFORMS EXHAUSTED, PROCEEDING WITH PARTIAL DATA---")
        return "aggregate_results"

    print(" " \
         "---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY---"
        )
    return "transform_query"


def aggregate_results(state):
    """
    Aggregates the results from multiple sections into a single list of documents.

    Args:
        state (dict): The current graph state.

    Returns:
        state (dict): Updated graph state with aggregated results.
    """
    print("---Aggregate Results---")

    grading_results = state["grading_results"]

    runs_tuples = defaultdict(list)

    for doc in sorted(grading_results, key=lambda d: d.metadata["chunk_index"]):
        runs_tuples[doc.metadata["run_id"]].extend(parse_chunk(doc.page_content))

    extracted_data = {run_id: extract_all(tuples) for run_id, tuples in runs_tuples.items()}
    
    return {"aggregates": extracted_data}


def generate(state):
    """
    Generates a query based on the user input and the aggregated facts from the retrieved documents.
    Args:
        state (dict): The current graph state.
    Returns:
        state (dict): Updated graph state with the generated query.
    """
    print("---Generate---")

    query = state["query"]
    aggregates = state["aggregates"]
    facts = "\n".join(
    f"{k}: {json.dumps(v, separators=(',', ':'), default=str)}"
    for k, v in aggregates.items()
    )
    generated_query = generate_query(query, facts)
    return {"generation": generated_query, "query": query, "aggregates": aggregates}

def grade_answer(state):
    """
    Grades the generated answer based on the user query and the provided facts (aggregates).
    Args:
        state (dict): The current graph state.
    Returns:
        state (dict): Updated graph state with the grading result.
    """

    print("---Grade Answer---")

    query = state["query"]

    aggregates = state["aggregates"]

    generation = state["generation"]
    facts = "\n".join(
    f"{k}: {json.dumps(v, separators=(',', ':'), default=str)}"
    for k, v in aggregates.items()
    )

    grading_result = grade_response(query, generation, facts)
    return {"grading_result": grading_result, "query": query, "aggregates": aggregates}


def detect_groups(page_content: str) -> set[str]:
    """
    Detects and returns the set of groups present in the given page content based on the defined PREFIX_ROUTING.
    """
    found = set()
    for group, prefix in PREFIX_ROUTING.items():
        if f"('{prefix}" in page_content or f'("{prefix}' in page_content:
            found.add(group)
    return found

def parse_chunk(doc: str) -> list[tuple]:
    """
    Parses a chunk of document content into a list of tuples.
    """
    import ast
    try:
        parsed = ast.literal_eval(doc)         
        if isinstance(parsed, list):
            return parsed                        
        return [parsed]                          
    except (ValueError, SyntaxError): 
        return [tuple(p.split(" = ", 1)) for p in doc.split(" | ") if " = " in p]


def normalize_path(path: str) -> str:
    """
    Normalizes a path string by replacing bracketed indices with dot notation.
    """
    return re.sub(r"\[(\d+)\]", r".\1", path)

def extract_all(docs):
    """
    Extracts and organizes data from a list of document tuples based on the defined EXTRACT_ROUTING.
    """
    result = result = {group: {} for group in EXTRACT_ROUTING}
    for path, value in docs:
        path = normalize_path(path)
        for group, prefixes in EXTRACT_ROUTING.items():
            if path.startswith(prefixes):                    
                matched = next(p for p in prefixes if path.startswith(p))
                result[group][path.removeprefix(matched)] = value
                break
    return result

if __name__ == "__main__":
   
    state = {
        "query": "Extract the run with the best metric?",
        "experiment_id": "0"
    }
    results = retrieval(state)
    print(len(results["documents"]), "documents retrieved.")
    grade_state = {
        "query": state["query"],
        "experiment_id": state["experiment_id"],
        "documents": results["documents"]
    }

    grading_results = grade_structure(grade_state)

    print("Grading results:", grading_results["grading_report"])

    print("Grading completed.")
    aggragate_state = {
        "query": state["query"],
        "experiment_id": state["experiment_id"],
        "grading_results": grading_results["documents"]
    }

    aggregated_results = aggregate_results(aggragate_state)

    print("Aggregated results:", aggregated_results["aggregates"])

    print("Aggregated completed.")
    
    generate_state = {
        "query": state["query"],
        "experiment_id": state["experiment_id"],
        "aggregates": aggregated_results["aggregates"]
    }

    generated_results = generate(generate_state)

    print("Generated results:", generated_results["generation"])

    print("Generation completed.")

    graded_answer_state = {
        "query": state["query"],
        "experiment_id": state["experiment_id"],
        "aggregates": aggregated_results["aggregates"],
        "generation": generated_results["generation"]
    }

    grading_results = grade_answer(graded_answer_state)

    print("Grading of generated answer completed.")

    print("Final Grading Result:", grading_results["grading_result"])
    #print("Generated Query:", generated_results["generated_query"])






    # transformed_results = transform_query(state)
    # print("Transformed Query Results:")
    # for doc in transformed_results["documents"]:
    #    print(doc)


    