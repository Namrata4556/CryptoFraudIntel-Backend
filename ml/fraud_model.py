import os
import joblib
import pandas as pd
import numpy as np


# ============================================================
# MODEL PATH
# ============================================================

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "fraud_model.pkl"
)


# ============================================================
# LOAD MODEL
# ============================================================

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"ML model not found at: {MODEL_PATH}"
    )


print("Loading ML model...")

model_package = joblib.load(MODEL_PATH)

model = model_package["model"]

FEATURES = model_package["features"]

print("ML model loaded successfully.")

print("Expected ML features:", len(FEATURES))


# ============================================================
# PREDICT FRAUD
# ============================================================

def predict_fraud(features):

    """
    Run the trained Random Forest model.

    Accepts either:

        1. Dictionary
        2. Pandas DataFrame

    Returns:

        prediction
        fraud probability
        fraud percentage
        risk level
    """

    print("\n----------------------------------------")
    print("ML PREDICTION")
    print("----------------------------------------")

    print(
        "Expected features:",
        len(FEATURES)
    )


    # ========================================================
    # CONVERT INPUT TO DATAFRAME
    # ========================================================

    if isinstance(features, pd.DataFrame):

        print("Input type: DataFrame")

        input_df = features.copy()

    elif isinstance(features, dict):

        print("Input type: Dictionary")

        input_df = pd.DataFrame(
            [features]
        )

    else:

        raise TypeError(
            "Features must be a dictionary or pandas DataFrame."
        )


    # ========================================================
    # MAKE SURE ALL MODEL FEATURES EXIST
    # ========================================================

    for feature in FEATURES:

        if feature not in input_df.columns:

            print(
                f"[WARNING] Missing feature: {feature}"
            )

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
    # FINAL FEATURE CHECK
    # ========================================================

    print(
        "Final feature shape:",
        input_df.shape
    )

    print(
        "Final feature count:",
        len(input_df.columns)
    )


    # ========================================================
    # MODEL PREDICTION
    # ========================================================

    print("Running Random Forest prediction...")

    prediction = int(
        model.predict(input_df)[0]
    )


    # ========================================================
    # FRAUD PROBABILITY
    # ========================================================

    if hasattr(model, "predict_proba"):

        probability = float(
            model.predict_proba(input_df)[0][1]
        )

    else:

        probability = float(
            prediction
        )


    # ========================================================
    # FRAUD PERCENTAGE
    # ========================================================

    fraud_percentage = round(
        probability * 100,
        2
    )


    # ========================================================
    # RISK LEVEL
    # ========================================================

    if probability >= 0.80:

        risk_level = "CRITICAL"

    elif probability >= 0.60:

        risk_level = "HIGH"

    elif probability >= 0.30:

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

    print("\nML RESULT")
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
        probability
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
    # RETURN RESULT
    # ========================================================

    return {

        "prediction": prediction,

        "label": label,

        "fraud_probability": probability,

        "fraud_percentage": fraud_percentage,

        "risk_level": risk_level
    }