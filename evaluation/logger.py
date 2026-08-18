import argparse
import os
import dotenv

dotenv.load_dotenv()


def log_info(query, experiment_id
              , timestamp, documentation_name, mlflow_tracking_uri):
    """
    Log information about the query and the number of runs.

    Args:
        query (str): The query string.
        experiment_id (str): The ID of the experiment.
        timestamp (float): The timestamp of the log entry.
        documentation_name (str): The name of the documentation.
        mlflow_tracking_uri (str): The URI of the MLflow tracking server.
    """
    log_message = (
        f"Query: {query}\n"
        f"Experiment ID: {experiment_id}\n"
        f"Documentation Name: {documentation_name}\n"
        f"MLflow Tracking URI: {mlflow_tracking_uri}\n"
    )
    mlflow_logger_name = f"{documentation_name}_log_{timestamp}"

    with open(mlflow_logger_name + ".txt", "x") as log_file:
        log_file.write(log_message + "\n")

    return mlflow_logger_name + ".txt"

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Log information about the query and the number of runs.")
    argparser.add_argument("--query", type=str, required=True, help="The query string.")
    argparser.add_argument("--experiment-id", type=str, required=True, help="The ID of the experiment.")
    argparser.add_argument("--documentation-name", type=str, required=True, help="The name of the documentation.")
    argparser.add_argument("--timestamp", type=float, required=True, help="The timestamp of the log entry.")

    argparser.add_argument("--mlflow-tracking-uri", type=str, required=True, help="The URI of the MLflow tracking server.")

    args = argparser.parse_args()
    logged = log_info(
        query=args.query,
        experiment_id=args.experiment_id,
        timestamp=args.timestamp,
        documentation_name=args.documentation_name,
        mlflow_tracking_uri=args.mlflow_tracking_uri
    )

    print(logged)