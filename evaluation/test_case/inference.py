from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KDTree, KNeighborsClassifier
from sklearn.metrics._dist_metrics import EuclideanDistance64
import mlflow
import pandas as pd


def log_model(X_train, y_train, X_test, y_test):
    with mlflow.start_run():
        # Log the hyperparameters
        
        params = {
         "max_iter": 200
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

        mlflow.set_tag("Training Info", "Basic LR model for iris data")   

def random_forest_model(X_train, y_train, X_test, y_test):
    with mlflow.start_run():
        # Log the hyperparameters
        params = {
            "n_estimators": 100,
            "max_depth": 5,
            "random_state": 42
        }
        mlflow.log_params(params)

        # Train the model
        from sklearn.ensemble import RandomForestClassifier

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

        mlflow.set_tag("Training Info", "Random Forest model for iris data")

def inference():
    # Load the iris dataset
    iris = pd.read_csv("https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv")
    X = iris.drop(columns=["species"], axis=1)
    y = iris["species"]

    # Split the dataset into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    mlflow.set_tracking_uri("http://localhost:5000")

    mlflow.set_experiment("Iris_Classification_Experiment")

    # Log models
    log_model(X_train, y_train, X_test, y_test)
    random_forest_model(X_train, y_train, X_test, y_test)

if __name__ == "__main__":
    inference()