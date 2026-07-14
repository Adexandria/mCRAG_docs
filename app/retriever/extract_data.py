import argparse
import http
import os
from typing import Any
import requests
from collections import defaultdict
from app.config import PREFIX_ROUTING, STOP_TERMS, SKIP_PREFIXES

tracking_uri = os.environ.get("ML_FLOW_tRACKING_URI", "http://localhost:5000")

PAGE_SIZE = os.environ.get("PAGE_SIZE", 100)

TIMEOUT_S = os.environ.get("TIMEOUT_SECONDS", 30)


def fetch_paginated_runs_by_experiment_id(experiment_id):
    """
    Fetches paginated runs for a given experiment ID from the MLflow tracking server.
    """
    url = f"{tracking_uri}/api/2.0/mlflow/runs/search"

    payload: dict[str, Any] = {
        "experiment_ids": [experiment_id],
        "max_results": PAGE_SIZE,
        "order_by": ["attributes.start_time DESC"],
    }

    page_token: str | None = None

    while True:
        body = {**payload, **({"page_token": page_token} if page_token else {})}
        response = requests.post(url, json=body, timeout=TIMEOUT_S)
        if response.status_code != http.HTTPStatus.OK:
            raise RuntimeError(
                f"runs/search failed for experiment {experiment_id}: "
                f"HTTP {response.status_code} — {response.text[:500]}")
        page = response.json()
        yield page
        page_token = page.get("next_page_token")
        if not page_token:
            return


def fetch_all_runs_by_experiment_id(experiment_id):
    """
    Fetches all runs by experiment ID (unpaginated).

    Args:
        experiment_id (str): The ID of the experiment.

    Returns:
        runs_data (list): A list of runs data.
    """
    try:
        for page in fetch_paginated_runs_by_experiment_id(experiment_id):
            yield from page.get("runs", [])
    except Exception as e:
        raise Exception(f"Error occurred while fetching all runs: {e}")
    

# The experiment id is not exposed to the user so this can be use to extract the experiment id from the experiment name. 
def get_experiment_by_name(experiment_name):
    """
    Get the experiment by name.

    Args:
        experiment_name (str): The name of the experiment.

    Returns:
        experiment_data (dict): The data of the experiment.
    """
    try:
        url = f"{tracking_uri}/api/2.0/mlflow/experiments/get-by-name"
        payload = {"experiment_name": experiment_name}
        response = requests.get(url, params=payload, timeout=TIMEOUT_S)

        print(f"Response status code: {response.status_code}")

        if response.status_code != http.HTTPStatus.OK:
            print(f"Failed to get experiment: HTTP {response.status_code} — {response.text[:500]}")
            raise Exception(f"Failed to get experiment")
        
        experiment_data = response.json()
        return experiment_data["experiment"]["experiment_id"]
    
    except Exception as e:
        raise Exception(f"Error occurred while fetching experiment: {e}")


def get_all_runs_by_experiment_name(experiment_name):
    """
    Get all runs by experiment name.

    Args:
        experiment_name (str): The name of the experiment.

    Returns:
        runs_data (list): A list of runs data.
    """
    try:
        experiment_id = get_experiment_by_name(experiment_name)
        print(f"Experiment ID for '{experiment_name}': {experiment_id}")
        return list(fetch_all_runs_by_experiment_id(experiment_id))
        
    except Exception as e:
        raise Exception(f"Error occurred while fetching all runs: {e}")
    


# Extension functions:
# Unwrap the run data to get the run object, flatten the run data, and extract keywords from the flattened run data.

def unwrap(run):
    """
    Unwrap information to get the run object.

    Returns:
        run (dict): The run object.
    """
    if kv_list(run):
        return {item["key"]: unwrap(item["value"]) for item in run}
    if isinstance(run, dict):
        return {key: unwrap(value) for key, value in run.items()}
    if isinstance(run, list):
        return [unwrap(value) for value in run]
        
    return run

def unwrap_run_data(run_data: dict[str, Any]) -> dict[str, Any]:
    return unwrap(run_data.get("run", run_data))

def kv_list(value: list | None) -> dict[str, Any]:
        return (isinstance(value, list) and len(value) > 0
            and all(isinstance(item, dict) and "key" in item  and "value" in item
                    for item in value))

def flatten(obj, prefix=None):
    """
    Flattens a nested dictionary or list into a list of tuples containing the path and value.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from flatten(value, path)
    elif isinstance(obj, list):
        if all(not isinstance(x, (dict, list)) for x in obj):
            yield prefix, obj
        else:
            for i, value in enumerate(obj):
                yield from flatten(value, f"{prefix}.{i}")
    else:
        yield prefix, obj


def extract_keywords(run_tuples: list[tuple]) -> dict[str, set]:
    """
    Extract keywords from the flattened run data based on the defined PREFIX_ROUTING and ignoring certain stop terms and prefixes.
    """
    terms = defaultdict(set)
    for path, value in run_tuples:
        if path.startswith(SKIP_PREFIXES):
            continue
        for group, prefix in PREFIX_ROUTING.items():
            if not path.startswith(prefix):
                continue
            key = path.removeprefix(prefix)
            for word in {key} | set(key.replace(".", " ").replace("_", " ").split()):
                if word.lower() not in STOP_TERMS and not word.isdigit():
                    terms[group].add(word.lower())
            # enum-like values: short alphabetic strings (FINISHED, LOCAL, split names)
            if isinstance(value, str) and value.isalpha() and len(value) <= 20:
                terms[group].add(value.lower())
            break
    return terms
    


## An example function to use while testing.
def get_run_by_id(run_id):
    """
    Get the run by ID.

    Args:
        run_id (str): The ID of the run.

    Returns:
        run_data (dict): The data of the run.
    """
    try:
        url = f"{tracking_uri}/api/2.0/mlflow/runs/get"

        response = requests.get(url, params={"run_id": run_id})

        if response.status_code != http.HTTPStatus.OK:
            raise Exception(f"Failed to get run")

        run_data = response.json()       
        print(f"Run data: {run_data}")
        return run_data 

    except Exception as e:
        raise Exception(f"Error occurred while fetching run: {e}")



if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Get run by ID")
    argparser.add_argument("--run_id", type=str, required=True, help="The ID of the run")
    args = argparser.parse_args()   

    run_data = get_run_by_id(args.run_id)

    unwrapped_data = unwrap_run_data(run_data)

    flattened_data = list(flatten(unwrapped_data))

    print("Unflattened run data:")
    for path, value in flattened_data:
        print(f"  {path} = {value!r}")

