from app.crag.graph import base_workflow

from pprint import pprint

from app.docs.extract_template import generate_documentation
from app.docs.response import MIMETYPE

from app.config import MEDIA_PATH

inputs = {
    "query": "Which attempt gave the best result?",
    "experiment_id": "1",
     "retry_count": 0
}
app = base_workflow()
final_state = app.invoke(inputs)

final_state = None
for mode, out in app.stream(inputs, stream_mode=["updates", "values"]):
    if mode == "updates":
        for node, delta in out.items():
            pprint(f"Node '{node}':"); pprint(delta, indent=2)
    else:
        final_state = out      


# print("Generating documentation...")
generate_documentation(final_state, MEDIA_PATH, MIMETYPE.HTML)