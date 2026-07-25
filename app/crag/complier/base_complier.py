import argparse

from app.crag.graph import base_workflow

from pprint import pprint

from app.docs.extract_template import generate_documentation
from app.docs.response import MIMETYPE

from app.config import MEDIA_PATH



def run_workflow(query: str, experiment_id: str, media_path: str = MEDIA_PATH, mimetype: str = MIMETYPE.HTML):
    """
    Run the workflow with the given query and experiment ID.
    """
    inputs = {
        "query": query,
        "experiment_id": experiment_id,
        "retry_count": 0
    }
    print(f"Running base workflow with query: '{query}' and experiment_id: '{experiment_id}'")

    app = base_workflow()

    final_state = app.invoke(inputs)    

    print("Base Workflow completed. Generating documentation...")

    generate_documentation(final_state, media_path, mimetype)
    
    print("Documentation generated successfully.")

if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(description="Run the workflow with a query and experiment ID.")
    argument_parser.add_argument("--query",required=True, help="The query to run the workflow with.")
    argument_parser.add_argument("--experiment-id", required=True, help="The experiment ID to run the workflow with.")
    argument_parser.add_argument("--media-path", default=MEDIA_PATH, help="The path to the media directory.")
    argument_parser.add_argument("--mimetype", default=MIMETYPE.HTML, help="The MIME type for the generated documentation.", choices=[MIMETYPE.HTML, MIMETYPE.PDF, MIMETYPE.MARKDOWN])

    args = argument_parser.parse_args()

    run_workflow(
        query=args.query,
        experiment_id=args.experiment_id,
        media_path=args.media_path,
        mimetype=args.mimetype
    )
