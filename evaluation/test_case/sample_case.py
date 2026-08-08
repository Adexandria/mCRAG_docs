import os
import argparse
import dagshub
import requests
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score
from sklearn.model_selection import train_test_split
import mlflow
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
from sklearn.preprocessing import StandardScaler
from app.retriever.extract_data import get_all_runs_by_experiment_id, get_experiment_by_id, unwrap_run_data
from dotenv import load_dotenv
from mlflow.tracking import MlflowClient

load_dotenv()

tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")

timeout_s = int(os.environ.get("TIMEOUT_SECONDS", 30))

DATASET_URL = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/titanic.csv"
DATASET_NAME = "titanic_dataset"

def load_data():
    """Read straight from the URL — nothing touches local disk as a file."""
    df = pd.read_csv(DATASET_URL)
 
    # minimal, deterministic cleanup: keep numeric-friendly columns, drop rows
    # with missing target/features rather than imputing (keeps this simple)
    df = df[["survived", "pclass", "sex", "age", "fare", "sibsp", "parch"]].dropna()
    df["sex"] = df["sex"].map({"male": 0, "female": 1})
 
    X = df.drop(columns=["survived"])
    y = df["survived"]
    return train_test_split(X, y, test_size=0.2, random_state=42), df
 
 
def log_run(name: str, model, params: dict, X_train, X_test, y_train, y_test, df):
    """Train one model, log params/metrics/model/dataset to MLflow."""
    with mlflow.start_run(run_name=name):
        model.fit(X_train, y_train)
 
        train_preds = model.predict(X_train)
        test_preds = model.predict(X_test)
 
        mlflow.log_params(params)
 
        mlflow.log_metric("train_accuracy", accuracy_score(y_train, train_preds))
        mlflow.log_metric("test_accuracy", accuracy_score(y_test, test_preds))
        mlflow.log_metric("precision", precision_score(y_test, test_preds))
        mlflow.log_metric("recall", recall_score(y_test, test_preds))
        mlflow.log_metric("f1_score", f1_score(y_test, test_preds))
 
        dataset = mlflow.data.from_pandas(df, source=DATASET_URL, name=DATASET_NAME)
        mlflow.log_input(dataset, context="training")
 
        mlflow.sklearn.log_model(sk_model=model, name=name.replace("-", "_"), input_example=X_train)
 
        run = mlflow.active_run()
        print(f"[{name}] run_id={run.info.run_id} "
              f"test_accuracy={accuracy_score(y_test, test_preds):.4f}")
        

def set_best_model_tag(experiment_name: str):
    
    experiment_id = get_experiment_by_id(experiment_name)

    runs = get_all_runs_by_experiment_id(experiment_id)

    print(runs[0])

    unwrapped_runs = [unwrap_run_data(run) for run in runs]

    best_run = max(unwrapped_runs, key=lambda run: run["data"]["metrics"].get("test_accuracy", 0))

    best_run_id = best_run["info"]["run_id"]

    remove_runs = [run for run in unwrapped_runs if run["info"]["run_id"] != best_run_id and "best_model" in run["data"]["tags"] and run["data"]["tags"]["best_model"] == "true"]

    # Remove the "best_model" tag from other runs
    for run in remove_runs:
        run_id = run["info"]["run_id"]
        delete_model_tag(run_id)

    set_model_tag(best_run_id)

    run_name = best_run["info"]["run_name"]

    return best_run_id, run_name, experiment_id

def set_model_tag(best_run_id: str):
    """
    Set the "best_model" tag for the run with the highest test accuracy in the given experiment.
    """
    client = MlflowClient(tracking_uri=tracking_uri)
    client.set_tag(best_run_id, "best_model", "true")


def delete_model_tag(run_id: str):
    """
    Delete the "best_model" tag from the specified run.
    """
    client = MlflowClient(tracking_uri=tracking_uri)
    client.delete_tag(run_id, "best_model")
    

def main():
    parser = argparse.ArgumentParser(description="Train sample models and log them to MLflow.")
    parser.add_argument("--experiment-name", default="titanic-demo")
    args = parser.parse_args()

    dagshub.init(repo_owner='Adexandria', repo_name='fraud_detector', mlflow=True)

    mlflow.set_tracking_uri(tracking_uri)

    experiment_name = args.experiment_name

    mlflow.set_experiment(experiment_name)
 
    (X_train, X_test, y_train, y_test), df = load_data()
 
    # Logistic regression benefits from scaled features; tree models don't need it.
    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)

    X_test_scaled = scaler.transform(X_test)
 
    runs = [
        ("logistic-regression", LogisticRegression(max_iter=200, random_state=42),
         {"max_iter": 200, "random_state": 42}, X_train_scaled, X_test_scaled),
 
        ("random-forest-shallow", RandomForestClassifier(n_estimators=100, max_depth=3, random_state=42),
         {"n_estimators": 100, "max_depth": 3, "random_state": 42}, X_train, X_test),
 
        ("random-forest-deep", RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42),
         {"n_estimators": 200, "max_depth": 10, "random_state": 42}, X_train, X_test),
    ]

    for name, model, params, X_tr, X_te in runs:
        log_run(name, model, params, X_tr, X_te, y_train, y_test, df)

    print(f"\nAll runs logged to experiment '{experiment_name}'.")

    print(f"Setting the 'best_model' tag for the run with the highest test accuracy in experiment '{experiment_name}'...")

    best_run_id, run_name, experiment_id = set_best_model_tag(experiment_name)

    if best_run_id:
        print(f"'best_model' tag set successfully for the best run in experiment '{experiment_name}'.")
        model_uri = f"runs:/{best_run_id}/{run_name}"


    print(f"\nDone. {len(runs)} runs logged to experiment '{experiment_name}'.")

    print(f'experiment_id: {experiment_id}')

    github_output_path = os.getenv("GITHUB_OUTPUT")
    if github_output_path:
        with open(github_output_path, "a") as output_file:
            output_file.write(f"experiment_id={experiment_id}\n")
 
 
if __name__ == "__main__":
    main()