from collections import defaultdict
import json
import re
from app.crag.state import Grade, Status
from app.crag.vector_stores import vector_store
from app.config import EXTRACT_ROUTING, SECTION_ROUTING, PREFIX_ROUTING
from app.crag.llm import rewrite_query

def retrieval(state):
    """
    Retrieve relevant information based on the given query.

    Args:
        query (str): The input query for which information needs to be retrieved.

    Returns:
        list: A list of relevant information or results based on the query.
    """
    query = state["query"]
    experiment_id = state["experiment_id"]

    documents = vector_store.similarity_search(query, k=13, filter={"experiment_id": experiment_id})
    
    return { "documents": documents , "query": query, "experiment_id": experiment_id}



def grade_structure(state) :
    """
    Grades the retrieved documents based on their relevance to the query and the experiment ID.
    """

    experiment_id = state["experiment_id"]
    sections = list(SECTION_ROUTING)

    correct, discarded = [], []
    groups_covered: dict[str, set] = defaultdict(set)  

    for doc in state["documents"]:
        meta = doc.metadata
        run_id = meta.get("run_id")

        if meta.get("experiment_id") != experiment_id:
            discarded.append({"grade": Grade.INCORRECT, "run_id": run_id,
                              "reason": f"experiment_id {meta.get('experiment_id')} != {experiment_id}"})
            continue

        if not run_id:
            discarded.append({"grade": Grade.AMBIGUOUS, "run_id": None,
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

        ## Make summary compulsory for all sections

        if supporting_runs:
            section_status[section] = {"status": Status.OK, "supporting_runs": supporting_runs}
        elif any(needed & groups for groups in groups_covered.values()):
            section_status[section] = {
                "status": Status.PARTIAL,
                "missing": sorted(needed - set.union(*groups_covered.values())),
            }
    
        else:
            section_status[section] = {"status": Status.INSUFFICIENT_DATA, "missing": sorted(needed)}

    report = {
        "total_retrieved": len(state["documents"]),
        "correct": len(correct),
        "discarded": discarded,
        "runs_found": sorted(groups_covered),
        "groups_per_run": {rid: sorted(g) for rid, g in groups_covered.items()},
        "section_status": section_status,
        "proceed": len(correct) > 0
                   and any(s["status"] != Status.INSUFFICIENT_DATA for s in section_status.values()),
    }

    return {"documents": correct, "grading_report": report}


def detect_groups(page_content: str) -> set[str]:
    """
    Detects and returns the set of groups present in the given page content based on the defined PREFIX_ROUTING.
    """
    found = set()
    for group, prefix in PREFIX_ROUTING.items():
        if f"('{prefix}" in page_content or f'("{prefix}' in page_content:
            found.add(group)
    return found


def transform_query(state):
    """
    Transforms a vague user query into a structured query and retrieves relevant documents based on the transformed query.
    """
    experiment_id = state["experiment_id"]
    query = state["query"]
    routed = rewrite_query(query)          

    documents_by_section = {}
    seen = {}                                      

    for section in routed:
        docs = vector_store.similarity_search(
              routed[section],                          
            k=13,
            filter={"experiment_id": experiment_id},
        )
        documents_by_section[section] = docs
        for doc in docs:
            key = (doc.metadata["run_id"], doc.metadata["chunk_index"])
            seen.setdefault(key, doc)

    return {
        "documents": list(seen.values()),           
        "documents_by_section": documents_by_section, 
        "section_queries_used": routed,               
    }

def aggregate_results(state):
    """
    Aggregates the results from multiple sections into a single list of documents.
    """
    grading_results = state["grading_results"]
    runs_tuples = defaultdict(list)
    for doc in sorted(grading_results, key=lambda d: d.metadata["chunk_index"]):
        runs_tuples[doc.metadata["run_id"]].extend(parse_chunk(doc.page_content))

    extracted_data = {run_id: extract_all(tuples) for run_id, tuples in runs_tuples.items()}
    
    return {"aggregates": extracted_data}


def parse_chunk(doc: str) -> list[tuple]:
    import ast
    try:
        parsed = ast.literal_eval(doc)         
        if isinstance(parsed, list):
            return parsed                        
        return [parsed]                          
    except (ValueError, SyntaxError): 
        return [tuple(p.split(" = ", 1)) for p in doc.split(" | ") if " = " in p]

def normalize_path(path: str) -> str:
    return re.sub(r"\[(\d+)\]", r".\1", path)

def extract_all(docs):
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
        "query": "What is the best metric for the latest runs?",
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
    aggragate_state = {
        "query": state["query"],
        "experiment_id": state["experiment_id"],
        "grading_results": grading_results["documents"]
    }

    aggregated_results = aggregate_results(aggragate_state)
    print("Aggregated Results:")
    print(json.dumps(aggregated_results["aggregates"], indent=2))




    # transformed_results = transform_query(state)
    # print("Transformed Query Results:")
    # for doc in transformed_results["documents"]:
    #    print(doc)


    