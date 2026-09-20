import os
import glob
import joblib
import pandas as pd
import xgboost as xgb

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RF_MODEL_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "fraud_model.pkl"
)

XGB_MODEL_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "xgboost_fraud_model.json"
)

XGB_FEATURES_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "xgboost_features.pkl"
)


# ============================================================
# FIND DATASET
# ============================================================

def find_dataset():

    search_patterns = [
    os.path.join(BASE_DIR, "*.csv"),
    os.path.join(BASE_DIR, "data", "*.csv"),
    os.path.join(BASE_DIR, "dataset", "*.csv"),
    os.path.join(BASE_DIR, "datasets", "*.csv"),

    # Dataset is stored one level above backend
    os.path.join(BASE_DIR, "..", "data", "*.csv"),

    os.path.join(BASE_DIR, "**", "*.csv")
]

    candidates = []

    for pattern in search_patterns:
        candidates.extend(
            glob.glob(pattern, recursive=True)
        )

    # Remove duplicates
    candidates = list(dict.fromkeys(candidates))

    # Ignore virtual environment and node_modules
    candidates = [
        path for path in candidates
        if "venv" not in path.lower()
        and "node_modules" not in path.lower()
    ]

    print("\nSearching for fraud dataset...\n")

    for path in candidates:

        try:
            df = pd.read_csv(path, nrows=10)

            if "FLAG" in df.columns:

                print("Dataset found:")
                print(path)

                return path

        except Exception:
            continue

    return None


# ============================================================
# LOAD EXISTING RANDOM FOREST FEATURE LIST
# ============================================================

def load_expected_features():

    if not os.path.exists(RF_MODEL_PATH):

        raise FileNotFoundError(
            "\nExisting Random Forest model not found:\n"
            + RF_MODEL_PATH
            + "\n\nMake sure fraud_model.pkl exists."
        )

    print("\nLoading existing Random Forest model...")

    package = joblib.load(RF_MODEL_PATH)

    if not isinstance(package, dict):

        raise ValueError(
            "fraud_model.pkl does not contain the expected dictionary."
        )

    if "features" not in package:

        raise ValueError(
            "The existing fraud_model.pkl does not contain a 'features' list."
        )

    features = package["features"]

    print("Expected ML features:", len(features))

    if len(features) != 46:

        raise ValueError(
            f"Expected 46 features, but found {len(features)}."
        )

    print("\n46 features loaded successfully.")

    return features


# ============================================================
# MAIN TRAINING
# ============================================================

def main():

    print("\n")
    print("=" * 70)
    print("CRYPTO FRAUD INTELLIGENCE SYSTEM")
    print("XGBOOST FRAUD MODEL TRAINING")
    print("=" * 70)

    # --------------------------------------------------------
    # STEP 1 - LOAD FEATURES
    # --------------------------------------------------------

    features = load_expected_features()

    # --------------------------------------------------------
    # STEP 2 - FIND DATASET
    # --------------------------------------------------------

    dataset_path = find_dataset()

    if dataset_path is None:

        raise FileNotFoundError(
            "\nCould not find a CSV dataset containing a FLAG column.\n"
            "Put your Ethereum fraud dataset inside the backend folder "
            "or backend/data folder."
        )

    # --------------------------------------------------------
    # STEP 3 - LOAD DATASET
    # --------------------------------------------------------

    print("\nLoading dataset...")

    df = pd.read_csv(dataset_path)

    print("Dataset shape:", df.shape)

    # --------------------------------------------------------
    # STEP 4 - CHECK TARGET
    # --------------------------------------------------------

    if "FLAG" not in df.columns:

        raise ValueError(
            "FLAG column was not found in dataset."
        )

    print("\nFLAG distribution:")

    print(
        df["FLAG"].value_counts()
    )

    # --------------------------------------------------------
    # STEP 5 - CHECK FEATURES
    # --------------------------------------------------------

    missing_features = [
        feature
        for feature in features
        if feature not in df.columns
    ]

    if missing_features:

        print("\nMissing features:")

        for feature in missing_features:
            print("-", feature)

        raise ValueError(
            "\nThe dataset does not contain all 46 features "
            "required by the existing Random Forest model."
        )

    print("\nAll 46 features found in dataset.")

    # --------------------------------------------------------
    # STEP 6 - BUILD X AND Y
    # --------------------------------------------------------

    X = df[features].copy()

    y = df["FLAG"].copy()

    # Convert all feature columns to numeric
    for column in X.columns:

        X[column] = pd.to_numeric(
            X[column],
            errors="coerce"
        )

    # Replace invalid values
    X = X.replace(
        [float("inf"), float("-inf")],
        pd.NA
    )

    X = X.fillna(0)

    # Convert target to numeric
    y = pd.to_numeric(
        y,
        errors="coerce"
    )

    # Remove invalid target rows
    valid_rows = y.notna()

    X = X.loc[valid_rows]
    y = y.loc[valid_rows]

    y = y.astype(int)

    print("\nFinal training data:")
    print("Rows:", len(X))
    print("Features:", len(X.columns))

    # --------------------------------------------------------
    # STEP 7 - TRAIN TEST SPLIT
    # --------------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    print("\nTraining rows:", len(X_train))
    print("Testing rows:", len(X_test))

    # --------------------------------------------------------
    # STEP 8 - HANDLE CLASS IMBALANCE
    # --------------------------------------------------------

    negative_count = (y_train == 0).sum()
    positive_count = (y_train == 1).sum()

    if positive_count > 0:

        scale_pos_weight = (
            negative_count / positive_count
        )

    else:

        scale_pos_weight = 1.0

    print("\nClass distribution:")
    print("Normal:", negative_count)
    print("Fraud:", positive_count)

    print(
        "Scale positive weight:",
        scale_pos_weight
    )

    # --------------------------------------------------------
    # STEP 9 - CREATE XGBOOST MODEL
    # --------------------------------------------------------

    print("\nCreating XGBoost classifier...")

    model = xgb.XGBClassifier(

        n_estimators=300,

        max_depth=6,

        learning_rate=0.05,

        subsample=0.8,

        colsample_bytree=0.8,

        objective="binary:logistic",

        eval_metric="auc",

        scale_pos_weight=scale_pos_weight,

        random_state=42,

        n_jobs=-1,

        tree_method="hist",

        device="cpu"
    )

    # --------------------------------------------------------
    # STEP 10 - TRAIN
    # --------------------------------------------------------

    print("\nStarting XGBoost training...")

    model.fit(
        X_train,
        y_train,
        eval_set=[
            (X_test, y_test)
        ],
        verbose=True
    )

    print("\nXGBoost training completed.")

    # --------------------------------------------------------
    # STEP 11 - PREDICTIONS
    # --------------------------------------------------------

    print("\nGenerating predictions...")

    y_pred = model.predict(X_test)

    y_probability = model.predict_proba(
        X_test
    )[:, 1]

    # --------------------------------------------------------
    # STEP 12 - METRICS
    # --------------------------------------------------------

    accuracy = accuracy_score(
        y_test,
        y_pred
    )

    auc = roc_auc_score(
        y_test,
        y_probability
    )

    print("\n")
    print("=" * 70)
    print("XGBOOST RESULTS")
    print("=" * 70)

    print(
        f"\nAccuracy: {accuracy * 100:.2f}%"
    )

    print(
        f"ROC-AUC: {auc:.4f}"
    )

    print("\nClassification Report:")

    print(
        classification_report(
            y_test,
            y_pred
        )
    )

    print("\nConfusion Matrix:")

    print(
        confusion_matrix(
            y_test,
            y_pred
        )
    )

    # --------------------------------------------------------
    # STEP 13 - FEATURE IMPORTANCE
    # --------------------------------------------------------

    print("\nTop XGBoost Features:")

    importance = pd.Series(
        model.feature_importances_,
        index=features
    )

    importance = importance.sort_values(
        ascending=False
    )

    print(
        importance.head(15)
    )

    # --------------------------------------------------------
    # STEP 14 - SAVE MODEL
    # --------------------------------------------------------

    print("\nSaving XGBoost model...")

    os.makedirs(
        os.path.dirname(XGB_MODEL_PATH),
        exist_ok=True
    )

    model.save_model(
        XGB_MODEL_PATH
    )

    # Save the exact feature order separately
    joblib.dump(
        features,
        XGB_FEATURES_PATH
    )

    print("\nModel saved:")
    print(XGB_MODEL_PATH)

    print("\nFeature list saved:")
    print(XGB_FEATURES_PATH)

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("XGBOOST TRAINING COMPLETE")
    print("=" * 70)

    print("\nYour existing Random Forest was NOT changed.")

    print("\nNext step:")
    print("We will connect this XGBoost model to the FastAPI backend")
    print("and compare Random Forest vs XGBoost.")

    print("\n")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()