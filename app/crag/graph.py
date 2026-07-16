from app.crag.nodes import generate, retrieval, transform_query, aggregate_results,grade_structure,decide_after_judging,retrieve_transformed, decide_to_generate,grade_answer, decide_to_generate
from app.crag.state import GraphState
from langgraph.graph import END, StateGraph, START

workflow  = StateGraph(GraphState)

workflow.add_node("retrieve", retrieval)
workflow.add_node("grade_structure", grade_structure)
workflow.add_node("transform_query", transform_query)
workflow.add_node("generate", generate)
workflow.add_node("retrieve_transformed", retrieve_transformed)
workflow.add_node("aggregate_results", aggregate_results)
workflow.add_node("grade_generation", grade_answer)

## Build graph edges
workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "grade_structure")
workflow.add_conditional_edges(
    "grade_structure",
    decide_to_generate,
    {
        "aggregate_results": "aggregate_results",
        "transform_query": "transform_query"
    },
)

workflow.add_edge("transform_query", "retrieve_transformed")
workflow.add_edge("retrieve_transformed", "grade_structure")
workflow.add_edge("aggregate_results", "generate")
workflow.add_edge("generate", "grade_generation")
workflow.add_conditional_edges(
    "grade_generation",
    decide_after_judging,
    {
        "END": END,
        "generate": "generate",
        "transform_query": "transform_query"
    }
)

app = workflow.compile()
