import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss


# ============================================================
# PATHS
# ============================================================

DATA_PATH = r"C:\CryptoFraudIntel\data\ethereum_fraud.csv"
MODEL_PATH = r"C:\CryptoFraudIntel\backend\ml\fraud_model.pkl"


# ============================================================
# LOAD DATA
# ============================================================

print("Loading dataset...")

df = pd.read_csv(DATA_PATH)

print("Dataset shape:", df.shape)


# ============================================================
# PREPARE DATA
# ============================================================

DROP_COLUMNS = [
    "FLAG",
    "Address",
    "Unnamed: 0",
    "Index",
    " ERC20 most sent token type",
    "ERC20 most sent token type",
    "ERC20_most_rec_token_type",
]

X = df.drop(
    columns=[c for c in DROP_COLUMNS if c in df.columns],
    errors="ignore"
)

y = df["FLAG"]


# Convert everything to numeric
X = X.apply(
    pd.to_numeric,
    errors="coerce"
)

X = X.replace(
    [float("inf"), float("-inf")],
    pd.NA
)

X = X.fillna(0)


print("Feature count:", X.shape[1])
print("Target distribution:")
print(y.value_counts())


# ============================================================
# SAME TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


# ============================================================
# LOAD EXISTING MODEL
# ============================================================

print("\nLoading existing Random Forest model...")

model = joblib.load(MODEL_PATH)

print("Model loaded.")


# ============================================================
# MODEL PROBABILITIES
# ============================================================

probabilities = model.predict_proba(X_test)[:, 1]


# ============================================================
# BRIER SCORE
# ============================================================

brier = brier_score_loss(
    y_test,
    probabilities
)

print("\n========================================")
print("CALIBRATION TEST")
print("========================================")

print(
    f"Brier Score: {brier:.4f}"
)


# ============================================================
# CALIBRATION CURVE
# ============================================================

fraction_of_positives, mean_predicted_value = calibration_curve(
    y_test,
    probabilities,
    n_bins=10,
    strategy="uniform"
)

print("\nCalibration bins:")

for predicted, actual in zip(
    mean_predicted_value,
    fraction_of_positives
):
    print(
        f"Predicted: {predicted:.3f}  "
        f"Actual fraud rate: {actual:.3f}"
    )


print("\nCalibration test complete.")