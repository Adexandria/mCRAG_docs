from pprint import pprint
from app.crag.graph import app

inputs = {
    "query": "Extract the run with the best metric?",
    "experiment_id": "0",
     "retry_count": 0
}
for out in app.stream(inputs):
    for key, value in out.items():
        pprint(f"Node '{key}' :")
        pprint(value, indent=2, width=80, depth = None)
    pprint("\\n---\\n")

pprint(value["grading_result"])