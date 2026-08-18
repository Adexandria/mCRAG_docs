import argparse

from app.retriever.extract_data import get_all_runs_by_experiment_id


def get_number_of_runs(experiment_id):
    """
    Get the number of runs for a given experiment ID.

    Args:
        experiment_id (str): The ID of the experiment.
    """
    runs = get_all_runs_by_experiment_id(experiment_id)
    return len(runs)

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Get the number of runs for a given experiment ID.")
    experiment_id = argparser.add_argument("--experiment-id", type=str, required=True, help="ID of the experiment to get the number of runs for.")

    args = argparser.parse_args()

    num_runs = get_number_of_runs(args.experiment_id)

    print(num_runs)