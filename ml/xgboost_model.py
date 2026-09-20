# ============================================================
# CRYPTO FRAUD INTELLIGENCE SYSTEM
# XGBOOST FRAUD MODEL
# ============================================================

import os
import joblib
import pandas as pd
import numpy as np

from xgboost import Booster


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "xgboost_fraud_model.json"
)

FEATURE_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "xgboost_features.pkl"
)


# ============================================================
# LOAD XGBOOST MODEL
# ============================================================

if not os.path.exists(MODEL_PATH):

    raise FileNotFoundError(
        f"XGBoost model not found at: {MODEL_PATH}"
    )


if not os.path.exists(FEATURE_PATH):

    raise FileNotFoundError(
        f"XGBoost feature file not found at: {FEATURE_PATH}"
    )


print("Loading XGBoost model...")

xgb_model = Booster()

xgb_model.load_model(
    MODEL_PATH
)
# ============================================================
# LOAD FEATURES
# ============================================================

FEATURES = joblib.load(
    FEATURE_PATH
)


print(
    "XGBoost model loaded successfully."
)

print(
    "Expected XGBoost features:",
    len(FEATURES)
)


# ============================================================
# PREDICT USING XGBOOST
# ============================================================

def predict_xgboost(features):

    """
    Run the trained XGBoost fraud model.

    Input:
        Dictionary OR Pandas DataFrame

    Output:
        prediction
        probability
        percentage
        risk level
    """

    print("\n")
    print("----------------------------------------")
    print("XGBOOST FRAUD PREDICTION")
    print("----------------------------------------")


    # ========================================================
    # CONVERT INPUT TO DATAFRAME
    # ========================================================

    if isinstance(features, pd.DataFrame):

        input_df = features.copy()

    elif isinstance(features, dict):

        input_df = pd.DataFrame(
            [features]
        )

    else:

        raise TypeError(
            "Features must be a dictionary or pandas DataFrame."
        )


    # ========================================================
    # ADD MISSING FEATURES
    # ========================================================

    for feature in FEATURES:

        if feature not in input_df.columns:

            input_df[feature] = 0.0


    # ========================================================
    # KEEP ONLY TRAINING FEATURES
    # ========================================================

    input_df = input_df[
        FEATURES
    ]


    # ========================================================
    # CLEAN DATA
    # ========================================================

    input_df = input_df.replace(
        [np.inf, -np.inf],
        0
    )

    input_df = input_df.fillna(0)


    # ========================================================
    # CONVERT TO NUMERIC
    # ========================================================

    for column in FEATURES:

        input_df[column] = pd.to_numeric(
            input_df[column],
            errors="coerce"
        )


    input_df = input_df.fillna(0)


    # ========================================================
    # PREDICTION
    # ========================================================

    print(
        "Running XGBoost prediction..."
    )

    # Convert input into XGBoost DMatrix
    import xgboost as xgb

    dmatrix = xgb.DMatrix(
        input_df,
        feature_names=FEATURES
    )

    # For binary:logistic, Booster.predict()
    # directly returns the fraud probability
    fraud_probability = float(
        xgb_model.predict(
            dmatrix
        )[0]
    )

    # Convert probability into 0/1 prediction
    prediction = int(
        fraud_probability >= 0.50
    )


    fraud_percentage = round(
        fraud_probability * 100,
        2
    )


    # ========================================================
    # RISK LEVEL
    # ========================================================

    if fraud_probability >= 0.80:

        risk_level = "CRITICAL"

    elif fraud_probability >= 0.60:

        risk_level = "HIGH"

    elif fraud_probability >= 0.30:

        risk_level = "MEDIUM"

    else:

        risk_level = "LOW"


    # ========================================================
    # LABEL
    # ========================================================

    label = (

        "FRAUD"

        if prediction == 1

        else "NORMAL"
    )


    # ========================================================
    # PRINT RESULT
    # ========================================================

    print("")
    print("XGBOOST RESULT")
    print("----------------------------------------")

    print(
        "Prediction:",
        prediction
    )

    print(
        "Label:",
        label
    )

    print(
        "Fraud probability:",
        fraud_probability
    )

    print(
        "Fraud percentage:",
        fraud_percentage,
        "%"
    )

    print(
        "Risk level:",
        risk_level
    )

    print("----------------------------------------")


    # ========================================================
    # RETURN
    # ========================================================

    return {

        "model":
            "XGBoost",

        "prediction":
            prediction,

        "label":
            label,

        "fraud_probability":
            fraud_probability,

        "fraud_percentage":
            fraud_percentage,

        "risk_level":
            risk_level
    }