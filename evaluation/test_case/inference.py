from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score
from sklearn.model_selection import train_test_split
import mlflow
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
import mlflow.data
import joblib


def log_model(X_train, y_train, X_test, y_test, dataset):
    with mlflow.start_run():
        # Log the hyperparameters
        
        params = {
         "max_iter": 100
        }
        mlflow.log_params(params)

        # Train the model
        lr = LogisticRegression(**params)

        lr.fit(X_train, y_train)


        # Log the model
        model_info = mlflow.sklearn.log_model(sk_model=lr, name="logistic_regression_model")
        y_pred = lr.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        mlflow.log_metric("accuracy", accuracy)

        precision = precision_score(y_test, y_pred, average='weighted')
        mlflow.log_metric("precision", precision)

        recall = recall_score(y_test, y_pred, average='weighted')
        mlflow.log_metric("recall", recall)

        f1 = f1_score(y_test, y_pred, average='weighted')
        mlflow.log_metric("f1_score", f1)

        mlflow.log_input(dataset, context="Iris dataset for classification tasks")

        mlflow.set_tag("Training Info", "Basic LR model for iris data")   


def log_failed_run_model(X_train, y_train):
    try:
        # Simulate a failure during model logging
        with mlflow.start_run():
            # Log the hyperparameters
            params = {
         "max_iter": 100
            }
            mlflow.log_params(params)

            # Train the model
            lr = LogisticRegression(**params)

            lr.fit(X_train, y_train)
            raise ValueError("Intentional failure for testing purposes")  # Simulate a failure
        
    except Exception as e:
        print(f"Run failed with error: {e}")


def random_forest_model(X_train, y_train, X_test, y_test, dataset):
    with mlflow.start_run():
        # Log the hyperparameters
        params = {
            "n_estimators": 100,
            "max_depth": 5,
            "random_state": 42
        }
        mlflow.log_params(params)

        rf = RandomForestClassifier(**params)

        rf.fit(X_train, y_train)


        # Log the model
        model_info = mlflow.sklearn.log_model(sk_model=rf, name="random_forest_model")
        y_pred = rf.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        mlflow.log_metric("accuracy", accuracy)

        precision = precision_score(y_test, y_pred, average='weighted')
        mlflow.log_metric("precision", precision)

        recall = recall_score(y_test, y_pred, average='weighted')
        mlflow.log_metric("recall", recall)

        f1 = f1_score(y_test, y_pred, average='weighted')
        mlflow.log_metric("f1_score", f1)

        mlflow.log_input(dataset, context="Iris dataset for classification tasks")

        mlflow.set_tag("Training Info", "Random Forest model for iris data")


def log_failed_run_random_forest_model(X_train, y_train):
    try:
        # Simulate a failure during model logging
        with mlflow.start_run():
            # Log the hyperparameters
            params = {
                "n_estimators": 100,
                "max_depth": 5,
                "random_state": 42
            }
            mlflow.log_params(params)

            rf = RandomForestClassifier(**params)

            rf.fit(X_train, y_train)
            raise ValueError("Intentional failure for testing purposes")  # Simulate a failure
        
    except Exception as e:
        print(f"Run failed with error: {e}")

def log_model_info_random_forest():
    """
    Logs the model information to MLflow.
    """
    with mlflow.start_run():
        params = {
                "n_estimators": 100,
                "max_depth": 5,
                "random_state": 42
            }
        mlflow.log_params(params)

def log_model_info_logistic_regression():
    """
    Logs the model information to MLflow.
    """
    with mlflow.start_run():
        params = {
         "max_iter": 100
        }
        mlflow.log_params(params)

def inference():
    # Load the iris dataset
    dataset_url = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv"
    iris = pd.read_csv(dataset_url)
    X = iris.drop(columns=["species"], axis=1)
    y = iris["species"]

    log_X = iris.drop(columns=["petal_length", "petal_width", "species"], axis=1)
    log_y = iris["species"]

    dataset = mlflow.data.from_pandas(
            iris, source=dataset_url, name="iris_dataset", targets="species"
    )

    # Split the dataset into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    Logistic_X_train, Logistic_X_test, Logistic_y_train, Logistic_y_test = train_test_split(log_X, log_y, test_size=0.2, random_state=42)

    mlflow.set_tracking_uri("http://localhost:5000")

    mlflow.set_experiment("Iris_Classification")

    # Log models
    
    for i in range(5):
        log_failed_run_model(Logistic_X_train, Logistic_y_train)
        log_failed_run_random_forest_model(X_train, y_train)
        log_model_info_random_forest()
        log_model_info_logistic_regression()

    log_model(Logistic_X_train, Logistic_y_train, Logistic_X_test, Logistic_y_test, dataset)
    random_forest_model(X_train, y_train, X_test, y_test, dataset)

if __name__ == "__main__":
    inference()